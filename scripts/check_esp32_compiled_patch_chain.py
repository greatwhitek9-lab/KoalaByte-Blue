#!/usr/bin/env python3
from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / "firmware/esp32-dualeye"
INCLUDED_SOURCE = FIRMWARE / "src/integrated_main.cpp"
WRAPPER_TEMPLATE = FIRMWARE / "src/integrated_main_clean_voice.cpp"
CONFIG_HEADER = FIRMWARE / "include/config.h"
WRAPPER_GENERATOR = FIRMWARE / "scripts/generate_wake_session_source.py"
INCLUDED_PATCHES = (
    FIRMWARE / "scripts/patch_guarded_ble_failover.py",
    FIRMWARE / "scripts/patch_tone_expression_payloads.py",
    FIRMWARE / "scripts/patch_alarm_background.py",
)
GENERATED_PATCHES = (
    FIRMWARE / "scripts/patch_tinyllama_vocabulary_fallback.py",
    FIRMWARE / "scripts/patch_wake_session_awake_eyes.py",
    FIRMWARE / "scripts/patch_local_response_bank.py",
    FIRMWARE / "scripts/patch_local_speech_lifecycle.py",
)
PRE_ROLL_PATCH = FIRMWARE / "scripts/patch_complex_capture_preroll.py"
RELEASE_PATCH = FIRMWARE / "scripts/patch_release_version.py"


class PatchContractError(RuntimeError):
    pass


def _eval_string(node: ast.AST, values: dict[str, str]) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and node.id in values:
        return values[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _eval_string(node.left, values) + _eval_string(node.right, values)
    raise PatchContractError(f"unsupported string expression: {ast.dump(node, include_attributes=False)}")


def _apply_exact(text: str, old: str, new: str, label: str, path: Path) -> str:
    count = text.count(old)
    if count != 1:
        raise PatchContractError(
            f"{path.relative_to(ROOT)} expected one {label!r} anchor, found {count}"
        )
    return text.replace(old, new, 1)


def apply_static_patch(text: str, path: Path) -> tuple[str, list[str]]:
    """Interpret the string replacement contract in one PlatformIO patch script.

    The build scripts are deliberately simple: they assign literal strings, call
    replace_once(), and occasionally assign text = text.replace(...). Executing
    the contract here avoids importing SCons/PlatformIO while still validating
    the same anchors and ordering before any SDK download or compilation begins.
    """

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: dict[str, str] = {}
    labels: list[str] = []

    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id != "text":
                try:
                    values[target.id] = _eval_string(node.value, values)
                except PatchContractError:
                    pass
                continue

            if isinstance(target, ast.Name) and target.id == "text":
                call = node.value
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and isinstance(call.func.value, ast.Name)
                    and call.func.value.id == "text"
                    and call.func.attr == "replace"
                    and len(call.args) >= 2
                ):
                    old = _eval_string(call.args[0], values)
                    new = _eval_string(call.args[1], values)
                    limit = 0
                    if len(call.args) >= 3 and isinstance(call.args[2], ast.Constant):
                        limit = int(call.args[2].value)
                    count = text.count(old)
                    if count < 1:
                        raise PatchContractError(
                            f"{path.relative_to(ROOT)} replacement anchor not found: {old[:80]!r}"
                        )
                    if limit == 1 and count != 1:
                        raise PatchContractError(
                            f"{path.relative_to(ROOT)} expected one replacement anchor, found {count}"
                        )
                    text = text.replace(old, new, limit if limit > 0 else -1)
                    labels.append(f"text.replace:{old[:48]}")
                continue

        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "replace_once":
                if len(call.args) < 3:
                    raise PatchContractError(f"{path}: replace_once requires three arguments")
                old = _eval_string(call.args[0], values)
                new = _eval_string(call.args[1], values)
                label = _eval_string(call.args[2], values)
                text = _apply_exact(text, old, new, label, path)
                labels.append(label)

    if not labels:
        raise PatchContractError(f"{path.relative_to(ROOT)} contains no interpreted replacements")
    return text, labels


