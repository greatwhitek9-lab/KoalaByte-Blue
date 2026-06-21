# KoalaByte Blue RevA25 Production Package

## Current production target

This package is the current source of truth for the KoalaByte Blue stacked Raspberry Pi 3B+ production-style build.

Retained BLE hardware:

```text
Nordic nRF52840 USB Dongle / PCA10059 / NRF52840-DONGLE
```

The build is **dongle-only** and **no-custom-PCB**. It uses off-the-shelf modules, short USB cabling, M2.5 standoffs, a simplified **PIFFA-style 50000 mAh USB portable power bank 22.5 W class** power path, optional 3D printed enclosure parts, and the optional InnoMaker USB to CAN Converter kit for Koala Kan Kommander.

## Architecture

```text
Top antenna / RF area:  ESP32-S3 2.4 GHz antenna opening
Front/UI layer:         ESP32-S3 DualEye module, 2x round 1.28 in LCDs, mic path
BLE/CAN service layer:  Nordic nRF52840 USB Dongle / PCA10059 + optional InnoMaker USB-to-CAN kit
Main computer layer:    Raspberry Pi 3 Model B+
Power source:           PIFFA-style 50000 mAh USB portable power bank through regulated USB output
Controls:               Six-button front panel wired to Raspberry Pi GPIO
Audio:                  8 ohm 2 W mini speaker
Enclosure:              Optional 3D printed eucalyptus-green koala-ear case / stacked frame
```

## Production BOM

Use only the current BOM:

```text
production/RevA17-dongle-only/BOM_RevA17_DongleOnly.csv
```

The BOM includes the Raspberry Pi 3B+, ESP32-S3 DualEye, Nordic nRF52840 USB Dongle, six-button front panel, speaker, ESP32 antenna, **PIFFA-style 50000 mAh USB portable power bank 22.5 W class**, short USB power/data cables, optional powered USB hub, cabling, fasteners, frame plates, optional printed enclosure parts, and the optional InnoMaker USB to CAN Converter kit.

The BOM no longer requires loose 18650 cells, a 2S holder, a 2S BMS, a battery fuse holder, a battery switch, a PD trigger board, or a buck converter for the main production build.

## Simplified power-bank power path

The current main production power source is:

```text
PIFFA-style 50000 mAh USB portable power bank 22.5 W class
```

Recommended path:

```text
PIFFA-style USB power bank
  -> regulated USB-A or USB-C output
  -> short quality USB power cable
  -> Raspberry Pi 3B+ micro-USB power input

Raspberry Pi USB ports or optional powered USB hub
  -> Nordic nRF52840 USB Dongle
  -> ESP32-S3 DualEye
  -> optional InnoMaker USB-to-CAN adapter
```

Validation requirements:

- Use the power bank's normal regulated USB output only.
- Do not open the power bank or route raw lithium voltage inside the device.
- Do not use the old 2x18650/BMS/fuse/switch/buck wiring stack.
- Use a short low-resistance Pi power cable.
- If the Pi shows undervoltage warnings or USB devices disconnect, use a better cable, a higher-current power-bank output, or a powered USB hub for accessories.

## RevA23 InnoMaker Koala Kan Kommander option

Physical path:

```text
Raspberry Pi 3B+ USB host
  -> short internal USB cable
  -> InnoMaker USB to CAN Converter kit
  -> adapter-side CAN_H / CAN_L / GND / optional SHIELD
  -> authorized bench harness or owned-device test network
```

Mechanical requirements:

1. Do **not** use the earlier circular CAN panel port.
2. Mount the InnoMaker converter internally, in the Level 2 USB service bay, or at the side/rear service area.
3. Use a rectangular service slot or internal mount with cable strain relief if the adapter-side CAN connector must be accessible.
4. Keep the adapter and CAN wiring away from antennas, speaker grille, USB cable bends, and the Raspberry Pi GPIO header.
5. Do not wire CAN_H or CAN_L directly to Raspberry Pi GPIO.

Software requirements:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py status --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py listen --interface can0 --duration 10
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py report --interface can0
```

The production plug-in is passive by default and `transmit-placeholder` remains blocked unless the explicit bench-simulator safety gates are satisfied.

## Firmware and software paths

Retained firmware/software paths:

```text
firmware/esp32-dualeye/
firmware/nrf52840-dongle-ear-tag-tx-lab/
pi-companion/
scripts/
```

Main retained companion features:

- `killerkoala` AI companion vocabulary and XP leveling.
- `eucalyptus` always-on passive Bluetooth/BLE scanner/logger naming and config.
- Koala BlueZ local adapter inventory/status/discovery/monitor helpers.
- Koala Kapture passive metadata capture.
- Koala Kry offline metadata replay/report pipeline.
- KoalaByte Lab synthetic owned-device BLE advertisement firmware for the USB Dongle.
- Koala Konnect optional external Bluetooth adapter mode for the USB Dongle.
- Koala Mode Switcher Pi-side controller for preparing and selecting the dongle firmware profile.
- Koala Kan Kommander passive InnoMaker USB-to-CAN status/listen/report workflow.

## Flash-ready validation flow

Run this first from the repository root:

```bash
python3 scripts/check_repo_readiness.py
```

Expected output:

```text
KoalaByte Blue repo readiness check passed.
Ready-to-flash file wiring is present for ESP32, nRF52840 Dongle/DFU, Pi companion, Koala Kan Kommander InnoMaker CAN support, Eucalyptus Mode, Boomerang, the that’s not a knife local guard service, and USB power-bank production power.
```

Primary all-component helper:

```bash
bash scripts/flash_all_components.sh --all
```

Useful alternatives:

```bash
bash scripts/flash_all_components.sh --pi
NO_MONITOR=1 ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --nrf-lab
bash scripts/flash_all_components.sh --all --build-only
bash scripts/flash_all_components.sh --all --smoke
```

## ESP32-S3 DualEye flashing

```bash
bash scripts/flash_esp32.sh
NO_MONITOR=1 ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_esp32.sh
```

Expected behavior:

- KoalaByte Blue animated boot splash appears.
- DualEye firmware emits serial boot JSON.
- Serial JSON includes `"boot_animation":1`.

## Raspberry Pi companion install

```bash
bash scripts/install_pi.sh
```

The installer creates/updates the Pi companion virtual environment, installs Python dependencies, runs `compileall`, and runs `scripts/check_repo_readiness.py`.
