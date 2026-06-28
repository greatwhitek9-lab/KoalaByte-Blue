# Koala Kombat Kruisin’

**Koala Kombat Kruisin’** is the KoalaByte Blue passive RF survey and mapping tool. It is built for authorized Wi-Fi/BLE site surveys, access point mapping, BLE survey walks, GPS-tagged export files, and optional WiGLE upload.

It is an observation-only workflow. It does not join Wi-Fi networks, pair with Bluetooth devices, or start service-level interaction.

## Survey node roles

Koala Kombat Kruisin’ now supports a small node mesh:

```text
Raspberry Pi 3B+       -> main Wi-Fi survey element using Linux Wi-Fi tools
Raspberry Pi 3B+ BLE   -> local secondary BLE survey node using BlueZ/Bleak
ESP32-S3 DualEye       -> secondary Wi-Fi + BLE survey node over USB CDC JSON
Heltec T114 / nRF52840 -> primary BLE + GNSS node over USB CDC JSON
```

The Pi remains the coordinator and writes the final JSONL, CSV, GeoJSON, and WiGLE files. ESP32-S3 and Heltec can contribute additional observations as radio nodes. Heltec T114 remains the preferred GNSS source when GPS logging is enabled.

## Menu path

```text
Main Canopy
  Koala Kombat Kruisin’
    Kruisin’ Status
    Wi-Fi AP Survey
    BLE Survey
    Wi-Fi + BLE Survey
    Kruisin’ GPS Status
    Kruisin’ Export Files
    Kruisin’ WiGLE Upload
```

## What it records

For Wi-Fi AP survey records:

```text
SSID
BSSID
RSSI / signal
channel
frequency
security summary
node_id / node_role / transport
latitude / longitude / altitude / accuracy when GPS is armed
first-seen timestamp
```

For BLE survey records:

```text
BLE address
advertised name when available
RSSI when available
node_id / node_role / transport
latitude / longitude / altitude / accuracy when GPS is armed
first-seen timestamp
```

## Output files

Each survey writes files under:

```text
logs/koala_kombat_kruisin/
```

Typical outputs:

```text
koala_kombat_kruisin_<timestamp>.jsonl
koala_kombat_kruisin_wifi_<timestamp>.csv
koala_kombat_kruisin_ble_<timestamp>.csv
koala_kombat_kruisin_<timestamp>.geojson
koala_kombat_kruisin_wigle_<timestamp>.csv
koala_kombat_kruisin_status.json
```

External node JSONL drop-in folder:

```text
logs/koala_kombat_kruisin/nodes/
```

## CLI usage

Readiness/status:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kombat_kruisin.py status
```

Wi-Fi AP survey only:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kombat_kruisin.py wifi-survey
```

BLE survey only:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kombat_kruisin.py ble-survey
```

Combined Wi-Fi + BLE survey:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kombat_kruisin.py survey
```

Export files:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kombat_kruisin.py export
```

Dry-run WiGLE upload, builds the WiGLE CSV but does not upload:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kombat_kruisin.py wigle-upload --dry-run
```

## Node setup

The Pi Wi-Fi scan is the main Wi-Fi survey path. To add the ESP32-S3 and Heltec as serial survey nodes, set whichever ports are present:

```bash
export KOALA_KOMBAT_NODE_MESH=1
export KOALA_KOMBAT_ESP32_PORT=/dev/ttyACM1
export KOALA_KOMBAT_HELTEC_PORT=/dev/ttyACM0
```

Common aliases are also accepted:

```text
KOALABYTE_ESP32_PORT / ESP32_PORT
KOALABYTE_PRIMARY_BLE_PORT / KOALABYTE_HELTEC_USB_PORT / HELTEC_PORT
```

New ESP32-S3 DualEye firmware emits:

```text
wifi_ap_seen
ble_seen
koala_kombat_node_status
wifi_survey_status
```

Heltec T114 contributes BLE observations and GNSS events through the existing combined-safe USB CDC JSON stream.

## GPS setup

GPS enrichment is opt-in. Use either the protected Heltec T114 GNSS path:

```bash
export KOALA_KOMBAT_GPS_LOGGING=1
```

or fixed bench/lab coordinates for indoor testing:

```bash
export KOALA_KOMBAT_FIXED_LAT=39.0001
export KOALA_KOMBAT_FIXED_LON=-76.0001
export KOALA_KOMBAT_FIXED_ACCURACY=25
```

## WiGLE upload

WiGLE upload is blocked unless it is explicitly armed and credentials are present:

```bash
export KOALA_KOMBAT_WIGLE_UPLOAD=1
export WIGLE_API_NAME=<your-wigle-api-name>
export WIGLE_API_TOKEN=<your-wigle-api-token>
PYTHONPATH=pi-companion python3 scripts/run_koala_kombat_kruisin.py wigle-upload
```

## Smoke check

The smoke check does not run a live Wi-Fi or BLE survey. It verifies the tool imports, fixed GPS readiness, and WiGLE row formatting:

```bash
PYTHONPATH=pi-companion python3 scripts/check_koala_kombat_kruisin.py
```

## Safety boundary

Koala Kombat Kruisin’ is for lawful owned-space surveys, defensive RF mapping, and authorized lab/site documentation. Do not run it where you do not have permission to collect Wi-Fi/BLE observation metadata or upload it to third-party services.
