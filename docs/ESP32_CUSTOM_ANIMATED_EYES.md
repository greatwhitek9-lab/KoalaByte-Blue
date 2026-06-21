# ESP32-S3 DualEye Custom Animated Eyes

KoalaByte Blue supports runtime-customizable KillerKoala eyes on the ESP32-S3 DualEye display.

The Pi can send a serial JSON command to change:

- eye look
- left eye color
- right eye color
- animation style
- brightness
- preview mode/mood

## Dependencies

The animated eye firmware is part of the ESP32-S3 DualEye PlatformIO project.

```bash
bash scripts/setup_esp32_tools.sh
NO_MONITOR=1 bash scripts/flash_esp32.sh
```

`flash_all_components.sh --all` also runs the ESP32 tool setup before flashing the ESP32 firmware. PlatformIO is installed by `scripts/setup_esp32_tools.sh` when missing.

The serial helper uses `pyserial`. The Pi companion requirements already include `pyserial`, and the helper will also tell you to install it if it is missing.

## Supported looks

```text
round
cyber
slit
sleepy
angry
star
heart
x
```

## Supported animations

```text
static
idle
pulse
blink
scan
glitch
sleepy
```

## Color format

Use RGB hex:

```text
#A54BFF
#32FF71
#FF9A26
```

## Serial JSON command

```json
{"type":"eye_style","look":"cyber","left_color":"#A54BFF","right_color":"#32FF71","animation":"pulse","brightness":100,"mode":"eucalyptus","mood":"custom"}
```

Reset to the default KillerKoala look:

```json
{"type":"eye_style","reset":true}
```

Ask the ESP32 for the current eye style:

```json
{"type":"eye_status"}
```

The ESP32 replies with:

```text
eye_style_ack
eye_style
```

## Helper script

Preview payload without sending:

```bash
PYTHONPATH=pi-companion python3 scripts/set_esp32_eyes.py --preset legend --preview-only
```

Send to a connected ESP32-S3 DualEye:

```bash
python3 scripts/set_esp32_eyes.py \
  --port /dev/ttyUSB0 \
  --preset killerkoala
```

Create a custom look:

```bash
python3 scripts/set_esp32_eyes.py \
  --port /dev/ttyUSB0 \
  --look slit \
  --left '#A54BFF' \
  --right '#32FF71' \
  --animation scan \
  --brightness 95
```

Save a reusable profile JSON:

```bash
python3 scripts/set_esp32_eyes.py \
  --preset greatwhite \
  --save-profile firmware/esp32-dualeye/themes/greatwhite_eyes.json \
  --preview-only
```

## Built-in presets

```text
killerkoala  cyber purple/green pulse
eucalyptus   round purple/green pulse
boomerang    angry orange/yellow scan
greatwhite   slit blue/white scan
sleepy       sleepy blue sleepy
love         heart pink pulse
legend       star yellow/green glitch
```

## Pi-to-ESP32 screen command integration

The existing `screen` command also accepts eye fields:

```json
{
  "type":"screen",
  "mode":"eucalyptus",
  "mood":"calm",
  "eye_look":"cyber",
  "left_eye":"#A54BFF",
  "right_eye":"#32FF71",
  "eye_animation":"pulse",
  "eye_brightness":100
}
```

This lets the Pi companion match the eyes to KillerKoala moods, XP rank, Eucalyptus mode, Boomerang mode, or future custom profiles.

## Firmware files

```text
firmware/esp32-dualeye/src/koalagotchi_mode_screens.h
firmware/esp32-dualeye/src/koalagotchi_mode_screens.cpp
firmware/esp32-dualeye/src/main.cpp
scripts/set_esp32_eyes.py
scripts/setup_esp32_tools.sh
```
