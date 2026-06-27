#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue.gpio_buttons import DEFAULT_BUTTONS, DEFAULT_ELECTRICAL_MODE
from koalablue.menu_catalog import SUBMENU_ITEMS, menu_labels
from scripts.check_menu_actions import build_manifest
from scripts.check_killerkoala_face_mouth_sync import validate_protocol

STATUS_PATH = ROOT / "logs" / "one_shot" / "control_surface_status.json"

REQUIRED_ONE_SHOT_SNIPPETS = [
    "scripts/install_pi.sh",
    "scripts/flash_esp32.sh",
    "scripts/check_killerkoala_face_mouth_sync.py",
    "scripts/check_menu_actions.py",
    "scripts/check_full_runtime_dependencies.py",
    "scripts/configure_koalabyte_external_antennas.sh",
    "scripts/check_killerkoala_ai.py",
    "run_full_runtime_dependency_gate",
    "STRICT_FULL_RUNTIME_DEPENDENCIES",
    "run_killerkoala_ai_readiness",
    "STRICT_KILLERKOALA_AI",
    "prepare_anteater_status",
    "run_optional_can",
    "INSTALL_INNOMAKER_CAN",
    "STRICT_INNOMAKER_CAN",
    '"required": false',
    "InnoMaker CAN kit is optional",
]

REQUIRED_COMMAND_HELPERS = [
    "scripts/install_koalabyte_one_shot.sh",
    "scripts/check_menu_actions.py",
    "scripts/check_voice_menu_launch.py",
    "scripts/check_external_antenna_readiness.py",
    "scripts/check_killerkoala_face_mouth_sync.py",
    "scripts/check_killerkoala_ai.py",
    "scripts/check_full_runtime_dependencies.py",
    "scripts/check_t114_status_dashboard.py",
    "scripts/run_esp32_dualeye_voice_bridge.py",
    "scripts/configure_koalabyte_external_antennas.sh",
    "scripts/flash_t114_when_plugged.sh",
    "scripts/run_didgeridoo.py",
    "scripts/run_location_password_gate.py",
    "scripts/run_t114_bluez.py",
    "scripts/run_meshtastic_app.py",
    "scripts/run_killerkoala_voice.py",
    "scripts/run_killerkoala_hybrid.py",
    "scripts/setup_killerkoala_ollama.sh",
    "scripts/test_gpio_buttons.py",
    "scripts/setup_gpio_buttons.py",
    "scripts/run_koala_bluez.py",
    "scripts/run_koala_bluez_manifest.sh",
    "scripts/run_koala_bluez_inventory.sh",
    "scripts/run_koala_bluez_status.sh",
    "scripts/run_koala_bluez_scan.sh",
    "scripts/run_koala_bluez_monitor.sh",
    "scripts/run_koala_bluez_all_safe.sh",
    "scripts/run_koala_bluez_info.sh",
    "scripts/run_koala_bluez_services.sh",
    "scripts/run_koala_bluez_gatt_readiness.sh",
]

REQUIRED_PROJECT_FILES = [
    "pi-companion/koalablue/bluez_tools.py",
    "pi-companion/koalablue/bluez_protected_lab.py",
    "docs/KOALA_BLUEZ_TOOLS_REVA16.md",
]

REQUIRED_PROTECTED_BLUEZ_LABELS = [
    "Outback Module Deck",
    "Joey Target Dossier",
    "Treehouse Service Trace",
    "Gumnut GATT Gatecheck",
    "Outback Radio Ledger",
    "Classic Track Finder",
    "Treehouse RFCOMM Wiremap",
    "Pouch Link Echo",
    "Gumnut GATT Ghostmap",
]

REQUIRED_PROTECTED_BLUEZ_COMMANDS = [
    "koala_bluez_manifest",
    "koala_bluez_info",
    "koala_bluez_services",
    "koala_bluez_gatt_readiness",
    "bluez_outback_radio_ledger",
    "bluez_classic_track_finder",
    "bluez_treehouse_rfcomm_wiremap",
    "bluez_pouch_link_echo",
    "bluez_gumnut_gatt_ghostmap",
]

REQUIRED_ANTENNA_STATUS = [
    "logs/koalabyte_external_antenna_status.json",
    "logs/t114_lora_external_antenna_status.json",
    "logs/t114_2g4_antenna_status.json",
    "logs/esp32s3_dualeye_2g4_antenna_status.json",
    "logs/pi_2g4_external_antenna_status.json",
]


