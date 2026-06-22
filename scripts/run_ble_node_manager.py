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
    parser = argparse.ArgumentParser(description="Run KoalaByte BLE node manager with nRF52840 Dongle as the primary BLE node.")
    parser.add_argument("--duration", type=float, default=30.0, help="Seconds to listen. Use 0 for continuous.")
    parser.add_argument("--dongle-port", default=os.getenv("KOALABYTE_NRF_BLE_PORT", os.getenv("NRF_BLE_PORT", os.getenv("NRF_DFU_PORT", ""))))
    parser.add_argument("--esp32-port", default=os.getenv("KOALABYTE_ESP32_FACE_PORT", os.getenv("ESP32_PORT", "")))
    parser.add_argument("--baud", type=int, default=int(os.getenv("KOALABYTE_BLE_NODE_BAUD", "115200")))
    parser.add_argument("--no-pi-bluez", action="store_true", help="Disable Raspberry Pi BlueZ secondary observations.")
    parser.add_argument("--log-dir", default="logs/ble_nodes")
    args = parser.parse_args()

    manager = BleNodeManager(
        dongle_port=args.dongle_port,
        esp32_port=args.esp32_port,
        baud=args.baud,
        log_dir=args.log_dir,
        pi_bluez=not args.no_pi_bluez,
    )

    if not manager.dongle.port:
        print("No nRF52840 Dongle serial port found. Set KOALABYTE_NRF_BLE_PORT or NRF_BLE_PORT.", file=sys.stderr)
        return 2

    duration = None if args.duration == 0 else args.duration
    for event in manager.run(duration_seconds=duration):
        print(json.dumps(event, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
