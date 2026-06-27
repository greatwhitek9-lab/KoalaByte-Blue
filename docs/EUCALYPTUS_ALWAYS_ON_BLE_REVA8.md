# Eucalyptus Mode: Koalagotchi Always-On Bluetooth Scanner and Logger

## Action name

The always-on passive Bluetooth/BLE scanner/logger action is now presented in the KoalaByte Blue menu as:

```text
Eucalyptus Mode
```

The lower-level CLI/service name remains:

```text
eucalyptus
```

## Purpose

**Eucalyptus Mode** is KoalaByte Blue's Koalagotchi-style always-on Bluetooth scanner and logger screen for authorized lab use. It watches local passive Eucalyptus Bluetooth/BLE capture logs, turns new observations into eucalyptus leaves, and shows KillerKoala eating those leaves as Bluetooth data snacks.

Eucalyptus can now also build a **GPS-enriched passive BLE trail** from the discovered-device logs. The trail can include coordinates from the protected Heltec T114 GNSS path, or from an explicit fixed lab location supplied by environment variables. WiGLE upload is a separate menu action and remains disabled unless the operator explicitly arms it and provides WiGLE credentials.

Safety boundary: Eucalyptus Mode is a status, visualization, GPS-enrichment, and upload-prep layer for passive Bluetooth observations. It does not start pairing, connection, probing, disruption, access, spoofing, jamming, or offensive workflows.

## Koalagotchi screen behavior

When selected, Eucalyptus Mode opens a full-color, high-resolution Koalagotchi screen:

- A long eucalyptus branch stretches from one side of the display to the other.
- KillerKoala walks back and forth across the branch.
- New passive Bluetooth observations become eucalyptus leaves.
- KillerKoala stops to eat the leaves, representing Bluetooth data being logged.
- Contentment rises when new Bluetooth observations appear.
- After 3 minutes with no new observations, contentment falls.
- When dormant, KillerKoala starts throwing a boomerang and grumbling in Aussie cyberpunk style.

## GPS-enriched Eucalyptus trail

Build a GPS-enriched passive BLE trail and WiGLE-format CSV:

```bash
PYTHONPATH=pi-companion python3 scripts/run_eucalyptus_wigle.py gps-trail
```

Output files:

```text
logs/eucalyptus/eucalyptus_gps_trail_<timestamp>.jsonl
logs/eucalyptus/eucalyptus_wigle_ble_<timestamp>.csv
logs/eucalyptus/eucalyptus_wigle_status.json
```

GPS enrichment is opt-in. To use the protected Heltec T114 GNSS path, unlock the protected location gate in the same shell/session and arm Eucalyptus GPS logging:

```bash
PYTHONPATH=pi-companion python3 scripts/run_location_password_gate.py unlock
export KOALABYTE_EUCALYPTUS_GPS_LOGGING=1
```

For bench testing without live GNSS, set a fixed lab coordinate:

```bash
export KOALABYTE_EUCALYPTUS_FIXED_LAT=39.0001
export KOALABYTE_EUCALYPTUS_FIXED_LON=-76.0001
export KOALABYTE_EUCALYPTUS_FIXED_ACCURACY=25
```

## WiGLE upload

Check readiness:

```bash
PYTHONPATH=pi-companion python3 scripts/run_eucalyptus_wigle.py status
```

Dry-run CSV creation without uploading:

```bash
PYTHONPATH=pi-companion python3 scripts/run_eucalyptus_wigle.py wigle-upload --dry-run
```

Actual upload requires explicit enablement and credentials:

```bash
export KOALABYTE_EUCALYPTUS_WIGLE_UPLOAD=1
export WIGLE_API_NAME=<your-wigle-api-name>
export WIGLE_API_TOKEN=<your-wigle-api-token>
PYTHONPATH=pi-companion python3 scripts/run_eucalyptus_wigle.py wigle-upload
```

The menu item is:

```text
Eucalyptus WiGLE Upload
```

## Graphics settings

The default renderer is full-color Pygame at quality resolution:

```json
{
  "display_name": "Eucalyptus Mode",
  "full_color_graphics": true,
  "quality_resolution": {
    "default_width": 800,
    "default_height": 480,
    "fullscreen_default": true,
    "fps": 30
  }
}
```

Run it directly:

```bash
PYTHONPATH=pi-companion python3 scripts/run_eucalyptus_cyberpet.py
```

Run in a window for desktop testing:

```bash
PYTHONPATH=pi-companion python3 scripts/run_eucalyptus_cyberpet.py --windowed --width 800 --height 480
```

Run terminal fallback:

```bash
PYTHONPATH=pi-companion python3 scripts/run_eucalyptus_cyberpet.py --terminal
```

Smoke test without display:

```bash
PYTHONPATH=pi-companion python3 scripts/check_eucalyptus_cyberpet.py
PYTHONPATH=pi-companion python3 scripts/check_eucalyptus_wigle.py
```

## Default storage

Eucalyptus passive Bluetooth capture storage:

```text
/blecaptures/
```

Eucalyptus Mode Koalagotchi state and events:

```text
logs/eucalyptus_mode/state.json
logs/eucalyptus_mode/events.jsonl
```

Eucalyptus GPS/WiGLE artifacts:

```text
logs/eucalyptus/eucalyptus_gps_trail_<timestamp>.jsonl
logs/eucalyptus/eucalyptus_wigle_ble_<timestamp>.csv
logs/eucalyptus/eucalyptus_wigle_status.json
```

## Config keys

See `pi-companion/config.default.json`:

```json
{
  "action_names": {
    "always_on_ble_scanner_logger": "eucalyptus",
    "eucalyptus_mode": "Eucalyptus Mode"
  },
  "eucalyptus": {
    "display_name": "eucalyptus",
    "enabled": true,
    "capture_dir": "/blecaptures",
    "mode": "passive_ble_observation",
    "wigle_upload_enabled": false,
    "wigle_api_name_env": "WIGLE_API_NAME",
    "wigle_api_token_env": "WIGLE_API_TOKEN"
  },
  "eucalyptus_mode": {
    "display_name": "Eucalyptus Mode",
    "description": "Koalagotchi always-on Bluetooth scanner and logger screen.",
    "idle_behavior": {"idle_seconds_before_grumble": 180},
    "full_color_graphics": true
  }
}
```

## Menu integration

The Eucalyptus submenu now includes:

```text
Eucalyptus Canopy Status
Eucalyptus Canopy Start
Eucalyptus Canopy Stop
Eucalyptus Canopy Restart
Eucalyptus GPS Trail
Eucalyptus Upload Trail
Eucalyptus WiGLE Upload
Eucalyptus Koalagotchi Mode
```

Command keys:

```text
eucalyptus status
eucalyptus start
eucalyptus stop
eucalyptus restart
eucalyptus gps-trail
eucalyptus upload-status
eucalyptus wigle-upload
eucalyptus_mode
```

## Boomerang parity setting

Boomerang has matching behavior settings in `config.default.json`, including verbal alerts, XP reward per logged record, output paths, and stay-open behavior. Boomerang remains the manual camera-awareness logbook and is separate from Eucalyptus Mode.

## Safety boundary

`eucalyptus` and `Eucalyptus Mode` are passive observation and logging workflows only. Location enrichment is opt-in, and WiGLE upload requires explicit operator enablement and credentials. They are not connection, pairing, disruption, access, spoofing, jamming, or offensive workflows.
