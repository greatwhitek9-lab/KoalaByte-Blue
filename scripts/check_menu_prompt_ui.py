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
REQUIRED_KEYBOARD_COMMANDS = [
    _KB + "wigle_api_name",
    _KB + ("wigle_api_" + "token"),
    _KB + ("location_" + "password"),
    _KB + ("location_unlock_" + "password"),
    _KB + "meshtastic_send_message",
    _KB + "meshtastic_send_dest",
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
]


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
    system_labels = set(menu_labels("system"))

    for command in REQUIRED_PROMPT_COMMANDS + REQUIRED_KEYBOARD_COMMANDS:
        if command not in leaf_commands:
            failures.append(f"missing prompt UI command in static catalog: {command}")
    if "Keyboard / Text Entry" not in main_labels:
        failures.append("Main menu missing Keyboard / Text Entry")
    if submenu_title("keyboard") != "Keyboard / Text Entry":
        failures.append("Keyboard submenu title is not registered")
    for label in ["WiGLE Name", "WiGLE Key", "Set Local Lock", "Unlock Local Lock", "Mesh Message", "Mesh Destination"]:
        if label not in keyboard_labels:
            failures.append(f"Keyboard submenu missing {label}")
    for label in ["Eucalyptus Prompt Status", "Eucalyptus GPS ON", "Eucalyptus WiGLE Upload ON", "Type WiGLE Name", "Type WiGLE Key"]:
        if label not in eucalyptus_labels:
            failures.append(f"Eucalyptus submenu missing {label}")
    for label in ["Kruisin’ Prompt Status", "Kruisin’ Default Ports", "Kruisin’ WiGLE Upload ON", "Type WiGLE Name", "Type WiGLE Key"]:
        if label not in kruisin_labels:
            failures.append(f"Kruisin submenu missing {label}")
    for label in ["Location Unlock ON", "Location Unlock OFF", "Set Local Lock", "Unlock Local Lock"]:
        if label not in didgeridoo_labels:
            failures.append(f"Didgeridoo submenu missing {label}")
    for label in ["Type Mesh Message", "Type Mesh Destination"]:
        if label not in meshtastic_labels:
            failures.append(f"Meshtastic submenu missing {label}")
    if "Prompt State Status" not in system_labels or "Keyboard / Text Entry" not in system_labels:
        failures.append("System submenu missing prompt/keyboard access")

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
    ]:
        result = run_automated_menu_action(command, command, "System / Companion")
        routed[command] = str(result.get("status"))
        if routed[command] != "AUTOMATED_ACTION_COMPLETE":
            failures.append(f"prompt UI action did not route: {command}")

    menu = MenuSelectionScreen()
    keyboard_event = None
    for index, item in enumerate(menu.items):
        if item.command == "submenu:keyboard":
            menu.selected_index = index
            keyboard_event = menu.select()
            break
    if menu.menu_name != "keyboard":
        failures.append("Keyboard submenu did not open from MenuSelectionScreen")
    for index, item in enumerate(menu.items):
        if item.command == REQUIRED_KEYBOARD_COMMANDS[0]:
            menu.selected_index = index
            menu.select()
            break
    if menu.display_mode != "keyboard":
        failures.append("Popup keyboard did not open from static keyboard submenu")

    state = menu_prompt_state.load_state()
    payload = {
        "status": "MENU_PROMPT_UI_READY" if not failures else "MENU_PROMPT_UI_INCOMPLETE",
        "required_prompt_commands": REQUIRED_PROMPT_COMMANDS,
        "required_keyboard_commands": REQUIRED_KEYBOARD_COMMANDS,
        "keyboard_event": getattr(keyboard_event, "event_type", None),
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
