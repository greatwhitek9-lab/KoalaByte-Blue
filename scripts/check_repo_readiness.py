#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = REPO_ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

REQUIRED_FILES = [
    "README.md",
    "install.sh",
    "pi-companion/config.default.json",
    "pi-companion/requirements.txt",
    "pi-companion/koalablue/menu_catalog.py",
    "pi-companion/koalablue/meshtastic_app.py",
    "pi-companion/koalablue/t114_bluez.py",
    "pi-companion/koalablue/gnss_location.py",
    "pi-companion/koalablue/location_password_gate.py",
    "pi-companion/koalablue/gpio_buttons.py",
    "pi-companion/koalablue/killerkoala_vocabulary.py",
    "pi-companion/koalablue/killerkoala_hybrid_companion.py",
    "pi-companion/koalablue/killerkoala_voice_control.py",
    "scripts/check_menu_actions.py",
    "scripts/check_killerkoala_ai.py",
    "scripts/check_killerkoala_face_mouth_sync.py",
    "scripts/check_one_shot_controls.py",
    "scripts/preflight_all_hardware.py",
    "scripts/preflight_all_hardware.sh",
    "scripts/test_gpio_buttons.py",
    "scripts/setup_gpio_buttons.py",
    "scripts/run_menu_screen.py",
    "scripts/run_killerkoala_voice.py",
    "scripts/run_killerkoala_hybrid.py",
    "scripts/run_didgeridoo.py",
    "scripts/run_meshtastic_app.py",
    "scripts/run_t114_bluez.py",
    "scripts/run_location_password_gate.py",
    "scripts/setup_killerkoala_ollama.sh",
    "scripts/configure_koalabyte_external_antennas.sh",
    "scripts/check_external_antenna_readiness.py",
    "scripts/flash_t114_when_plugged.sh",
    "scripts/flash_heltec_mouth.sh",
    "scripts/flash_esp32.sh",
    "scripts/install_koalabyte_one_shot.sh",
    "firmware/esp32-dualeye/platformio.ini",
    "firmware/heltec-mouth/platformio.ini",
    "training/killerkoala_lora/Modelfile.killerkoala-tinyllama",
    "docs/KILLERKOALA_LORA_TRAINING.md",
    "docs/EXTERNAL_ANTENNA_READINESS.md",
    "docs/T114_PLUG_IN_FLASHING.md",
]

SHELL_HELPERS = [
    "install.sh",
    "scripts/configure_koalabyte_external_antennas.sh",
    "scripts/flash_t114_when_plugged.sh",
    "scripts/flash_heltec_mouth.sh",
    "scripts/preflight_all_hardware.sh",
    "scripts/setup_killerkoala_ollama.sh",
    "scripts/install_koalabyte_one_shot.sh",
]

REQUIRED_AI_REQUIREMENTS = [
    "httpx",
    "pyttsx3",
    "SpeechRecognition",
]


def check_required_files(failures: list[str]) -> None:
    for relative_path in REQUIRED_FILES:
        if not (REPO_ROOT / relative_path).exists():
            failures.append(f"missing required file: {relative_path}")


def check_readme(failures: list[str]) -> None:
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for needle in [
        "bash scripts/install_koalabyte_one_shot.sh",
        "bash install.sh",
        "InnoMaker CAN kit is optional",
        "ESP32-S3 DualEye",
        "Heltec Mesh Node T114",
        "Didgeridoo",
        "Meshtastic",
        "GNSS",
        "eyes and mouth",
        "button",
        "antenna",
        "TinyLlama",
        "Ollama",
        "killerkoala-tinyllama:latest",
        "scripts/setup_killerkoala_ollama.sh",
    ]:
        if needle not in text:
            failures.append(f"README.md missing expected deployment text: {needle}")


def check_config(failures: list[str]) -> None:
    path = REPO_ROOT / "pi-companion" / "config.default.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"config.default.json is invalid JSON: {exc}")
        return
    for section in ["killerkoala_companion", "koala_kan_kommander", "anteater", "front_panel_buttons"]:
        if section not in config:
            failures.append(f"config missing required section: {section}")
    buttons = config.get("front_panel_buttons", {}).get("buttons", {}) if isinstance(config.get("front_panel_buttons"), dict) else {}
    if len(buttons) != 6:
        failures.append("front_panel_buttons must define exactly six buttons")


