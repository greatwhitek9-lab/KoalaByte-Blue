# KoalaByte Blue / killerkoala AI Companion Firmware RevA4

ESP32-S3 DualEye firmware, Raspberry Pi companion software, and optional Nordic nRF52840 DK lab firmware for the **KoalaByte Blue Pi3B+ stacked research device**.

## Hardware profile

Production compact BLE board:

```text
Nordic nRF52840 Dongle / PCA10059 / NRF52840-DONGLE
```

Optional development/debug board:

```text
Nordic nRF52840 DK / PCA10056
```

Use the DK for development and validation. Keep the Dongle in the final compact physical build.

## Ready-to-flash status

The ESP32-S3 DualEye firmware is a PlatformIO project and can be built/flashed directly from `firmware/esp32-dualeye/`. See [`docs/FLASHING.md`](docs/FLASHING.md).

Quick ESP32 flash:

```bash
bash scripts/flash_esp32.sh
```

The optional nRF52840 DK lab peripheral firmware is an nRF Connect SDK / Zephyr project at:

```text
firmware/nrf52840-dk-lab-peripheral/
```

Quick nRF52840 DK flash:

```bash
bash scripts/flash_nrf52840_dk_lab.sh
```

## What is included

- ESP32-S3 DualEye firmware scaffold with USB serial JSON protocol.
- Mic wake path enabled by default with wake word **killerkoala**.
- Raspberry Pi companion dependency/config files.
- Always-on passive BLE capture configuration under `/blecaptures/`.
- Production BOM and safety-test CSV files.
- Optional nRF52840 DK safe lab-peripheral firmware.
- Flashing guides and production-file manifests.

## Production package

The no-custom-PCB physical production files are staged under:

```text
production/RevA1-nrf52840-dongle/
```

Latest hardware additions:

- `docs/NRF52840_DK_OPTION_REVA4.md`
- `production/RevA1-nrf52840-dongle/BOM_RevA4_Dongle_Plus_DK.csv`

## Safety boundary

This package is for authorized Bluetooth research, BLE inventory, local logging, AI companion behavior, and safe lab validation. It does not include working exploit, bypass, jamming, injection, brute-force, tracking, or unauthorized access code.

## Main Pi commands

```text
scan              Run a safe BLE inventory scan
summary           Summarize observed BLE devices
show              Show device table
level/status      Show XP and rank
report            Write Markdown report
wake killerkoala  Test wake-word flow
lab               Password-gated Authorized Lab Use menu
quit              Exit
```

## First ESP32 flash

```bash
git clone https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
python3 -m pip install --user platformio
bash scripts/flash_esp32.sh
```

## First nRF52840 DK flash

Install Nordic nRF Connect SDK first, then:

```bash
git clone https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
bash scripts/flash_nrf52840_dk_lab.sh
```
