#!/usr/bin/env python3
"""Execute firmware protocol patch contracts without PlatformIO or Zephyr."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ESP32 = ROOT / "firmware/esp32-dualeye"
T114 = ROOT / "firmware/t114-combined-safe"
MANIFEST = ROOT / "version/koalabyte_protocol.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load protocol patch: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_once(text: str, marker: str, label: str) -> None:
    count = text.count(marker)
    if count != 1:
        raise AssertionError(f"{label} expected exactly once, found {count}: {marker}")


def validate_esp32(manifest: dict[str, object]) -> dict[str, str]:
    config = (ESP32 / "include/config.h").read_text(encoding="utf-8")
    protocol = str(manifest["esp32_dualeye_min_protocol"])
    repo_version = str(manifest["repo_protocol_version"])
    require_once(config, f'#define KOALABLUE_PROTOCOL "{protocol}"', "ESP32 protocol declaration")
    require_once(
        config,
        f'#define KOALABLUE_REPO_PROTOCOL_VERSION "{repo_version}"',
        "ESP32 repository protocol declaration",
    )

    source = (ESP32 / "src/integrated_main.cpp").read_text(encoding="utf-8")
    old = '  doc["fw"] = KOALABLUE_FW_VERSION;\n  doc["touch"] = false;\n'
    require_once(source, old, "ESP32 node-status protocol anchor")
    patched = source.replace(
        old,
        '  doc["fw"] = KOALABLUE_FW_VERSION;\n'
        '  doc["protocol"] = KOALABLUE_PROTOCOL;\n'
        '  doc["repo_protocol_version"] = KOALABLUE_REPO_PROTOCOL_VERSION;\n'
        '  doc["touch"] = false;\n',
        1,
    )
    require_once(patched, 'doc["protocol"] = KOALABLUE_PROTOCOL;', "ESP32 patched protocol field")
    require_once(
        patched,
        'doc["repo_protocol_version"] = KOALABLUE_REPO_PROTOCOL_VERSION;',
        "ESP32 patched repository protocol field",
    )

    platformio = (ESP32 / "platformio.ini").read_text(encoding="utf-8")
    release_pos = platformio.find("pre:scripts/patch_release_version.py")
    protocol_pos = platformio.find("pre:scripts/patch_protocol_status.py")
    if release_pos < 0 or protocol_pos < 0 or protocol_pos <= release_pos:
        raise AssertionError("ESP32 protocol patch must run after release-version stamping")
    return {"protocol": protocol, "repo_protocol_version": repo_version}


def validate_t114(manifest: dict[str, object]) -> dict[str, str]:
    protocol = str(manifest["heltec_t114_min_protocol"])
    repo_version = str(manifest["repo_protocol_version"])
    tone_path = T114 / "scripts/generate_tone_aware_main.py"
    patch_path = T114 / "scripts/patch_protocol_status.py"
    patch_text = patch_path.read_text(encoding="utf-8")
    require_once(patch_text, f'PROTOCOL = "{protocol}"', "T114 protocol constant")
    require_once(
        patch_text,
        f'REPO_PROTOCOL_VERSION = "{repo_version}"',
        "T114 repository protocol constant",
    )

    tone_module = load_module("koalabyte_t114_tone_contract", tone_path)
    protocol_module = load_module("koalabyte_t114_protocol_contract", patch_path)
    with tempfile.TemporaryDirectory(prefix="koalabyte-t114-protocol-") as temp_dir:
        temp_root = Path(temp_dir)
        tone_output = temp_root / "tone-main.c"
        protocol_output = temp_root / "protocol-main.c"
        tone_module.generate(T114 / "src/main.c", tone_output)
        protocol_module.patch(tone_output, protocol_output)
        patched = protocol_output.read_text(encoding="utf-8")
    require_once(patched, f'#define KOALA_PROTOCOL "{protocol}"', "T114 patched protocol declaration")
    require_once(
        patched,
        f'#define KOALA_REPO_PROTOCOL_VERSION "{repo_version}"',
        "T114 patched repository protocol declaration",
    )
    require_once(patched, r'\"protocol\":\"%s\"', "T114 status protocol field")
    require_once(
        patched,
        r'\"repo_protocol_version\":\"%s\"',
        "T114 status repository protocol field",
    )
    require_once(patched, r'\"tone\":\"%s\"', "T114 tone-aware status field")

    cmake = (T114 / "CMakeLists.txt").read_text(encoding="utf-8")
    tone_pos = cmake.find("generate_tone_aware_main.py")
    protocol_pos = cmake.find("patch_protocol_status.py")
    bootloader_pos = cmake.find("patch_uf2_bootloader_entry.py")
    if min(tone_pos, protocol_pos, bootloader_pos) < 0 or not (
        tone_pos < protocol_pos < bootloader_pos
    ):
        raise AssertionError("T114 generated-source order must be tone, protocol, then UF2 entry")
    return {"protocol": protocol, "repo_protocol_version": repo_version}


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("project") != "KoalaByte Blue V2 Heltec Edition":
        raise AssertionError("unexpected KoalaByte protocol manifest")
    esp32 = validate_esp32(manifest)
    t114 = validate_t114(manifest)
    print(
        json.dumps(
            {
                "status": "FIRMWARE_PROTOCOL_CONTRACT_READY",
                "repo_protocol_version": manifest["repo_protocol_version"],
                "esp32": esp32,
                "t114": t114,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
