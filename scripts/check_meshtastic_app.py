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


def main() -> int:
    failures: list[str] = []
    try:
        importlib.import_module("meshtastic")
    except Exception as exc:
        failures.append(f"missing Meshtastic Python package: {exc}")

    try:
        from koalablue import meshtastic_app
        from koalablue.meshtastic_menu_items import make_didgeridoo_items, make_meshtastic_items
        from koalablue.menu_ui import MenuItem, MenuSelectionScreen
    except Exception as exc:
        failures.append(f"KoalaByte Meshtastic imports failed: {exc}")
        payload = {"status": "MESHTASTIC_APP_INCOMPLETE", "failures": failures, "updated_at": time.time()}
        STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1

    didgeridoo_labels = [item.label for item in make_didgeridoo_items(MenuItem)]
    meshtastic_labels = [item.label for item in make_meshtastic_items(MenuItem)]
    for label in ["Meshtastic App"]:
        if label not in didgeridoo_labels:
            failures.append(f"Didgeridoo menu missing {label}")
    for label in ["Meshtastic Profile", "Meshtastic Compatibility", "Phone App Pairing", "ESP32 Device Link", "Use Heltec USB Serial", "Use Network TCP", "Use BLE Link", "Meshtastic Status", "Meshtastic Nodes", "Meshtastic GPS Info"]:
        if label not in meshtastic_labels:
            failures.append(f"Meshtastic menu missing {label}")

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
    payload = {
        "status": "MESHTASTIC_APP_READY" if not failures else "MESHTASTIC_APP_INCOMPLETE",
        "didgeridoo_labels": didgeridoo_labels,
        "meshtastic_labels": meshtastic_labels,
        "profile_status": profile.get("status"),
        "compatibility_status": compatibility.get("status"),
        "failures": failures,
        "updated_at": time.time(),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
