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

Safety boundary: Eucalyptus Mode is a status and visualization layer for passive Bluetooth observations. It does not start pairing, connection, probing, disruption, access, or offensive workflows.

## Koalagotchi screen behavior

When selected, Eucalyptus Mode opens a full-color, high-resolution Koalagotchi screen:

- A long eucalyptus branch stretches from one side of the display to the other.
- KillerKoala walks back and forth across the branch.
- New passive Bluetooth observations become eucalyptus leaves.
- KillerKoala stops to eat the leaves, representing Bluetooth data being logged.
- Contentment rises when new Bluetooth observations appear.
- After 3 minutes with no new observations, contentment falls.
- When dormant, KillerKoala starts throwing a boomerang and grumbling in Aussie cyberpunk style.

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
    "mode": "passive_ble_observation"
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

The menu item appears under **Bluetooth Tools** as:

```text
Eucalyptus Mode
```

It uses command key:

```text
eucalyptus_mode
```

The existing eucalyptus service control actions remain available:

```text
eucalyptus status
eucalyptus start
eucalyptus stop
eucalyptus restart
eucalyptus upload-status
```

## Boomerang parity setting

Boomerang now has matching behavior settings in `config.default.json`, including verbal alerts, XP reward per logged record, output paths, and stay-open behavior. Boomerang remains the manual camera-awareness logbook and is separate from Eucalyptus Mode.

## Safety boundary

`eucalyptus` and `Eucalyptus Mode` are passive observation and logging workflows only. They are not connection, pairing, disruption, access, or offensive workflows.
