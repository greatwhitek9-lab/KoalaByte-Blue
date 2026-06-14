# KoalaByte Blue / killerkoala AI Companion Firmware RevA2

GitHub-ready firmware and Raspberry Pi companion software for the **KoalaByte Blue Pi3B+ stacked research device**.

## RevA1 changes

- AI companion renamed to **killerkoala**.
- Wake word set to **`killerkoala`**.
- ESP32-S3 DualEye mic wake is **enabled by default** at the firmware-configuration level.
- Pi companion uses gruff/cyberpunk-style prompts and responses.
- Added XP and rank progression:
  - **Noob**: beginner tier, 0+ XP
  - **Hacker**: middle tier, 100+ XP
  - **Legend**: final tier, 300+ XP
- Safe completed actions award XP.
- Research Lab placeholders remain intentionally blocked and nonfunctional.


## Repository name

Recommended GitHub repository name: `KoalaByte-Blue`  
Display name: **KoalaByte Blue**

This repository is a no-custom-PCB firmware/software stack for the Pi 3B+ + ESP32-S3 DualEye + Nordic nRF52840 Dongle research platform.

## Important hardware note

The ESP32 firmware has mic wake enabled by default, but the exact ESP32-S3 DualEye microphone I2S pin mapping is board-revision-specific. Until `MIC_I2S_BCLK_PIN`, `MIC_I2S_WS_PIN`, and `MIC_I2S_DIN_PIN` are set in `firmware/esp32-dualeye/include/config.h`, the ESP32 boots safely and reports:

```json
{"type":"voice_backend","status":"mic_enabled_pin_mapping_required"}
```

That means the wake-word path is wired into the firmware/software architecture, but real hardware voice capture requires confirming the DualEye board's audio example/schematic pin values.


## Ready-to-flash status

The ESP32-S3 DualEye firmware is a PlatformIO project and can be built/flashed directly from `firmware/esp32-dualeye/`. See [`docs/FLASHING.md`](docs/FLASHING.md) for the full step-by-step guide.

Quick flash:

```bash
./scripts/flash_esp32.sh
```

## Production package

The latest no-custom-PCB physical production files are included under:

```text
production/RevA1-nrf52840-dongle/
```

See [`docs/PRODUCTION_FILES.md`](docs/PRODUCTION_FILES.md).

## Repository layout

```text
firmware/esp32-dualeye/      ESP32-S3 DualEye PlatformIO firmware
pi-companion/koalablue/      Raspberry Pi 3B+ Python companion app
docs/                        Protocol and lab policy docs
scripts/install_pi.sh        Pi setup helper
.github/workflows/           Python syntax-check workflow
```

## Pi setup

```bash
cd pi-companion
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m koalablue.app --no-serial
```

With ESP32 connected:

```bash
python -m koalablue.app --serial /dev/ttyACM0
```

If your module path is `koalablue`, use:

```bash
python -m koalablue.app --serial /dev/ttyACM0
```

## Main commands

```text
scan              Run a safe BLE inventory scan
summary           Summarize observed BLE devices
show              Show device table
level/status      Show XP and rank
report            Write Markdown report
wake killerkoala  Test the wake-word flow from the Pi console
lab               Password-gated Research Lab placeholder menu
quit              Exit
```

## Safety boundary

This package contains placeholders for offensive/aggressive lab actions, but they intentionally return `BLOCKED_PLACEHOLDER` and contain no working offensive code. They are present only to reserve UI/API space for future authorized modules that must be implemented under applicable law and safety policy.

## Flash ESP32

```bash
cd firmware/esp32-dualeye
pio run -t upload
pio device monitor -b 115200
```

## Progression system

The Pi app stores XP in `logs/killerkoala_profile.json`.

| Rank | XP threshold |
|---|---:|
| Noob | 0 |
| Hacker | 100 |
| Legend | 300 |

XP is awarded for completed safe actions such as scans, report generation, inventory review, and voice-wake tests.


## RevA2 always-on BLE capture

RevA2 adds a passive always-on BLE advertisement capture service for the Pi 3B+.
It logs captures under `/blecaptures/` as JSONL and CSV, with raw Bluetooth MAC
addresses enabled by default per the project configuration. WiGLE upload support
is included but disabled until API credentials and a valid location source are
configured. See `docs/BLE_CAPTURE_WIGLE.md`.

Console commands:

```text
alwayson status
alwayson start
alwayson stop
alwayson restart
```

This feature is passive capture only: no connection attempts, no jamming, no
injection, no bypass logic, and no person-tracking profile generation.
