#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "pi-companion"))

from koalablue.esp32_touch_menu_bridge import Esp32TouchMenuBridge
from koalablue.menu_ui import MenuSelectionScreen

try:
    import serial
except Exception:  # pragma: no cover
    serial = None  # type: ignore


def main() -> int:
    parser = argparse.ArgumentParser(description="Bridge ESP32-S3 DualEye touch events into the KoalaByte menu state machine")
    parser.add_argument("--port", default=os.environ.get("KOALABYTE_ESP32_FACE_PORT") or os.environ.get("ESP32_PORT") or "/dev/koalabyte-esp32-eyes")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--calibrate", action="store_true", help="send menu frame geometry to the ESP32 before reading events")
    parser.add_argument("--screen-w", type=int, default=240)
    parser.add_argument("--screen-h", type=int, default=240)
    parser.add_argument("--row-height", type=int, default=40)
    parser.add_argument("--visible-rows", type=int, default=6)
    parser.add_argument("--once", action="store_true", help="read one event and exit")
    args = parser.parse_args()

    if serial is None:
        print("pyserial is required; install pi-companion requirements first.", file=sys.stderr)
        return 1

    menu = MenuSelectionScreen(visible_rows=args.visible_rows)
    bridge = Esp32TouchMenuBridge(menu=menu)

    with serial.Serial(args.port, args.baud, timeout=0.2) as ser:
        if args.calibrate:
            ser.write((bridge.calibration_command(screen_w=args.screen_w, screen_h=args.screen_h, row_height=args.row_height, visible_rows=args.visible_rows) + "\n").encode("utf-8"))
            ser.flush()
            time.sleep(0.1)
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            event = bridge.handle_line(line)
            if event is not None:
                print(json.dumps({"event": event.event_type, "command": event.command, "label": event.selected_label, "index": event.selected_index}, sort_keys=True))
                if args.once:
                    return 0


if __name__ == "__main__":
    raise SystemExit(main())
