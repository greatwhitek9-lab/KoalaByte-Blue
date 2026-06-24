# KoalaByte Blue V2 Heltec Edition

KoalaByte Blue V2 Heltec Edition is the Raspberry Pi + ESP32-S3 DualEye + Heltec T114 build of the KillerKoala cyber companion. It is built for lawful owned-device labs, defensive Bluetooth observation, Didgeridoo mesh status, front-panel UI, AntEater passive BLE review, and optional isolated CAN bench work.

Use it only on your own equipment, your own lab traffic, or systems you have written permission to test.

---

## What this branch is for

This branch is the deployable Heltec Edition profile for:

- Raspberry Pi 3B+ as the Linux companion host.
- Waveshare ESP32-S3-DualEye-LCD-1.28 as the face, eyes, buttons, UI display, and secondary local BLE node.
- Heltec Mesh Node T114 as the primary BLE board, LoRa board, and Didgeridoo mesh board.
- InnoMaker USB-to-CAN adapter as an optional isolated CAN bench accessory.
- USB power bank / regulated USB power, not raw battery voltage.

No custom PCB is required for this profile.

---

## Hardware layout

| Part | Role | Connection |
|---|---|---|
| Raspberry Pi 3B+ | Main host, menus, logs, voice, services | Pi power + USB devices |
| ESP32-S3 DualEye | Eyes, face, UI, buttons, secondary BLE | USB data cable |
| Heltec Mesh Node T114 | Primary BLE, LoRa, Didgeridoo mesh, GNSS-aware workflows | USB-C data cable |
| InnoMaker USB-to-CAN | Optional isolated bench CAN work | USB data cable |
| Power bank | Main regulated power source | USB power output |

Power rule: do **not** feed raw lithium battery voltage into the Pi, ESP32-S3, Heltec T114, or CAN adapter.

---

## Antenna routing

Use three external antenna paths:

```text
Heltec T114 LoRa connector -> region-matched LoRa antenna
Heltec T114 2.4 GHz connector -> additional case-mounted 2.4 GHz antenna
ESP32-S3 DualEye 2.4 GHz connector -> ESP32-S3 2.4 GHz antenna
Raspberry Pi 3B+ -> no required external antenna; optional USB wireless adapter only
```

The extra 2.4 GHz antenna goes to the **Heltec T114**, not the Pi. A Pi USB wireless adapter is optional only and must not block firmware, installer, CI, or readiness.

Check antenna readiness with:

```bash
bash scripts/configure_koalabyte_external_antennas.sh --check-only
python3 scripts/check_external_antenna_readiness.py
```

---

## Menu map

The main field menus are intentionally simple:

| Main menu item | What it does |
|---|---|
| Eucalyptus | Passive BLE logger and Koalagotchi-style BLE screen. |
| Bluetooth Tools | Local safe BLE inventory, status, defensive review, AntEater, and lab-only helpers. |
| Didgeridoo | All mesh/T114/Meshtastic/GNSS actions. |
| CAN Bench Tools | InnoMaker USB-to-CAN manifest and isolated bench-simulator workflow. |
| Reports & Reviews | Report generators, Boomerang, and defensive review templates. |
| System / Companion | KillerKoala voice/status, buttons, settings, and helper controls. |

The mesh stack lives under **Didgeridoo**. That submenu contains T114 controller checks, T114 status, Didgeridoo status, Didgeridoo nodes, Didgeridoo GPS info, protected location gate status, and protected GNSS current fix.

---

## Initial flashing: start here

Start from Raspberry Pi OS Lite 64-bit with SSH enabled.

### 1. Clone the repo

```bash
git clone https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
```

### 2. Plug in the boards with USB data cables

Connect these before the one-shot flash when possible:

```text
ESP32-S3 DualEye -> Pi USB
Heltec Mesh Node T114 -> Pi USB-C data cable
InnoMaker CAN adapter -> Pi USB, optional
```

The Heltec board should appear as `/dev/ttyACM*`, `/dev/ttyUSB*`, or the udev alias `/dev/koalabyte-heltec` after setup.

### 3. Run the readiness check

```bash
python3 scripts/check_repo_readiness.py
```

### 4. Run the one-shot installer / flasher

```bash
bash scripts/flash_all_components.sh --install-firmware
```

That command prepares the Pi companion, installs/checks system dependencies, sets up Heltec T114 USB support, builds/flashes the ESP32-S3 DualEye when connected, generates protocol and antenna readiness artifacts, validates the menu, installs the BLE node manager, performs AntEater readiness, and checks CAN bench manifest support.

### 5. Heltec plug-in flashing behavior