def run_command(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    return proc.returncode, proc.stdout, proc.stderr


def button_manifest() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen_numbers: set[int] = set()
    seen_pins: set[int] = set()
    for key, cfg in sorted(DEFAULT_BUTTONS.items(), key=lambda item: int(item[1]["number"])):
        number = int(cfg["number"])
        pin = int(cfg["pin"])
        seen_numbers.add(number)
        seen_pins.add(pin)
        rows.append(
            {
                "id": key,
                "number": number,
                "label": cfg.get("label"),
                "pin_bcm": pin,
                "physical_pin": cfg.get("physical_pin"),
                "press_command": cfg.get("press_command"),
                "alias_command": cfg.get("alias_command", ""),
                "hold_command": cfg.get("hold_command", ""),
                "hold_seconds": cfg.get("hold_seconds", ""),
                "electrical_mode": {
                    "internal_pull_up_enabled": DEFAULT_ELECTRICAL_MODE.pull_up,
                    "not_pressed_raw_level": DEFAULT_ELECTRICAL_MODE.idle_state,
                    "pressed_raw_level": DEFAULT_ELECTRICAL_MODE.pressed_state,
                    "wiring": DEFAULT_ELECTRICAL_MODE.wiring,
                },
            }
        )
    if seen_numbers != {1, 2, 3, 4, 5, 6}:
        raise ValueError(f"front-panel button numbers must be 1..6, got {sorted(seen_numbers)}")
    if len(seen_pins) != 6:
        raise ValueError("front-panel button GPIO pins must be unique")
    return rows


def validate_optional_can_policy(one_shot_text: str) -> list[str]:
    failures: list[str] = []
    for needle in ["set +e", "setup_rc=$?", "manifest_rc=$?", "inventory_rc=$?", "status_rc=$?", '"required": false', "STRICT_INNOMAKER_CAN"]:
        if needle not in one_shot_text:
            failures.append(f"optional CAN policy missing non-failing marker: {needle}")
    if "exit 1" in one_shot_text.split("run_optional_can", 1)[-1].split("prepare_anteater_status", 1)[0] and "STRICT_INNOMAKER_CAN" not in one_shot_text:
        failures.append("optional CAN block can fail without STRICT_INNOMAKER_CAN")
    return failures


def validate_protected_bluez_menu() -> list[str]:
    failures: list[str] = []
    bluetooth_labels = set(menu_labels("bluetooth"))
    lab_labels = set(menu_labels("lab"))
    all_entries = [entry for entries in SUBMENU_ITEMS.values() for entry in entries]
    commands = {str(entry.get("command", "")) for entry in all_entries}

    for label in REQUIRED_PROTECTED_BLUEZ_LABELS:
        if label not in bluetooth_labels:
            failures.append(f"Bluetooth Tools menu missing protected BlueZ label: {label}")
    for label in REQUIRED_PROTECTED_BLUEZ_LABELS[1:]:
        if label not in lab_labels:
            failures.append(f"Authorized Lab menu missing protected BlueZ label: {label}")
    for command in REQUIRED_PROTECTED_BLUEZ_COMMANDS:
        if command not in commands:
            failures.append(f"menu catalog missing protected BlueZ command: {command}")

    return failures


def validate_protected_bluez_code() -> list[str]:
    failures: list[str] = []
    protected_module = ROOT / "pi-companion" / "koalablue" / "bluez_protected_lab.py"
    menu_runner = ROOT / "scripts" / "run_menu_screen.py"
    docs = ROOT / "docs" / "KOALA_BLUEZ_TOOLS_REVA16.md"
    runtime_gate = ROOT / "scripts" / "check_full_runtime_dependencies.py"
    required_needles = {
        protected_module: [
            "ensure_unlocked",
            "KOALABYTE_BLUEZ_LAB_TARGET",
            "KOALABYTE_BLUEZ_OWNED_DEVICE",
            "Outback Radio Ledger",
            "Classic Track Finder",
            "Treehouse RFCOMM Wiremap",
            "Pouch Link Echo",
            "Gumnut GATT Ghostmap",
        ],
        menu_runner: [
            "run_koala_bluez_manifest",
            "run_protected_bluez_menu_action",
            "bluez_gumnut_gatt_ghostmap",
        ],
        docs: [
            "Outback Module Deck",
            "Protected lab-only BlueZ menu actions",
            "KOALABYTE_BLUEZ_LAB_TARGET",
            "Gumnut GATT Ghostmap",
        ],
        runtime_gate: [
            "koalablue.bluez_protected_lab",
            "scripts/run_koala_bluez_info.sh",
            "scripts/run_koala_bluez_services.sh",
            "bluez_legacy_lab_optional",
        ],
    }
    for path, needles in required_needles.items():
        if not path.exists():
            failures.append(f"missing protected BlueZ file: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in needles:
            if needle not in text:
                failures.append(f"{path.relative_to(ROOT)} missing protected BlueZ marker: {needle}")
    return failures


def main() -> int:
    failures: list[str] = []
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    menu_manifest, menu_failures = build_manifest()
    failures.extend(f"menu: {failure}" for failure in menu_failures)
    failures.extend(validate_protected_bluez_menu())
    failures.extend(validate_protected_bluez_code())

    buttons: list[dict[str, object]] = []
    try:
        buttons = button_manifest()
    except Exception as exc:
        failures.append(f"buttons: {exc}")

    for helper in REQUIRED_COMMAND_HELPERS:
        if not (ROOT / helper).exists():
            failures.append(f"missing command/control helper: {helper}")
    for project_file in REQUIRED_PROJECT_FILES:
        if not (ROOT / project_file).exists():
            failures.append(f"missing project file: {project_file}")

    one_shot = ROOT / "scripts" / "install_koalabyte_one_shot.sh"
    one_shot_text = one_shot.read_text(encoding="utf-8") if one_shot.exists() else ""
    for snippet in REQUIRED_ONE_SHOT_SNIPPETS:
        if snippet not in one_shot_text:
            failures.append(f"one-shot installer missing required step/policy: {snippet}")
    failures.extend(validate_optional_can_policy(one_shot_text))

    antenna_rc, antenna_stdout, antenna_stderr = run_command(["bash", "scripts/configure_koalabyte_external_antennas.sh", "--check-only"])
    if antenna_rc != 0:
        failures.append(f"antenna readiness command failed: {antenna_stderr.strip() or antenna_stdout.strip()}")
    for status_file in REQUIRED_ANTENNA_STATUS:
        if not (ROOT / status_file).exists():
            failures.append(f"missing antenna status file: {status_file}")

    menu_voice_rc, menu_voice_stdout, menu_voice_stderr = run_command([sys.executable, "scripts/check_voice_menu_launch.py"])
    if menu_voice_rc != 0:
        failures.append(f"voice menu launch readiness failed: {menu_voice_stderr.strip() or menu_voice_stdout.strip()}")

    ai_rc, ai_stdout, ai_stderr = run_command([sys.executable, "scripts/check_killerkoala_ai.py"])
    if ai_rc != 0:
        failures.append(f"KillerKoala AI readiness failed: {ai_stderr.strip() or ai_stdout.strip()}")

    face_failures = validate_protocol()
    failures.extend(f"face/mouth: {failure}" for failure in face_failures)

    payload = {
        "status": "ONE_SHOT_CONTROLS_READY" if not failures else "ONE_SHOT_CONTROLS_INCOMPLETE",
        "updated_at": time.time(),
        "menu": {
            "status": menu_manifest.get("status"),
            "menu_names": menu_manifest.get("menu_names", []),
            "enabled_leaf_count": menu_manifest.get("enabled_leaf_count", 0),
            "handler_count": menu_manifest.get("handler_count", 0),
            "manifest": "logs/menu_actions/menu_action_manifest.json",
        },
        "protected_bluez_menu": {
            "labels": REQUIRED_PROTECTED_BLUEZ_LABELS,
            "commands": REQUIRED_PROTECTED_BLUEZ_COMMANDS,
            "password_gate_module": "pi-companion/koalablue/location_password_gate.py",
            "protected_module": "pi-companion/koalblue/bluez_protected_lab.py".replace("koalblue", "koalablue"),
            "target_env": "KOALABYTE_BLUEZ_LAB_TARGET",
            "owned_env": "KOALABYTE_BLUEZ_OWNED_DEVICE",
            "required_for_one_shot_control_validation": True,
        },
        "voice_menu_launch": {
            "status_path": "logs/menu_voice/voice_menu_launch_status.json",
            "manifest_path": "logs/menu_voice/voice_menu_launch_manifest.json",
            "syntax": ["killerkoala run <menu item or command>", "killerkoala open <menu item or command>"],
            "check_rc": menu_voice_rc,
        },
        "buttons": buttons,
        "button_count": len(buttons),
        "gpio_button_electrical_mode": {
            "internal_pull_up_enabled": DEFAULT_ELECTRICAL_MODE.pull_up,
            "not_pressed_raw_level": DEFAULT_ELECTRICAL_MODE.idle_state,
            "pressed_raw_level": DEFAULT_ELECTRICAL_MODE.pressed_state,
        },
        "killerkoala_ai": {
            "status_path": "logs/killerkoala/killerkoala_ai_readiness.json",
            "required": True,
            "esp32_dualeye_builtin_mic_bridge": "scripts/run_esp32_dualeye_voice_bridge.py",
            "check_rc": ai_rc,
        },
        "full_runtime_dependency_gate": {
            "status_path": "logs/one_shot/full_runtime_dependencies.json",
            "checker": "scripts/check_full_runtime_dependencies.py",
            "strict_mode_env": "STRICT_FULL_RUNTIME_DEPENDENCIES=1",
            "required_for_one_shot": True,
        },
        "innomaker_can": {
            "required_for_install": False,
            "default_mode": "optional",
            "strict_mode_env": "STRICT_INNOMAKER_CAN=1",
            "install_must_continue_when_absent": True,
        },
        "antenna_status_files": REQUIRED_ANTENNA_STATUS,
        "required_command_helpers": REQUIRED_COMMAND_HELPERS,
        "required_project_files": REQUIRED_PROJECT_FILES,
        "one_shot_required_steps": REQUIRED_ONE_SHOT_SNIPPETS,
        "face_mouth_protocol": "killerkoala_face",
        "failures": failures,
    }
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "status_path": str(STATUS_PATH), "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
