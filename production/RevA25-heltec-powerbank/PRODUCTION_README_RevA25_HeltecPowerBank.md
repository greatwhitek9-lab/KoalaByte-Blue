# KoalaByte Blue RevA25 Heltec Power-Pack Production Package

## Current production target

This package is the current source of truth for the KoalaByte Blue stacked Raspberry Pi 3B+ production-style build.

Primary BLE/radio/GNSS hardware:

```text
Heltec Mesh Node T114 / nRF52840 + SX1262 LoRa board
```

The build is **Heltec T114 based**, **no-custom-PCB**, and powered from a regulated **USB portable power pack / power bank**. It does not use the Nordic nRF52840 USB Dongle as the production BLE board, and it does not use loose 18650 cells, a 2S holder, a BMS, a fuse/switch/buck stack, or raw battery wiring.

## Architecture

```text
Top antenna / RF area:  Heltec LoRa antenna, Heltec 2.4 GHz antenna if exposed, ESP32-S3 2.4 GHz antenna
Front/UI layer:         ESP32-S3 DualEye module, 2x round 1.28 in LCDs, mic path
Radio/GNSS layer:       Heltec Mesh Node T114 / nRF52840 + SX1262 LoRa board
CAN service layer:      Optional InnoMaker USB-to-CAN kit
Main computer layer:    Raspberry Pi 3 Model B+
Power source:           Regulated USB portable power pack / power bank
Controls:               Six-button front panel wired to Raspberry Pi GPIO
Audio:                  8 ohm 2 W mini speaker
Enclosure:              Optional 3D printed eucalyptus-green koala-ear case / stacked frame
```

## Production BOM

Use only the current Heltec/power-pack BOM:

```text
production/RevA25-heltec-powerbank/BOM_RevA25_HeltecPowerBank.csv
```

The BOM includes the Raspberry Pi 3B+, ESP32-S3 DualEye, Heltec Mesh Node T114, six-button front panel, speaker, ESP32 antenna path, Heltec LoRa antenna path, optional Heltec 2.4 GHz antenna path, regulated USB portable power pack, short USB power/data cables, optional powered USB hub, cabling, fasteners, frame plates, optional printed enclosure parts, and the optional InnoMaker USB to CAN Converter kit.

The BOM does **not** require the Nordic nRF52840 USB Dongle, loose 18650 cells, a 2S holder, a 2S BMS, a battery fuse holder, a battery switch, a PD trigger board, a buck converter, or raw lithium battery wiring.

## Antenna paths

Use the general production antenna wiring diagram:

```text
production/WIRING_DIAGRAM_ANTENNAS.md
production/WIRING_DIAGRAM_ANTENNAS.svg
```

Practical antenna routing:

```text
Heltec T114 LoRa connector
  -> short IPEX/U.FL/MHF coax pigtail if needed
  -> case-mounted SMA/RP-SMA bulkhead if used
  -> region-matched LoRa antenna, for example 915 MHz in the US or 868 MHz where legal

Heltec T114 2.4 GHz connector, if exposed on your board revision
  -> short IPEX/U.FL/MHF coax pigtail
  -> external 2.4 GHz Wi-Fi/BLE antenna

ESP32-S3 DualEye 2.4 GHz connector
  -> short IPEX/U.FL/MHF1 coax pigtail
  -> case-mounted SMA/RP-SMA bulkhead if used
  -> external 2.4 GHz Wi-Fi/BLE antenna
```

Do not swap LoRa and 2.4 GHz antennas. Do not solder random wire to RF pads. Use the board vendor's documented connector/selector path.

## USB power-pack power path

The current main production power source is:

```text
Regulated USB portable power pack / power bank, 5 V capable, high-current output recommended
```

Recommended path:

```text
USB portable power pack
  -> regulated USB-A or USB-C output
  -> short quality USB power cable
  -> Raspberry Pi 3B+ micro-USB power input

Raspberry Pi USB ports or optional powered USB hub
  -> Heltec Mesh Node T114
  -> ESP32-S3 DualEye
  -> optional InnoMaker USB-to-CAN adapter
```

Validation requirements:

- Use the power pack's normal regulated USB output only.
- Do not open the power pack or route raw lithium voltage inside the device.
- Do not use the old 2x18650/BMS/fuse/switch/buck wiring stack.
- Use a short low-resistance Pi power cable.
- If the Pi shows undervoltage warnings or USB devices disconnect, use a better cable, a higher-current power-pack output, or a powered USB hub for accessories.

## Optional InnoMaker Koala Kan Kommander path

Physical path:

```text
Raspberry Pi 3B+ USB host
  -> short internal USB cable
  -> InnoMaker USB to CAN Converter kit
  -> adapter-side CAN_H / CAN_L / GND / optional SHIELD
  -> authorized bench harness or owned-device test network
```

Mechanical requirements:

1. Do not use the earlier circular CAN panel port.
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
firmware/t114-combined-safe/
pi-companion/
scripts/
```

Main companion features:

- `killerkoala` AI companion vocabulary and XP leveling.
- `eucalyptus` always-on passive Bluetooth/BLE scanner/logger naming and config.
- T114 primary BLE/GNSS/LoRa status path.
- Koala BlueZ local adapter inventory/status/discovery/monitor helpers.
- Koala Kapture passive metadata capture.
- Koala Kry offline metadata replay/report pipeline.
- Didgeridoo/Meshtastic status paths.
- Koala Kan Kommander passive InnoMaker USB-to-CAN status/listen/report workflow.
- Menu display sync, AI-face idle return, KoalaByte Doctor, field readiness checks, and release/log helpers.

## One-shot validation and install flow

Run this first from the repository root:

```bash
bash scripts/install_koalabyte_one_shot.sh --check-only
```

Then run the full install when ready:

```bash
bash scripts/install_koalabyte_one_shot.sh
```

Useful checks:

```bash
python3 scripts/check_repo_readiness.py
PYTHONPATH=pi-companion python3 scripts/check_field_readiness.py
PYTHONPATH=pi-companion python3 scripts/check_koalabyte_version_handshake.py
bash scripts/koalabyte_doctor.sh --quick
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
- Serial JSON includes the ESP32 2.4 GHz antenna readiness field.

## Heltec T114 flashing / status

The Heltec T114 is the production radio/GNSS board. Use the combined-safe profile:

```bash
T114_PLUG_FLASH_PROFILE=combined-safe bash scripts/install_koalabyte_one_shot.sh
```

If you are only checking readiness:

```bash
bash scripts/flash_t114_when_plugged.sh --check-only
python3 scripts/discover_koalabyte_ports.py --profile heltec
```

## Raspberry Pi companion install

```bash
bash scripts/install_pi.sh
```

The installer creates/updates the Pi companion virtual environment, installs Python dependencies, runs `compileall`, and runs repository readiness checks.

## Safety boundary

This production package is for lawful owned-device labs and defensive review. Do not connect the CAN adapter, BLE/radio tools, LoRa path, or GPS/GNSS workflows to systems, vehicles, radios, networks, or devices you do not own or do not have permission to test.