def check_ai_requirements(failures: list[str]) -> None:
    requirements_path = REPO_ROOT / "pi-companion" / "requirements.txt"
    text = requirements_path.read_text(encoding="utf-8") if requirements_path.exists() else ""
    lowered = text.lower()
    for requirement in REQUIRED_AI_REQUIREMENTS:
        if requirement.lower() not in lowered:
            failures.append(f"pi-companion/requirements.txt missing KillerKoala AI dependency: {requirement}")

    voice_control = REPO_ROOT / "pi-companion" / "koalablue" / "killerkoala_voice_control.py"
    if voice_control.exists():
        voice_text = voice_control.read_text(encoding="utf-8")
        if "koalblue/" in voice_text or "koalblue." in voice_text:
            failures.append("killerkoala_voice_control.py contains typo reference to koalblue instead of koalablue")
        for needle in ["WAKE_WORD = \"killerkoala\"", "killerkoala-tinyllama:latest", "execute_module", "parse_voice_command"]:
            if needle not in voice_text:
                failures.append(f"killerkoala_voice_control.py missing expected AI/voice text: {needle}")

    one_shot = REPO_ROOT / "scripts" / "install_koalabyte_one_shot.sh"
    if one_shot.exists():
        one_shot_text = one_shot.read_text(encoding="utf-8")
        for needle in ["run_killerkoala_ai_readiness", "scripts/check_killerkoala_ai.py", "KillerKoala AI and voice readiness"]:
            if needle not in one_shot_text:
                failures.append(f"one-shot installer missing KillerKoala AI readiness hook: {needle}")


def check_menu_catalog(failures: list[str]) -> None:
    try:
        from koalablue.menu_catalog import MENU_GROUPS, SUBMENU_ITEMS, leaf_menu_entries, menu_labels
        from scripts.check_menu_actions import build_manifest
    except Exception as exc:
        failures.append(f"failed to import menu readiness helpers: {exc}")
        return
    if "Didgeridoo" not in MENU_GROUPS:
        failures.append("menu catalog missing Didgeridoo group")
    if "didgeridoo" not in SUBMENU_ITEMS:
        failures.append("menu catalog missing didgeridoo submenu")
    if "Didgeridoo" not in menu_labels("main"):
        failures.append("main menu labels missing Didgeridoo")
    if "Heltec / Mesh" in menu_labels("main"):
        failures.append("main menu should not expose a separate Heltec / Mesh item")
    didgeridoo_labels = set(menu_labels("didgeridoo"))
    expected = {
        "T114 BlueZ Controller Check",
        "T114 BlueZ Status",
        "Didgeridoo Status",
        "Didgeridoo Nodes",
        "Didgeridoo GPS Info",
        "Protected Location Gate Status",
        "Protected GNSS Current Fix",
    }
    for label in sorted(expected - didgeridoo_labels):
        failures.append(f"Didgeridoo submenu missing {label}")
    if not leaf_menu_entries():
        failures.append("menu catalog has no enabled leaf menu entries")
    manifest, menu_failures = build_manifest()
    if manifest.get("status") != "MENU_ACTIONS_READY":
        failures.append("menu action manifest is not ready")
    for failure in menu_failures:
        failures.append(f"menu action readiness: {failure}")


def check_helpers(failures: list[str]) -> None:
    for helper in SHELL_HELPERS:
        path = REPO_ROOT / helper
        if not path.exists():
            failures.append(f"missing shell helper: {helper}")
            continue
        text = path.read_text(encoding="utf-8")
        if "set -euo pipefail" not in text:
            failures.append(f"shell helper missing strict shell mode: {helper}")
        result = subprocess.run(["bash", "-n", str(path)], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            failures.append(f"shell syntax failed for {helper}: {result.stderr.strip()}")


def main() -> int:
    failures: list[str] = []
    check_required_files(failures)
    check_readme(failures)
    check_config(failures)
    check_ai_requirements(failures)
    check_menu_catalog(failures)
    check_helpers(failures)
    if failures:
        print("KoalaByte Blue V2 Heltec Edition repo readiness check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("KoalaByte Blue V2 Heltec Edition repo readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
