# Optional T114 Firmware Artifacts

This document preserves the useful findings from the optional T114 build/flash firmware scripts mined from `Backup_heltec` and defines how their artifacts are now generated in the KoalaByte Blue V2 Heltec Edition default paths.

## Deployment rule

The active Heltec Edition branch keeps this default architecture:

```text
Heltec Mesh Node T114 onboard nRF52840 -> primary BLE board and canonical passive BLE source
ESP32-S3 DualEye -> face, eyes, buttons, UI, and secondary BLE node
Raspberry Pi BlueZ -> secondary/fallback host Bluetooth stack
Legacy external nRF52840 Dongle -> explicit opt-in compatibility only
```

The HCI USB, color-mouth, GNSS, face-state, and passive BLE **protocol artifacts** are now part of:

- the one-shot Pi install path through `scripts/install_pi.sh`
- the normal `bash scripts/flash_all_components.sh --install-firmware` path because it runs `scripts/install_pi.sh`
- the normal `bash scripts/flash_all_components.sh --all` path because it runs `scripts/install_pi.sh`
- the default firmware helper through `scripts/build_firmware_all.sh`
- the default CI firmware build through `.github/workflows/koalabyte-blue-ci.yml`

Actual unattended flashing of optional T114 HCI USB or color-mouth firmware remains guarded. Those firmware profiles change the T114 board role and still require hardware validation before adding automatic flashing.

## Default artifact helper

The default artifact path is:

```bash
bash scripts/build_default_t114_protocol_artifacts.sh
```

That helper writes:

```text
logs/optional_t114_firmware_artifacts.json
logs/t114_2g4_antenna_status.json
```

It does not build or flash T114 firmware. It records the protocol schemas, HCI USB build/flash metadata, GNSS message shape, face-state message shape, and passive BLE observation shape so the standard build/install paths always carry the mined artifacts.

## HCI USB / Koala Konnect artifact schema

When an optional T114 HCI USB build is performed, the useful metadata should be written to:

```text
logs/t114_hci_usb_mode.json
```

Recommended schema:

```json
{
  "mode": "t114_koala_konnect",
  "hci_profile": "t114_hci_usb",
  "product_mode": "Koala Konnect",
  "external_bluetooth_adapter": true,
  "board": "<confirmed Zephyr board target>",
  "build_dir": "build/nrf52840-t114-hci-usb",
  "sample_dir": "<Zephyr samples/bluetooth/hci_usb path>",
  "host_role": "USB Bluetooth HCI controller for BlueZ and compatible host Bluetooth stacks",
  "t114_2g4_antenna": "connector",
  "antenna_status_path": "logs/t114_2g4_antenna_status.json",
  "antenna_overlay": ""
}
```

The optional HCI build should resolve antenna overlays through:

```bash
bash scripts/configure_t114_2g4_antenna.sh --print-export
```

If the helper prints an overlay path, pass it into the optional Zephyr build as an extra devicetree overlay. If the helper prints nothing, build without an overlay and treat the 2.4 GHz antenna as a physical connector-only configuration.

## HCI USB flash artifact schema

When an optional T114 HCI USB flash is performed, the useful metadata should be written to:

```text
logs/t114_active_ble_mode.json
```

Recommended schema:

```json
{
  "mode": "t114_koala_konnect",
  "hci_profile": "t114_hci_usb",
  "product_mode": "Koala Konnect",
  "build_dir": "build/nrf52840-t114-hci-usb",
  "flash_method": "west-or-uf2",
  "port": "<optional mounted UF2 path or serial hint>",
  "external_bluetooth_adapter": true,
  "host_expectation": "After replugging, supported hosts may expose the Heltec board as an external Bluetooth HCI adapter. Host driver support is required.",
  "verify_linux": "bluetoothctl list && bluetoothctl show && bluetoothctl --timeout 15 scan on",
  "phone_note": "Phone support depends on USB OTG power/data support and the phone OS exposing USB Bluetooth HCI adapters."
}
```

