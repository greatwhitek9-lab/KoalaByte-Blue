#!/usr/bin/env python3
from __future__ import annotations

import importlib
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

STATUS_PATH = ROOT / "logs" / "one_shot" / "meshtastic_app_readiness.json"

REQUIRED_MESHTASTIC_LABELS = [
    "Meshtastic Profile",
    "Meshtastic Compatibility",
    "Phone App Pairing",
    "ESP32 Device Link",
    "Use Heltec USB Serial",
    "Use Network TCP",
    "Use BLE Link",
    "Meshtastic Status",
    "Meshtastic Nodes",
    "Meshtastic GPS Info",
    "Meshtastic Listen Gate",
    "Meshtastic Send Gate",
]

REQUIRED_MESHTASTIC_COMMANDS = [
    "meshtastic_profile",
    "meshtastic_compatibility",
    "meshtastic_phone_pairing",
    "meshtastic_esp32_device",
    "meshtastic_setup_serial",
    "meshtastic_setup_tcp",
    "meshtastic_setup_ble",
    "meshtastic_status",
    "meshtastic_nodes",
    "meshtastic_gps",
    "meshtastic_listen",
    "meshtastic_send_gate",
]


def main() -> int:
    failures: list[str] = []
    try:
        importlib.import_module("meshtastic")
    except Exception as exc:
        failures.append(f"missing Meshtastic Python package: {exc}")

    try:
        from koalablue import meshtastic_app
        from koalablue.menu_catalog import menu_labels, leaf_menu_entries
        from koalablue.meshtastic_menu_items import make_didgeridoo_items, make_meshtastic_items
        from koalablue.menu_action_runner import run_automated_menu_action
        from koalablue.menu_ui import MenuItem, MenuSelectionScreen
    except Exception as exc:
        failures.append(f"KoalaByte Meshtastic imports failed: {exc}")
        payload = {"status": "MESHTASTIC_APP_INCOMPLETE", "failures": failures, "updated_at": time.time()}
        STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1

    didgeridoo_labels = [item.label for item in make_didgeridoo_items(MenuItem)]
    dynamic_meshtastic_labels = [item.label for item in make_meshtastic_items(MenuItem)]
    static_meshtastic_labels = menu_labels("meshtastic")
    static_leaf_commands = {str(entry.get("command")) for entry in leaf_menu_entries()}

    if "Meshtastic App" not in didgeridoo_labels:
        failures.append("Didgeridoo menu missing Meshtastic App")
    for label in REQUIRED_MESHTASTIC_LABELS:
        if label not in dynamic_meshtastic_labels:
            failures.append(f"dynamic Meshtastic menu missing {label}")
        if label not in static_meshtastic_labels:
            failures.append(f"static Meshtastic menu missing {label}")
    for command in REQUIRED_MESHTASTIC_COMMANDS:
        if command not in static_leaf_commands:
            failures.append(f"static Meshtastic catalog missing command {command}")

    menu = MenuSelectionScreen(items=make_didgeridoo_items(MenuItem))
    for idx, item in enumerate(menu.items):
        if item.command == "submenu:meshtastic":
            menu.selected_index = idx
            menu.select()
            break
    if menu.menu_name != "meshtastic":
        failures.append("Meshtastic App did not open the Meshtastic submenu")

    profile = meshtastic_app.profile_status()
    compatibility = meshtastic_app.compatibility_status()
    send_gate = run_automated_menu_action("meshtastic_send_gate", "Meshtastic Send Gate", "Didgeridoo")
    if str(send_gate.get("status")) not in {"AUTOMATED_ACTION_COMPLETE"}:
        failures.append("Meshtastic Send Gate did not route through automated menu runner")

    payload = {
        "status": "MESHTASTIC_APP_READY" if not failures else "MESHTASTIC_APP_INCOMPLETE",
        "didgeridoo_labels": didgeridoo_labels,
        "dynamic_meshtastic_labels": dynamic_meshtastic_labels,
        "static_meshtastic_labels": static_meshtastic_labels,
        "required_meshtastic_labels": REQUIRED_MESHTASTIC_LABELS,
        "required_meshtastic_commands": REQUIRED_MESHTASTIC_COMMANDS,
        "profile_status": profile.get("status"),
        "compatibility_status": compatibility.get("status"),
        "send_gate_status": send_gate.get("status"),
        "send_gate_result_status": (send_gate.get("result") or {}).get("status") if isinstance(send_gate.get("result"), dict) else None,
        "failures": failures,
        "updated_at": time.time(),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
