#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "pi-companion"))

from koalablue.esp32_touch_menu_bridge import Esp32TouchMenuBridge
from koalablue.menu_ui import MenuSelectionScreen


def main() -> int:
    menu = MenuSelectionScreen(visible_rows=6)
    bridge = Esp32TouchMenuBridge(menu=menu)
    samples = [
        {"type": "menu_touch", "event": "down", "x": 100, "y": 80, "row": 2},
        {"type": "menu_touch", "event": "up", "x": 100, "y": 80, "row": 2},
        {"type": "menu_touch", "event": "long_press", "x": 100, "y": 120, "row": 3},
    ]
    events = []
    for payload in samples:
        event = bridge.handle_payload(payload)
        if event is not None:
            events.append({"type": event.event_type, "command": event.command, "label": event.selected_label, "index": event.selected_index})
    print(json.dumps({"touch_menu_bridge": "ok", "events": events}, indent=2, sort_keys=True))
    return 0 if events else 1


if __name__ == "__main__":
    raise SystemExit(main())
