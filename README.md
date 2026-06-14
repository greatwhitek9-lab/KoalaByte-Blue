# KoalaByte Blue / killerkoala AI Companion Firmware RevA2

eap32-s3 dual eye firmware and Raspberry Pi companion software for the **KoalaByte Blue Pi3B+ stacked research device**.

## Ready-to-flash status

The ESP32-S3 DualEye firmware is a PlatformIO project and can be built/flashed directly from `firmware/esp32-dualeye/`. See [`docs/FLASHING.md`](docs/FLASHING.md) for the full step-by-step guide.

Quick flash:

```bash
./scripts/flash_esp32.sh
```

## What is included

- ESP32-S3 DualEye firmware scaffold with USB serial JSON protocol.
- Mic wake path enabled by default with wake word **killerkoala**.
- Raspberry Pi companion dependency/config files.
- Always-on passive BLE capture configuration under `/blecaptures/`.
- Production BOM and safety-test CSV files.
- Flashing guide and production-file manifest.

## Production package

The no-custom-PCB physical production files are staged under:

```text
production/RevA1-nrf52840-dongle/
```

The full binary PDF/image/ZIP production package is also available in the companion ZIP delivered from ChatGPT. The repository currently contains the text production artifacts and manifest.

## Safety boundary

This package is for authorized Bluetooth research, BLE inventory, local logging, AI companion behavior, and nonfunctional lab placeholders. It does not include working exploit, bypass, jamming, injection, brute-force, or unauthorized access code.

## Main Pi commands

```text
scan              Run a safe BLE inventory scan
summary           Summarize observed BLE devices
show              Show device table
level/status      Show XP and rank
report            Write Markdown report
wake killerkoala  Test wake-word flow
lab               Password-gated placeholder lab menu
quit              Exit
```

## First flash

```bash
git clone https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
python3 -m pip install --user platformio
./scripts/flash_esp32.sh
```
