#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

STATUS_PATH = ROOT / "logs" / "one_shot" / "menu_prompt_ui_readiness.json"

_KB = "keyboard:"
_LOC = "location_"
REQUIRED_KEYBOARD_COMMANDS = [
    _KB + "wigle_api_name",
    _KB + ("wigle_api_" + "token"),
    _KB + (_LOC + "password"),
    _KB + (_LOC + "unlock_" + "password"),
    _KB + "meshtastic_send_message",
    _KB + "meshtastic_send_dest",
    _KB + "bluez_lab_target",
]

REQUIRED_PROMPT_COMMANDS = [
    "prompt_state_status",
    "eucalyptus_prompt_status",
    "eucalyptus_gps_on",
    "eucalyptus_gps_off",
    "eucalyptus_wigle_dry_run_on",
    "eucalyptus_wigle_dry_run_off",
    "eucalyptus_wigle_upload_on",
    "eucalyptus_wigle_upload_off",
    "kruisin_prompt_status",
    "kruisin_gps_on",
    "kruisin_gps_off",
    "kruisin_nodes_on",
    "kruisin_nodes_off",
    "kruisin_default_ports",
    "kruisin_wigle_dry_run_on",
    "kruisin_wigle_dry_run_off",
    "kruisin_wigle_upload_on",
    "kruisin_wigle_upload_off",
    "location_gate_unlock_on",
    "location_gate_unlock_off",
    "bluez_lab_scope_status",
    "bluez_lab_owned_on",
    "bluez_lab_owned_off",
    "bluez_lab_scope_clear",
]


def _require_labels(failures: list[str], labels: set[str], menu_name: str, required: list[str]) -> None:
    for label in required:
        if label not in labels:
            failures.append(f"{menu_name} submenu missing {label}")


def main() -> int:
    failures: list[str] = []
    try:
        from koalablue import menu_prompt_state
        from koalablue.menu_catalog import leaf_menu_entries, menu_labels, submenu_title
        from koalablue.menu_action_runner import run_automated_menu_action
        from koalablue.menu_ui import MenuSelectionScreen
    except Exception as exc:
        failures.append(f"prompt UI imports failed: {exc}")
        payload = {"status": "MENU_PROMPT_UI_INCOMPLETE", "failures": failures, "updated_at": time.time()}
        STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1

    leaf_commands = {str(entry.get("command", "")) for entry in leaf_menu_entries()}
    main_labels = set(menu_labels("main"))
    keyboard_labels = set(menu_labels("keyboard"))
    eucalyptus_labels = set(menu_labels("eucalyptus"))
    kruisin_labels = set(menu_labels("kruisin"))
    didgeridoo_labels = set(menu_labels("didgeridoo"))
    meshtastic_labels = set(menu_labels("meshtastic"))
    lab_labels = set(menu_labels("lab"))
    system_labels = set(menu_labels("system"))

    for command in REQUIRED_PROMPT_COMMANDS + REQUIRED_KEYBOARD_COMMANDS:
        if command not in leaf_commands:
            failures.append(f"missing prompt UI command in static catalog: {command}")

    if "Keyboard / Text Entry" in main_labels:
        failures.append("Main menu should not expose a standalone keyboard page")
    if "Keyboard / Text Entry" in system_labels:
        failures.append("System menu should not expose a standalone keyboard page")
    if keyboard_labels:
        failures.append("Keyboard submenu should be hidden; keyboard should only open from text input actions")
    if submenu_title("keyboard") == "Keyboard / Text Entry":
        failures.append("Keyboard submenu title should not be registered as a visible menu page")

    _require_labels(failures, eucalyptus_labels, "Eucalyptus", ["Eucalyptus Prompt Status", "Eucalyptus GPS ON", "Eucalyptus WiGLE Upload ON", "Type WiGLE Name", "Type WiGLE Key"])
    _require_labels(failures, kruisin_labels, "Kruisin", ["Kruisin’ Prompt Status", "Kruisin’ Default Ports", "Kruisin’ WiGLE Upload ON", "Type WiGLE Name", "Type WiGLE Key"])
    _require_labels(failures, didgeridoo_labels, "Didgeridoo", ["Location Unlock ON", "Location Unlock OFF", "Create Location Password", "Unlock Current Process"])
    _require_labels(failures, meshtastic_labels, "Meshtastic", ["Type Mesh Message", "Type Mesh Destination"])
    _require_labels(failures, lab_labels, "Lab", ["BlueZ Lab Scope Status", "Type BlueZ Lab Target", "Owned Device Scope ON", "Owned Device Scope OFF", "Clear BlueZ Lab Scope"])
    if "Prompt State Status" not in system_labels:
        failures.append("System submenu missing Prompt State Status")

    routed: dict[str, str] = {}
    for command in [
        "prompt_state_status",
        "eucalyptus_gps_on",
        "eucalyptus_wigle_dry_run_on",
        "eucalyptus_wigle_upload_off",
        "kruisin_default_ports",
        "kruisin_nodes_on",
        "kruisin_wigle_dry_run_on",
        "kruisin_wigle_upload_off",
        "location_gate_unlock_off",
        "bluez_lab_scope_status",
        "bluez_lab_owned_on",
        "bluez_lab_owned_off",
        "bluez_lab_scope_clear",
    ]:
        result = run_automated_menu_action(command, command, "System / Companion")
        routed[command] = str(result.get("status"))
        if routed[command] != "AUTOMATED_ACTION_COMPLETE":
            failures.append(f"prompt UI action did not route: {command}")

    text_input_events: dict[str, str] = {}
    for submenu_name, command in [
        ("eucalyptus", REQUIRED_KEYBOARD_COMMANDS[0]),
        ("kruisin", REQUIRED_KEYBOARD_COMMANDS[1]),
        ("didgeridoo", REQUIRED_KEYBOARD_COMMANDS[2]),
        ("didgeridoo", REQUIRED_KEYBOARD_COMMANDS[3]),
        ("meshtastic", REQUIRED_KEYBOARD_COMMANDS[4]),
        ("lab", REQUIRED_KEYBOARD_COMMANDS[6]),
    ]:
        menu = MenuSelectionScreen()
        menu._open_menu(submenu_name, "test_open", f"submenu:{submenu_name}")
        for index, item in enumerate(menu.items):
            if item.command == command:
                menu.selected_index = index
                menu.select()
                break
        key = f"{submenu_name}:{command}"
        text_input_events[key] = str(menu.display_mode)
        if menu.display_mode != "keyboard":
            failures.append(f"Popup keyboard did not open from {submenu_name} text input action {command}")

    state = menu_prompt_state.load_state()
    payload = {
        "status": "MENU_PROMPT_UI_READY" if not failures else "MENU_PROMPT_UI_INCOMPLETE",
        "policy": "popup keyboard appears only after selecting text input actions, not as a standalone menu page",
        "required_prompt_commands": REQUIRED_PROMPT_COMMANDS,
        "required_keyboard_commands": REQUIRED_KEYBOARD_COMMANDS,
        "text_input_events": text_input_events,
        "routed": routed,
        "prompt_path": str(menu_prompt_state.PROMPT_PATH),
        "state_sections": sorted(str(key) for key in state.keys()),
        "failures": failures,
        "updated_at": time.time(),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
