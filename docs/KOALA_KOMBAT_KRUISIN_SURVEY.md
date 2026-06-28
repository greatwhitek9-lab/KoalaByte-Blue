# Koala Kombat Kruisin’

**Koala Kombat Kruisin’** is the KoalaByte Blue passive RF survey and mapping tool. It is built for authorized Wi-Fi/BLE site surveys, access point mapping, BLE survey walks, GPS-tagged export files, and optional WiGLE upload.

It is a passive observation workflow. It does not join Wi-Fi networks, pair with Bluetooth devices, probe services, deauth clients, spoof identifiers, jam RF, or attempt access.

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
latitude / longitude / altitude / accuracy when GPS is armed
first-seen timestamp
```

For BLE survey records:

```text
BLE address
advertised name when available
RSSI when available
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
