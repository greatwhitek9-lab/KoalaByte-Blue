# RevA17+ KillerKoala Companion Vocabulary

## Purpose

KillerKoala now uses a larger vocabulary engine instead of a short fixed phrase list.

The companion is designed around this split:

```text
ESP32-S3 DualEye:
  wake word front end
  short command aliases
  serial event/status reporting

Raspberry Pi:
  large KillerKoala vocabulary engine
  Aussie/cyberpunk response variation
  XP and rank tone changes
  anti-repeat phrase rotation
  menu/action execution
```

The goal is for KillerKoala to sound like a real companion, not a toy that barks the same five phrases.

## Implementation files

```text
pi-companion/koalablue/killerkoala_vocabulary.py
firmware/esp32-dualeye/voice_commands/README.md
firmware/esp32-dualeye/voice_commands/killerkoala_multinet_aliases.csv
scripts/run_killerkoala_voice.py
pi-companion/config.default.json
pi-companion/koalablue/menu_catalog.py
```

## Voice profile

```text
Name: killerkoala
Accent: Australian male
Attitude: gruff, cheeky, cyberpunk lab companion with legal-scope discipline
TTS hint: en-AU male, low pitch, gravelly delivery, confident but not hostile
Architecture: ESP32-S3 voice front end + Raspberry Pi companion brain
```

The repository stores voice metadata, command aliases, and written response text. It does not bundle a commercial voice model or audio files.

## XP ranks

```text
Noob   = 0+ XP, cautious and rough beginner tone
Hacker = 75+ XP, sharper and more confident tone
Legend = 250+ XP, cocky controlled veteran tone
```

## Anti-repeat behavior

The vocabulary engine now tracks recently used lines per event/rank in:

```text
logs/killerkoala/killerkoala_phrase_history.json
```

By default, it avoids recently selected lines from the last 24 selections for that event/rank. If the recent-history window is exhausted, it safely falls back to the full candidate pool.

Use `--no-history` for deterministic previews that do not read or write phrase history.

## Candidate scale

KillerKoala now builds responses from event-specific lines plus Aussie/cyberpunk opener combinations. The manifest includes the candidate counts per event/rank and an estimated total line count.

Write the manifest:

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py --manifest
```

Output:

```text
logs/killerkoala/killerkoala_vocabulary_manifest.json
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

Preview without updating history:

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py scan_complete --xp 100 --no-history
```

## ESP32-S3 voice-command alias pack

The ESP32-S3 voice front-end plan is recorded in:

```text
firmware/esp32-dualeye/include/config.h
firmware/esp32-dualeye/voice_commands/killerkoala_multinet_aliases.csv
```

The alias pack maps phrases such as:

```text
killerkoala give the air a squiz -> bluez_scan
killerkoala suss the bluetooth stack -> bluez_status
killerkoala bag the beacons -> koala_kapture
killerkoala chew through the logs -> koala_kry
killerkoala call it a day -> shutdown
```

The ESP32-S3 should send recognized command IDs or recognized text to the Raspberry Pi. The Pi companion then chooses the long-form KillerKoala response from the large vocabulary engine.

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

`ear_tag_tx_lab` is retained as the internal event key for compatibility. User-facing text calls that workflow **KoalaByte Lab**.

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
give_it_a_squiz -> bluez_status
bag_the_beacons -> capture_saved
chew_the_logs -> koala_kry
```

## Menu entry

The main menu includes:

```text
KillerKoala Voice
```

## Safety scope

KillerKoala vocabulary is for authorized lab narration, local diagnostics, status reactions, companion banter, and defensive workflow guidance. It should not encourage out-of-scope access, device impersonation, disruption, or captured-signal replay.
