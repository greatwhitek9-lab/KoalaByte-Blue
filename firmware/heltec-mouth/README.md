# Heltec Mesh Node T114 v2 color mouth display

This firmware target is for the Heltec Mesh Node T114 v2 / HT-n5262 board with nRF52840, SX1262, USB-C, the 1.14 inch color TFT display, and the optional L76K GNSS add-on module.

## Pi connection

Connect the Heltec T114 to the Raspberry Pi with a USB-C data cable. Do not wire the Heltec serial pins to the Pi GPIO header for the KillerKoala face, GNSS, BLE, or LoRa control channel.

The Pi sends newline-delimited JSON face commands over the Heltec USB CDC serial device. The Pi-side bridge checks these environment variables first:

- `KOALABYTE_HELTEC_USB_PORT`
- `KOALABYTE_HELTEC_FACE_PORT`
- `HELTEC_PORT`

When none are set, the bridge searches common USB serial paths such as `/dev/serial/by-id/*`, `/dev/ttyACM*`, and `/dev/ttyUSB*`.

## BLE primary node

The Heltec branch uses the T114 board's nRF52840 as the **primary BLE node**. ESP32-S3 BLE and Raspberry Pi BlueZ can be used later as secondary observers, but Heltec-origin BLE events are the canonical source of truth when duplicate observations are merged.

The T114 firmware accepts these USB CDC JSON commands:

```json
{"type":"ble_start","role":"primary","active_scan":false}
```

```json
{"type":"ble_stop"}
```

```json
{"type":"ble_status"}
```

```json
{"type":"ble_set_role","role":"secondary"}
```

When scanning, the Heltec emits passive BLE advertisement observations in this shape:

```json
{"type":"ble_adv_seen","device":"heltec-t114","source":"heltec-t114","role":"primary","transport":"usb-cdc","addr":"AA:BB:CC:DD:EE:FF","addr_type":"random","rssi":-61,"active_scan":false}
```

Run the Pi-side node manager after flashing the Heltec firmware:

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 PYTHONPATH=pi-companion python3 scripts/run_ble_node_manager.py --duration 30
```

Use `--active-scan` only for owned-device lab testing where scan-response collection is allowed. The default is passive scanning.

## GNSS add-on

The L76K GNSS module plugs into the Heltec T114 8-pin 1.25 mm GNSS connector. That GNSS cable goes from the GNSS module to the T114 board only; it does not go to the Raspberry Pi GPIO header.

The T114 firmware opens the board's GNSS UART with `Serial1.begin(KOALA_GNSS_BAUD)` and forwards NMEA sentences to the Pi over the same USB CDC link as JSON messages:

```json
{"type":"gnss_nmea","device":"heltec-t114","transport":"usb-cdc","nmea":"$GNRMC,..."}
```

The Pi can also ask for current GNSS status by sending:

```json
{"type":"gnss_status"}
```

## Build and flash

```bash
BUILD_ONLY=1 scripts/flash_heltec_mouth.sh
HELTEC_PORT=/dev/ttyACM0 scripts/flash_heltec_mouth.sh
```

The PlatformIO environment is `heltec_t114_mouth` and uses the local `heltec_t114` board definition plus the `Heltec_T114_Board` Arduino variant.

## Display behavior

The T114 color TFT renders only the lower koala face channel: fuzzy grey cheeks, black nose, and a solid orange animated mouth. The ESP32-S3 DualEye board renders only the eyes. Both devices receive the same face state from the Pi so the eye and mouth motion stay synchronized.