def apply_preroll(text: str) -> str:
    spec = importlib.util.spec_from_file_location("koalabyte_preroll_contract", PRE_ROLL_PATCH)
    if spec is None or spec.loader is None:
        raise PatchContractError(f"unable to load {PRE_ROLL_PATCH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    patched = module.patch_text(text)
    if not isinstance(patched, str):
        raise PatchContractError("pre-roll patch did not return source text")
    return patched


def validate_release_stamp() -> dict[str, str]:
    text = CONFIG_HEADER.read_text(encoding="utf-8")
    patch = RELEASE_PATCH.read_text(encoding="utf-8")
    tree = ast.parse(patch, filename=str(RELEASE_PATCH))
    values: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                try:
                    values[target.id] = _eval_string(node.value, values)
                except PatchContractError:
                    pass
    new = values.get("new", "")
    old_candidates = (
        '#define KOALBLUE_FW_VERSION "0.9.7-dualeye-sensitive-killerkoala-menu"',
        '#define KOALABLUE_FW_VERSION "0.9.7-dualeye-sensitive-killerkoala-menu"',
    )
    matches = [candidate for candidate in old_candidates if candidate in text]
    if len(matches) != 1 or not new:
        raise PatchContractError(
            f"release version contract invalid: old_matches={len(matches)} new_present={bool(new)}"
        )
    stamped = text.replace(matches[0], new, 1)
    if "0.9.24-cyber-koala-expression-sync-v2" not in stamped:
        raise PatchContractError("release version output marker is missing")
    return {"source": matches[0], "target": new}


def main() -> int:
    wrapper = WRAPPER_TEMPLATE.read_text(encoding="utf-8")
    include_marker = '#include "integrated_main.cpp"'
    if wrapper.count(include_marker) != 1:
        raise PatchContractError(
            "compiled wrapper must include integrated_main.cpp exactly once"
        )

    included_text = INCLUDED_SOURCE.read_text(encoding="utf-8")
    included_results: list[dict[str, Any]] = []
    for patch in INCLUDED_PATCHES:
        patch_text = patch.read_text(encoding="utf-8")
        if '"integrated_main.cpp"' not in patch_text:
            raise PatchContractError(
                f"{patch.relative_to(ROOT)} no longer targets integrated_main.cpp"
            )
        included_text, labels = apply_static_patch(included_text, patch)
        included_results.append(
            {
                "patch": str(patch.relative_to(ROOT)),
                "replacement_count": len(labels),
                "labels": labels,
            }
        )

    generated_text, generator_labels = apply_static_patch(wrapper, WRAPPER_GENERATOR)
    if generated_text.count(include_marker) != 1:
        raise PatchContractError(
            "wake-session generation lost or duplicated the integrated source include"
        )
    generated_text = apply_preroll(generated_text)

    generated_results: list[dict[str, Any]] = [
        {
            "patch": str(WRAPPER_GENERATOR.relative_to(ROOT)),
            "replacement_count": len(generator_labels),
            "labels": generator_labels,
        },
        {
            "patch": str(PRE_ROLL_PATCH.relative_to(ROOT)),
            "replacement_count": 1,
            "labels": ["patch_text full pre-roll contract"],
        },
    ]
    for patch in GENERATED_PATCHES:
        patch_text = patch.read_text(encoding="utf-8")
        if '"integrated_main_wake_session.cpp"' not in patch_text:
            raise PatchContractError(
                f"{patch.relative_to(ROOT)} no longer targets generated wake-session source"
            )
        generated_text, labels = apply_static_patch(generated_text, patch)
        generated_results.append(
            {
                "patch": str(patch.relative_to(ROOT)),
                "replacement_count": len(labels),
                "labels": labels,
            }
        )

    included_markers = (
        "bleFallbackRequested",
        "loadBleCrashGuard();",
        "applyToneFace(doc, state, message);",
        "showStoredSpeechExpression",
        "alarmBackgroundActive",
        "drawAlarmBackground(true);",
        "error_alarm_latched_waiting_for_pi_clear",
    )
    generated_markers = (
        "wakeSessionActive",
        "serviceWakeSessionTimeout();",
        "trustedPiMenuActivity",
        '"koalabyte-blue-pi"',
        '"local_menu_test"',
        "openGeneratedMenu",
        "complexPreRoll[MIC_PRE_ROLL_BLOCKS][MIC_PCM_CHUNK_BYTES]",
        "waveshare_vocabulary_miss_to_tinyllama",
        "showWakeSessionEyes",
        "local_response_count",
        "embedded_en_au_william_neural_mulaw_40_clip_bank",
        "emitLocalSpeechLifecycle",
        "showLocalSpeakingEyes(category);",
    )
    missing_included = [marker for marker in included_markers if marker not in included_text]
    missing_generated = [marker for marker in generated_markers if marker not in generated_text]
    if missing_included or missing_generated:
        raise PatchContractError(
            f"patch-chain markers missing: included={missing_included}, generated={missing_generated}"
        )
    if "LocalVoiceCategory::Greeting" in generated_text or "LocalVoiceCategory::Thanks" in generated_text:
        raise PatchContractError("legacy local-response category aliases remain after patch chain")

    release = validate_release_stamp()
    print(
        json.dumps(
            {
                "status": "ESP32_COMPLETE_PATCH_CHAIN_READY",
                "compiled_source": "integrated_main_wake_session.cpp",
                "textual_include": str(INCLUDED_SOURCE.relative_to(ROOT)),
                "included_source_patches": included_results,
                "generated_source_patches": generated_results,
                "included_markers": list(included_markers),
                "generated_markers": list(generated_markers),
                "release_version": release,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
