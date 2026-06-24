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

from koalablue.gpio_buttons import DEFAULT_BUTTONS
from koalablue.menu_catalog import MAIN_MENU_ITEMS, SUBMENU_ITEMS
from scripts.check_menu_actions import build_manifest
from scripts.check_killerkoala_face_mouth_sync import validate_protocol

STATUS_PATH = ROOT / "logs" / "one_shot" / "control_surface_status.json"

REQUIRED_ONE_SHOT_SNIPPETS = [
    "scripts/install_pi.sh",
    "scripts/flash_esp32.sh",
    "scripts/check_killerkoala_face_mouth_sync.py",
    "scripts/check_menu_actions.py",
    "scripts/configure_koalabyte_external_antennas.sh",
    "prepare_anteater_status",
    "run_optional_can",
]

REQUIRED_COMMAND_HELPERS = [
    "scripts/install_koalabyte_one_shot.sh",
    "scripts/check_menu_actions.py",
    "scripts/check_external_antenna_readiness.py",
    "scripts/check_killerkoala_face_mouth_sync.py",
    "scripts/configure_koalabyte_external_antennas.sh",
    "scripts/flash_t114_when_plugged.sh",
    "scripts/run_didgeridoo.py",
    "scripts/run_location_password_gate.py",
    "scripts/run_t114_bluez.py",
    "scripts/run_meshtastic_app.py",
    "scripts/test_gpio_buttons.py",
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
                "press_command": cfg.get("press_command"),
                "alias_command": cfg.get("alias_command", ""),
                "hold_command": cfg.get("hold_command", ""),
                "hold_seconds": cfg.get("hold_seconds", ""),
            }
        )
    if seen_numbers != {1, 2, 3, 4, 5, 6}:
        raise ValueError(f"front-panel button numbers must be 1..6, got {sorted(seen_numbers)}")
    if len(seen_pins) != 6:
        raise ValueError("front-panel button GPIO pins must be unique")
    return rows


def main() -> int:
    failures: list[str] = []
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    menu_manifest, menu_failures = build_manifest()
    failures.extend(f"menu: {failure}" for failure in menu_failures)

    buttons: list[dict[str, object]] = []
    try:
        buttons = button_manifest()
    except Exception as exc:
        failures.append(f"buttons: {exc}")

    for helper in REQUIRED_COMMAND_HELPERS:
        if not (ROOT / helper).exists():
            failures.append(f"missing command/control helper: {helper}")

    one_shot = ROOT / "scripts" / "install_koalabyte_one_shot.sh"
    one_shot_text = one_shot.read_text(encoding="utf-8") if one_shot.exists() else ""
    for snippet in REQUIRED_ONE_SHOT_SNIPPETS:
        if snippet not in one_shot_text:
            failures.append(f"one-shot installer missing required step: {snippet}")

    antenna_rc, antenna_stdout, antenna_stderr = run_command(["bash", "scripts/configure_koalabyte_external_antennas.sh", "--check-only"])
    if antenna_rc != 0:
        failures.append(f"antenna readiness command failed: {antenna_stderr.strip() or antenna_stdout.strip()}")
    for status_file in REQUIRED_ANTENNA_STATUS:
        if not (ROOT / status_file).exists():
            failures.append(f"missing antenna status file: {status_file}")

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
        "buttons": buttons,
        "button_count": len(buttons),
        "antenna_status_files": REQUIRED_ANTENNA_STATUS,
        "required_command_helpers": REQUIRED_COMMAND_HELPERS,
        "one_shot_required_steps": REQUIRED_ONE_SHOT_SNIPPETS,
        "face_mouth_protocol": "killerkoala_face",
        "failures": failures,
    }
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "status_path": str(STATUS_PATH), "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
