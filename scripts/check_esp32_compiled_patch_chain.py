#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
BASE_SOURCE = ROOT / "firmware/esp32-dualeye/src/integrated_main_clean_voice.cpp"
PATCHES = (
    ROOT / "firmware/esp32-dualeye/scripts/patch_guarded_ble_failover.py",
    ROOT / "firmware/esp32-dualeye/scripts/patch_tone_expression_payloads.py",
    ROOT / "firmware/esp32-dualeye/scripts/patch_alarm_background.py",
)
COMPILED_SOURCE_NAME = "integrated_main_wake_session.cpp"


def replacement_calls(path: Path) -> Iterable[tuple[str, str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "replace_once":
            continue
        if len(node.args) < 3:
            continue
        values: list[str] = []
        for arg in node.args[:3]:
            value = ast.literal_eval(arg)
            if not isinstance(value, str):
                raise TypeError(f"{path}: replace_once arguments must be strings")
            values.append(value)
        yield values[0], values[1], values[2]


def main() -> int:
    text = BASE_SOURCE.read_text(encoding="utf-8")
    applied: list[dict[str, object]] = []
    for patch in PATCHES:
        patch_text = patch.read_text(encoding="utf-8")
        if f'"{COMPILED_SOURCE_NAME}"' not in patch_text:
            raise AssertionError(
                f"{patch.relative_to(ROOT)} does not target {COMPILED_SOURCE_NAME}"
            )
        replacements = list(replacement_calls(patch))
        if not replacements:
            raise AssertionError(f"{patch.relative_to(ROOT)} has no replace_once calls")
        labels: list[str] = []
        for old, new, label in replacements:
            count = text.count(old)
            if count != 1:
                raise AssertionError(
                    f"{patch.relative_to(ROOT)} expected one {label!r} anchor, found {count}"
                )
            text = text.replace(old, new, 1)
            labels.append(label)
        applied.append(
            {
                "patch": str(patch.relative_to(ROOT)),
                "replacement_count": len(replacements),
                "labels": labels,
            }
        )

    required_markers = (
        "bleFallbackRequested",
        "loadBleCrashGuard();",
        "applyToneFace(doc, state, message);",
        "showStoredSpeechExpression",
        "alarmBackgroundActive",
        "drawAlarmBackground(true);",
        "error_alarm_latched_waiting_for_pi_clear",
    )
    missing = [marker for marker in required_markers if marker not in text]
    if missing:
        raise AssertionError(f"compiled patch-chain output missing markers: {missing}")

    print(
        json.dumps(
            {
                "status": "ESP32_COMPILED_PATCH_CHAIN_READY",
                "base_source": str(BASE_SOURCE.relative_to(ROOT)),
                "compiled_source": COMPILED_SOURCE_NAME,
                "patches": applied,
                "required_markers": list(required_markers),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
