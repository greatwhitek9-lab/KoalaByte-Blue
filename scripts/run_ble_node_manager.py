#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pi-companion"))

from koalablue.ble_node_manager import BleNodeManager  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run KoalaByte BLE node manager with Heltec T114 as the primary BLE node.")
    parser.add_argument("--duration", type=float, default=30.0, help="Seconds to listen. Use 0 for continuous.")
    parser.add_argument("--heltec-port", default=os.getenv("KOALABYTE_HELTEC_USB_PORT", os.getenv("HELTEC_PORT", "")))
    parser.add_argument("--esp32-port", default=os.getenv("KOALABYTE_ESP32_FACE_PORT", os.getenv("ESP32_PORT", "")))
    parser.add_argument("--baud", type=int, default=int(os.getenv("KOALABYTE_FACE_BAUD", "115200")))
    parser.add_argument("--active-scan", action="store_true", help="Ask the Heltec nRF52840 to use active BLE scanning.")
    parser.add_argument("--no-start", action="store_true", help="Do not send ble_start; only listen to existing serial events.")
    parser.add_argument("--log-dir", default="logs/ble_nodes")
    args = parser.parse_args()

    manager = BleNodeManager(
        heltec_port=args.heltec_port,
        esp32_port=args.esp32_port,
        baud=args.baud,
        log_dir=args.log_dir,
    )

    if not manager.heltec.port:
        print("No Heltec serial port found. Set KOALABYTE_HELTEC_USB_PORT or HELTEC_PORT.", file=sys.stderr)
        return 2

    duration = None if args.duration == 0 else args.duration
    for event in manager.run(duration_seconds=duration, active_scan=args.active_scan, start_primary=not args.no_start):
        print(json.dumps(event, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
