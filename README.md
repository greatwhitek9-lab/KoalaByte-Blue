# KoalaByte Blue V2 Heltec Edition

KoalaByte Blue V2 Heltec Edition is the Raspberry Pi + ESP32-S3 DualEye + Heltec T114 build of the KillerKoala cyber companion. It is built for lawful owned-device labs, defensive Bluetooth observation, Didgeridoo mesh status, front-panel UI, AntEater passive BLE review, and optional isolated CAN bench work.

Use it only on your own equipment, your own lab traffic, or systems you have written permission to test.

---

## Full one-shot install

Plug everything in first:

```text
Raspberry Pi 3B+ powered from regulated USB
ESP32-S3 DualEye -> Pi USB data cable
Heltec Mesh Node T114 -> Pi USB-C data cable
InnoMaker CAN kit -> optional Pi USB data cable
```

Then run one command:

```bash
bash scripts/install_koalabyte_one_shot.sh
```

That one command handles the Pi companion install, Heltec plug-in firmware flash, ESP32-S3 DualEye firmware flash, BLE node manager service, Didgeridoo/menu readiness, antenna/protocol artifacts, and AntEater passive-readiness status.

The InnoMaker CAN kit is optional. If it is not plugged in, the one-shot installer records a non-failing optional CAN status and continues.

Deployment readiness markers: `bash scripts/install_koalabyte_one_shot.sh`; `InnoMaker CAN kit is optional`.

Useful overrides:

```bash
# Pick ESP32 upload port manually
ESP32_PORT=/dev/ttyUSB0 bash scripts/install_koalabyte_one_shot.sh

# Default Heltec color-mouth profile
T114_PLUG_FLASH_PROFILE=color-mouth bash scripts/install_koalabyte_one_shot.sh

# Heltec HCI USB profile instead
T114_PLUG_FLASH_PROFILE=hci-usb bash scripts/install_koalabyte_one_shot.sh

# Skip optional CAN checks entirely
INSTALL_INNOMAKER_CAN=0 bash scripts/install_koalabyte_one_shot.sh

# Make optional CAN strict only when you intentionally want CAN to block deployment
STRICT_INNOMAKER_CAN=1 bash scripts/install_koalabyte_one_shot.sh
```

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

## Initial flashing details

The preferred deployment command is:

```bash
bash scripts/install_koalabyte_one_shot.sh
```

That command is stricter than the older component helper: Pi, Heltec, and ESP32-S3 are part of the main install path; only the InnoMaker CAN kit is optional by default.

### 1. Clone the repo

```bash
git clone https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
```

### 2. Run readiness before flashing

```bash
python3 scripts/check_repo_readiness.py
```

### 3. Run the one-shot install

```bash
bash scripts/install_koalabyte_one_shot.sh
```

### 4. Confirm detected ports

```bash
python3 scripts/discover_koalabyte_ports.py --profile heltec
cat logs/preflight/koalabyte_ports.env
```

Expected runtime variables usually look like:

```bash
KOALABYTE_PRIMARY_BLE_PORT=/dev/koalabyte-heltec
KOALABYTE_HELTEC_USB_PORT=/dev/koalabyte-heltec
```

### ESP32-S3 manual boot mode, only if needed

Most ESP32-S3 boards auto-enter download mode. Use manual BOOT only if upload stalls at `Connecting...`.

```text
Hold BOOT
Tap RESET/EN
Release RESET/EN
Wait about 2 seconds
Release BOOT
Run the one-shot command again
```

---

## Common commands

```bash
# Full branch readiness
python3 scripts/check_repo_readiness.py
PYTHONPATH=pi-companion python3 scripts/check_menu_actions.py

# Full one-shot deployment
bash scripts/install_koalabyte_one_shot.sh

# Older component helper, still available for advanced/manual target work
bash scripts/flash_all_components.sh --install-firmware

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

Optional InnoMaker USB-to-CAN support for isolated bench-simulator or owned-harness workflows only. It is the only hardware module in the one-shot path that is optional by default.

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

A missing optional InnoMaker CAN kit or optional Pi USB wireless adapter should not fail the firmware branch. A missing Heltec T114 or ESP32-S3 matters for the full one-shot installer.

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
