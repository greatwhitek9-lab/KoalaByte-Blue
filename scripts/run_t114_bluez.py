#!/usr/bin/env python3
"""Run Heltec T114 nRF52840 combined BLE wrapper actions.

The Pi owns action processing and automation. The Heltec T114 onboard nRF52840
is the primary BLE radio endpoint over USB CDC JSON. Raspberry Pi BlueZ and the
ESP32-S3 DualEye remain secondary BLE nodes.
"""

from koalablue.t114_bluez import run_cli

if __name__ == "__main__":
    raise SystemExit(run_cli())