Do not copy the mined HCI flash script as-is unless the build-helper name is corrected. The mined script referenced `scripts/build_koala_konnect_t114.sh`, but the available mined helper was named `scripts/build_nrf52840_t114_hci_usb.sh`.

## Optional flash methods

The mined flash flow supported two explicit methods:

```text
T114_FLASH_METHOD=west
T114_FLASH_METHOD=uf2
```

These are useful, but automatic flashing should remain guarded because flashing HCI USB changes the T114 from the normal KoalaByte Heltec primary-board profile into a host Bluetooth controller profile.

## Heltec color-mouth USB CDC protocol

The optional color-mouth firmware profile used the T114 USB-C data cable as the only Pi connection. Do not wire Heltec serial pins to the Raspberry Pi GPIO header for face, GNSS, BLE, or LoRa control.

The Pi-side bridge should check these ports in order:

```text
KOALABYTE_HELTEC_USB_PORT
KOALABYTE_HELTEC_FACE_PORT
HELTEC_PORT
```

If none are set, it may scan common USB serial paths such as:

```text
/dev/serial/by-id/*
/dev/ttyACM*
/dev/ttyUSB*
```

## Face-state message shape

Optional face firmware accepts newline-delimited USB CDC JSON messages like:

```json
{
  "type": "killerkoala_face",
  "enabled": true,
  "state": "speaking",
  "message": "too easy mate",
  "duration_ms": 4500
}
```

It may acknowledge with:

```json
{
  "type": "killerkoala_tft_ack",
  "device": "heltec-t114-color",
  "state": "speaking",
  "active": true,
  "gnss_enabled": true,
  "ble_primary_enabled": true,
  "ble_scan_active": false
}
```

This is display-state traffic only. It does not require automatic T114 firmware flashing.

## GNSS forwarding shape

Optional color-mouth/GNSS firmware can forward NMEA data as USB CDC JSON:

```json
{
  "type": "gnss_nmea",
  "device": "heltec-t114",
  "transport": "usb-cdc",
  "nmea": "$GNRMC,..."
}
```

The Pi can request status with:

```json
{"type":"gnss_status"}
```

The active branch keeps GNSS handling password-gated through `pi-companion/koalablue/location_password_gate.py` and `pi-companion/koalablue/gnss_location.py`.

## Passive BLE event shape

Optional T114 firmware profiles should emit passive BLE observations in this shape when acting as the Heltec primary node:

```json
{
  "type": "ble_adv_seen",
  "device": "heltec-t114",
  "source": "heltec-t114",
  "role": "primary",
  "transport": "usb-cdc",
  "addr": "AA:BB:CC:DD:EE:FF",
  "addr_type": "random",
  "rssi": -61,
  "active_scan": false
}
```

Recommended implementation notes mined from the optional firmware:

- Suppress duplicate observations for the same address unless enough time has passed or RSSI changes enough to matter.
- Default to passive scanning.
- Use active scan only in owned-device lab testing where scan-response collection is authorized.
- Keep Heltec-origin observations canonical when duplicate observations are merged.

## Useful default validation commands

```bash
bash scripts/build_default_t114_protocol_artifacts.sh
python scripts/write_optional_t114_firmware_artifacts.py
bash scripts/configure_t114_2g4_antenna.sh --check-only
PYTHONPATH=pi-companion python scripts/run_t114_bluez.py controller-check
PYTHONPATH=pi-companion python scripts/run_killerkoala_face_demo.py --state wake --message "killerkoala online"
PYTHONPATH=pi-companion python scripts/run_location_password_gate.py status
```

## Default flow status

The protocol artifacts are now in the default install/build/CI path. Automatic firmware flashing for optional T114 HCI USB or Heltec color-mouth firmware should not be added until the exact board target, firmware role, and recovery process are validated on hardware.