During install, the Heltec plug-in helper waits for the T114 USB device and runs the selected T114 profile.

Default profile:

```bash
T114_PLUG_FLASH_PROFILE=color-mouth bash scripts/flash_t114_when_plugged.sh
```

HCI USB profile:

```bash
T114_PLUG_FLASH_PROFILE=hci-usb bash scripts/flash_t114_when_plugged.sh
```

Skip Heltec plug-in flashing:

```bash
FLASH_T114_ON_PLUG=0 bash scripts/flash_all_components.sh --install-firmware
```

Use non-strict mode only when you want the rest of the install to continue if the T114 is not plugged in:

```bash
STRICT_T114_PLUG_FLASH=0 bash scripts/flash_all_components.sh --install-firmware
```

### 6. ESP32-S3 manual boot mode, only if needed

Most ESP32-S3 boards auto-enter download mode. Use manual BOOT only if upload stalls at `Connecting...`.

```text
Hold BOOT
Tap RESET/EN
Release RESET/EN
Wait about 2 seconds
Release BOOT
Run the flash command again
```

Manual ESP32-only flash:

```bash
ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32
```

### 7. Confirm detected ports

```bash
python3 scripts/discover_koalabyte_ports.py --profile heltec
cat logs/preflight/koalabyte_ports.env
```

Expected runtime variables usually look like:

```bash
KOALABYTE_PRIMARY_BLE_PORT=/dev/koalabyte-heltec
KOALABYTE_HELTEC_USB_PORT=/dev/koalabyte-heltec
```

---

## Common commands

```bash
# Full check before deployment
python3 scripts/check_repo_readiness.py
PYTHONPATH=pi-companion python3 scripts/check_menu_actions.py

# Build/package path without flashing services
bash scripts/flash_all_components.sh --all --build-only

# Safe smoke checks after install
bash scripts/flash_all_components.sh --all --smoke

# Didgeridoo mesh app checks
python3 scripts/run_didgeridoo.py status
python3 scripts/run_didgeridoo.py nodes
python3 scripts/run_didgeridoo.py gps

# AntEater passive report from existing Heltec primary BLE logs
PYTHONPATH=pi-companion python3 scripts/run_anteater.py status
PYTHONPATH=pi-companion python3 scripts/run_anteater.py scan

# External antenna readiness
bash scripts/configure_koalabyte_external_antennas.sh --check-only
python3 scripts/check_external_antenna_readiness.py

# Hardware preflight
python3 scripts/preflight_all_hardware.py --profile heltec
```

---

## What each core app does

### Eucalyptus

Passive BLE observation and Koalagotchi-style screen mode. It is for local observation, status, XP, and companion UI feedback.

### AntEater

Passive BLE payment-terminal risk triage from existing Heltec primary BLE logs. It does not pair, connect, probe, spoof, jam, or disrupt.

### Didgeridoo

The Didgeridoo app owns the mesh stack. It contains T114 checks, Meshtastic status, node listing, GPS/GNSS info, protected location gate status, and protected GNSS current fix.

### Koala Kan Kommander

Optional InnoMaker USB-to-CAN support for isolated bench-simulator or owned-harness workflows only.

### KillerKoala companion

Voice/status personality, XP/ranks, face state, buttons, and UI feedback. Ranks are Noob, Hacker, and Legend.

---

## Deployment smoke test

After flashing, run:

```bash
python3 scripts/check_repo_readiness.py
PYTHONPATH=pi-companion python3 scripts/check_menu_actions.py
python3 scripts/run_didgeridoo.py status
bash scripts/configure_koalabyte_external_antennas.sh --check-only
PYTHONPATH=pi-companion python3 scripts/run_anteater.py status
python3 scripts/preflight_all_hardware.py --profile heltec
```

A missing optional CAN adapter or optional Pi USB wireless adapter should not fail the firmware branch. A missing Heltec T114 matters if plug-in flashing is strict.

---

## Useful docs

```text
docs/MAIN_BLE_NODE_ROLES.md
docs/T114_PLUG_IN_FLASHING.md
docs/EXTERNAL_ANTENNA_READINESS.md
docs/ANTEATER_BLE_CARD_SKIMMER_DETECTOR.md
docs/FLASHING.md
docs/ORDERABLE_PARTS_LIST.md
docs/PRODUCTION_FILES.md
```

---

## Project vibe

KoalaByte Blue is meant to feel like a real little cyber field companion: practical enough for a bench, weird enough to be memorable, and safe enough to demo without turning your lab into chaos. KillerKoala watches the canopy, eats Bluetooth eucalyptus data, runs Didgeridoo mesh checks, gains XP through approved actions, and keeps the device focused on lawful local work.
