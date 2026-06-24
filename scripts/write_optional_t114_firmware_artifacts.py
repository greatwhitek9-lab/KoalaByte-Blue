#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

DEFAULT_OUTPUT = Path("logs/optional_t114_firmware_artifacts.json")


def build_manifest() -> dict[str, object]:
    return {
        "status": "OPTIONAL_T114_FIRMWARE_ARTIFACTS_RECORDED",
        "generated_at": time.time(),
        "default_deployment": {
            "included_in_one_shot_all": False,
            "included_in_install_firmware": False,
            "included_in_default_ci_build": False,
            "reason": "Optional T114 HCI USB and color-mouth firmware profiles change the board role and require hardware validation before flashing.",
        },
        "hci_usb_build_manifest": {
            "path": "logs/t114_hci_usb_mode.json",
            "mode": "t114_koala_konnect",
            "hci_profile": "t114_hci_usb",
            "product_mode": "Koala Konnect",
            "external_bluetooth_adapter": True,
            "build_dir": "build/nrf52840-t114-hci-usb",
            "host_role": "USB Bluetooth HCI controller for BlueZ and compatible host Bluetooth stacks",
            "antenna_status_path": "logs/t114_2g4_antenna_status.json",
        },
        "hci_usb_flash_manifest": {
            "path": "logs/t114_active_ble_mode.json",
            "flash_methods": ["west", "uf2"],
            "verify_linux": "bluetoothctl list && bluetoothctl show && bluetoothctl --timeout 15 scan on",
            "phone_note": "Phone support depends on USB OTG power/data support and the phone OS exposing USB Bluetooth HCI adapters.",
            "build_helper_name_warning": "The mined flash script referenced scripts/build_koala_konnect_t114.sh, but the mined build helper was scripts/build_nrf52840_t114_hci_usb.sh.",
        },
        "usb_cdc_ports": [
            "KOALABYTE_HELTEC_USB_PORT",
            "KOALABYTE_HELTEC_FACE_PORT",
            "HELTEC_PORT",
            "/dev/serial/by-id/*",
            "/dev/ttyACM*",
            "/dev/ttyUSB*",
        ],
        "face_state_message": {
            "type": "killerkoala_face",
            "enabled": True,
            "state": "speaking",
            "message": "too easy mate",
            "duration_ms": 4500,
        },
        "face_ack_message": {
            "type": "killerkoala_tft_ack",
            "device": "heltec-t114-color",
            "state": "speaking",
            "active": True,
            "gnss_enabled": True,
            "ble_primary_enabled": True,
            "ble_scan_active": False,
        },
        "gnss_message": {
            "type": "gnss_nmea",
            "device": "heltec-t114",
            "transport": "usb-cdc",
            "nmea": "$GNRMC,...",
            "status_request": {"type": "gnss_status"},
        },
        "passive_ble_event": {
            "type": "ble_adv_seen",
            "device": "heltec-t114",
            "source": "heltec-t114",
            "role": "primary",
            "transport": "usb-cdc",
            "addr": "AA:BB:CC:DD:EE:FF",
            "addr_type": "random",
            "rssi": -61,
            "active_scan": False,
        },
        "rules": [
            "Keep optional T114 HCI USB and color-mouth firmware out of the default one-shot installer until hardware validated.",
            "Use the T114 2.4 GHz antenna connector for the 2.4 GHz antenna; do not attach LoRa antenna to the 2.4 GHz connector.",
            "Only use a devicetree antenna overlay when the RF-switch GPIO has been confirmed from the exact schematic or board DTS.",
            "GNSS/location writing stays protected by the local password gate.",
            "Default BLE observation should be passive; active scan is for owned-device lab testing only.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Write optional T114 firmware artifact manifest without building or flashing firmware")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"wrote": str(out), "status": manifest["status"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
