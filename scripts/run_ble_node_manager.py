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


def default_primary_ble_port() -> str:
    return os.getenv(
        "KOALABYTE_PRIMARY_BLE_PORT",
        os.getenv(
            "KOALABYTE_HELTEC_USB_PORT",
            os.getenv(
                "HELTEC_PORT",
                os.getenv("KOALABYTE_NRF_BLE_PORT", os.getenv("NRF_BLE_PORT", os.getenv("NRF_DFU_PORT", ""))),
            ),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run KoalaByte Blue V2 Heltec Edition BLE node manager with Heltec T114 nRF52840 as the primary BLE board.")
    parser.add_argument("--duration", type=float, default=30.0, help="Seconds to listen. Use 0 for continuous.")
    parser.add_argument("--primary-port", default=default_primary_ble_port(), help="Primary BLE serial port. Default checks KOALABYTE_PRIMARY_BLE_PORT, KOALABYTE_HELTEC_USB_PORT, HELTEC_PORT, then legacy nRF env names.")
    parser.add_argument("--dongle-port", default="", help="Legacy alias for --primary-port. Prefer --primary-port for the Heltec Edition.")
    parser.add_argument("--esp32-port", default=os.getenv("KOALABYTE_ESP32_FACE_PORT", os.getenv("ESP32_PORT", "")))
    parser.add_argument("--baud", type=int, default=int(os.getenv("KOALABYTE_BLE_NODE_BAUD", "115200")))
    parser.add_argument("--no-pi-bluez", action="store_true", help="Disable Raspberry Pi BlueZ secondary node observations.")
    parser.add_argument("--log-dir", default="logs/ble_nodes")
    args = parser.parse_args()

    primary_port = args.primary_port or args.dongle_port
    manager = BleNodeManager(
        primary_port=primary_port,
        esp32_port=args.esp32_port,
        baud=args.baud,
        log_dir=args.log_dir,
        pi_bluez=not args.no_pi_bluez,
    )

    if not manager.primary_ble.port:
        print("No Heltec T114 primary BLE serial port found. Set KOALABYTE_PRIMARY_BLE_PORT, KOALABYTE_HELTEC_USB_PORT, or HELTEC_PORT.", file=sys.stderr)
        return 2

    duration = None if args.duration == 0 else args.duration
    for event in manager.run(duration_seconds=duration):
        print(json.dumps(event, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())