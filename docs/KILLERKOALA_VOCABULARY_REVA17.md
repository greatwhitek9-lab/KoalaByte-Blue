# RevA17 killerkoala Companion Vocabulary

## Purpose

RevA17 adds a structured vocabulary engine for the `killerkoala` AI companion.

The companion now has:

- Australian male voice-profile metadata.
- Edgy, gruff cyberpunk lab-companion attitude.
- XP-based confidence scaling.
- Event reactions for boot, scan, capture, BlueZ, KoalaByte Lab, Koala Kry, errors, shutdown, and level-up events.
- Inquiry responses for status and help requests.
- A manifest writer for UI/TTS integration.

## Implementation files

```text
pi-companion/koalablue/killerkoala_vocabulary.py
scripts/run_killerkoala_voice.py
pi-companion/config.default.json
pi-companion/koalablue/menu_catalog.py
```

## Voice profile

```text
Name: killerkoala
Accent: Australian male
Attitude: edgy, gruff, cyberpunk lab companion
TTS hint: en-AU male, low pitch, gravelly delivery, confident but not hostile
```

The repository stores voice metadata and written response text. It does not bundle a commercial voice model or audio files.

## XP ranks

```text
Noob   = 0+ XP, cautious and rough beginner tone
Hacker = 75+ XP, sharper and more confident tone
Legend = 250+ XP, cocky controlled veteran tone
```

## Preview commands

Preview default status response:

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py status
```

Preview a higher-rank scan response:

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py scan_start --xp 100
```

Preview Legend tone:

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py bluez_status --xp 300
```

Write manifest:

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py --manifest
```

Output:

```text
logs/killerkoala/killerkoala_vocabulary_manifest.json
```

## Supported events

```text
boot
scan_start
scan_complete
device_found
capture_saved
error
level_up
bluez_status
ear_tag_tx_lab
koala_kry
shutdown
inquiry_status
inquiry_help
```

`ear_tag_tx_lab` is retained as the internal event key for compatibility. User-facing text now calls that workflow **KoalaByte Lab**.

Aliases include:

```text
status -> inquiry_status
help -> inquiry_help
scan -> scan_start
bluez -> bluez_status
capture -> capture_saved
kry -> koala_kry
ear_tag -> ear_tag_tx_lab
shutdown_confirm -> shutdown
```

## Menu entry

The main menu now includes:

```text
KillerKoala Voice
```

## Safety scope

killerkoala vocabulary is for authorized lab narration, local diagnostics, status reactions, and defensive workflow guidance. It should not be used to encourage out-of-scope access, device impersonation, disruption, or captured-signal replay.
