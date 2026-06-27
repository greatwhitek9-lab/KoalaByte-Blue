# KoalaByte Blue V2 Heltec Edition

**KoalaByte Blue is a pocket-sized koala cyberdeck with attitude.** It is a Raspberry Pi 3B+ powered cyber companion with animated ESP32-S3 DualEye eyes, a Heltec Mesh Node T114 radio/GNSS board, six physical front buttons, eucalyptus-styled menus, KillerKoala voice responses, passive defensive Bluetooth visibility, local reports, and optional InnoMaker CAN bench support.

It is built to feel like a tiny field deck and cyber pet in one: boot it, watch the eyes come alive, open Eucalyptus mode, check Didgeridoo radio/GNSS status, review local Bluetooth signals, export reports, and let KillerKoala bark back when the device does something useful.

KoalaByte Blue is for lawful owned-device labs, defensive review, education, and your own hardware. Do not use it on systems, vehicles, radios, networks, or devices you do not own or do not have permission to test.

---

## Quick build profile

| Part | Role |
|---|---|
| Raspberry Pi 3B+ | Main Linux brain, installer, menus, logs, reports, voice routing, local services, and readiness checks. |
| ESP32-S3 DualEye | Animated eyes, face/display feedback, mic/voice bridge path, and visual personality. |
| Heltec Mesh Node T114 | Production BLE/GNSS/LoRa board for Didgeridoo, Meshtastic-related status, GNSS, and radio checks. |
| Six 4-pin buttons | Front-panel controls for menu navigation. |
| USB power bank / regulated USB supply | Production power source. No loose 18650/raw battery wiring is required. |
| InnoMaker USB-to-CAN kit | Optional isolated owned-bench CAN adapter. InnoMaker CAN kit is optional and skipped if absent. |

No custom PCB is required for this profile.

---

## What the current `Main` branch includes

| Feature | What it does |
|---|---|
| One-shot installer | Runs the Pi, ESP32-S3, Heltec T114, menu, service, and readiness setup from one command. |
| `--check-only` dry run | Validates the repo without flashing firmware or installing services. |
| KoalaByte Doctor | Runs quick/full diagnostics and writes `logs/doctor/koalabyte_doctor_status.json`. |
| Field readiness checker | Confirms doctor, udev, services, logrotate, release package, production files, and version helpers are present. |
| Stable udev names | Adds `/dev/koalabyte-*` aliases for easier board discovery. |
| Boot services | Provides systemd templates for the menu, menu sync, and doctor check. |
| Version handshake | Checks Pi/ESP32/Heltec protocol readiness. |
| Local status dashboard | Emits local JSON/HTML status for field checks. |
| Release ZIP package | Builds `dist/KoalaByte-Blue-install-package.zip`. |
| Log export/logrotate | Bundles debug logs and installs optional log rotation. |

Fast repo check:

```bash
bash scripts/install_koalabyte_one_shot.sh --check-only
```

Fast health check:

```bash
bash scripts/koalabyte_doctor.sh --quick
```

---

## Hardware needed

### Required

```text
Raspberry Pi 3B+
128 GB microSD card recommended, 32 GB minimum for basic testing
Regulated USB power bank or USB power supply
ESP32-S3 DualEye board
Heltec Mesh Node T114
USB data cable for ESP32-S3 DualEye
USB-C data cable for Heltec T114
Six 4-pin momentary buttons
40-pin GPIO extender/cable or direct GPIO wiring
Correct antennas for the boards you use
```

### Optional

```text
InnoMaker USB-to-CAN kit
USB data cable for InnoMaker CAN kit
External case-mounted antenna pigtails
8 ohm speaker path for the ESP32-S3 if your board supports it
Small fan for the Raspberry Pi case
Powered USB hub if USB devices disconnect or the Pi shows undervoltage
```

Power rule: use a regulated USB power bank or USB supply. Do not feed raw battery voltage into the Pi, ESP32-S3, Heltec T114, button wiring, CAN wiring, or antenna hardware.

---

## Fresh Raspberry Pi 3B+ install: Pi OS Lite, no desktop

This is the clean install path for a brand-new microSD card. **Do not flash KoalaByte directly to the SD card.** First flash Raspberry Pi OS Lite, boot the Pi, then run the KoalaByte installer.

### 1. Flash Raspberry Pi OS Lite to the microSD

Use Raspberry Pi Imager on your computer:

```text
Raspberry Pi Device: Raspberry Pi 3
Operating System: Raspberry Pi OS Lite, 64-bit recommended
Storage: your microSD card
```

Open the Imager settings before writing the card:

```text
Set hostname: koalabyte-blue
Enable SSH: yes
Set username/password: your choice
Configure Wi-Fi: only if you are not using Ethernet
Set locale/timezone: your region
```

Write the card, eject it safely, insert it into the Raspberry Pi 3B+, connect Ethernet or Wi-Fi, then power the Pi from a regulated USB power supply or power bank.

### 2. SSH into the Pi

From your computer:

```bash
ssh <your-user>@koalabyte-blue.local
```

If `.local` does not resolve, find the Pi IP address from your router and use:

```bash
ssh <your-user>@<pi-ip-address>
```

### 3. Update the Pi first

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

Reconnect after reboot:

```bash
ssh <your-user>@koalabyte-blue.local
```

### 4. Plug in the KoalaByte boards

Use data-capable USB cables:

```text
ESP32-S3 DualEye -> Raspberry Pi USB port
Heltec Mesh Node T114 -> Raspberry Pi USB port with USB-C data cable
Optional InnoMaker CAN kit -> Raspberry Pi USB port only if using CAN bench tools
```

The InnoMaker CAN kit can stay unplugged for a normal install. The installer skips CAN setup when the adapter is absent.

### 5. Download and run the installer from `Main`

```bash
curl -fsSL -o koalabyte-install.sh https://raw.githubusercontent.com/greatwhitek9-lab/KoalaByte-Blue/Main/install.sh
bash koalabyte-install.sh check-only
```

If the dry run passes, run the full installer:

```bash
bash koalabyte-install.sh
```

The installer clones/updates the repo at:

```text
~/KoalaByte-Blue
```

Then it runs the one-shot installer.

### 6. Reboot and start KoalaByte Blue

```bash
sudo reboot
```

Reconnect, then start the device UI:

```bash
cd ~/KoalaByte-Blue
bash scripts/koalabyte_blue_boot.sh
```

---

## Already cloned install

From inside an existing checkout:

```bash
bash install.sh check-only
bash install.sh
```

Or run the one-shot directly:

```bash
bash scripts/install_koalabyte_one_shot.sh --check-only
bash scripts/install_koalabyte_one_shot.sh
```

Useful install options:

```bash
# Explicit normal Heltec profile
T114_PLUG_FLASH_PROFILE=combined-safe bash scripts/install_koalabyte_one_shot.sh

# Skip Heltec flashing while debugging USB/ports
FLASH_T114_ON_PLUG=0 bash scripts/install_koalabyte_one_shot.sh

# Do not fail the whole install if the T114 is not ready yet
STRICT_T114_PLUG_FLASH=0 bash scripts/install_koalabyte_one_shot.sh

# Make dependency checks strict
STRICT_FULL_RUNTIME_DEPENDENCIES=1 bash scripts/install_koalabyte_one_shot.sh

# Stable serial aliases: auto/default, force, or skip
INSTALL_UDEV_RULES=auto bash scripts/install_koalabyte_one_shot.sh
INSTALL_UDEV_RULES=1 bash scripts/install_koalabyte_one_shot.sh
INSTALL_UDEV_RULES=0 bash scripts/install_koalabyte_one_shot.sh

# Boot services: auto/default, force, or skip
INSTALL_BOOT_SERVICES=auto bash scripts/install_koalabyte_one_shot.sh
INSTALL_BOOT_SERVICES=1 bash scripts/install_koalabyte_one_shot.sh
INSTALL_BOOT_SERVICES=0 bash scripts/install_koalabyte_one_shot.sh

# Optional CAN behavior
INSTALL_INNOMAKER_CAN=optional bash scripts/install_koalabyte_one_shot.sh
INSTALL_INNOMAKER_CAN=0 bash scripts/install_koalabyte_one_shot.sh
STRICT_INNOMAKER_CAN=1 bash scripts/install_koalabyte_one_shot.sh
```

---

## What the one-shot installer does

The normal one-shot path prepares the Pi companion, checks the repo, handles udev names, flashes the ESP32-S3 DualEye firmware, prepares/flashes the Heltec T114 combined-safe profile, validates KillerKoala AI/voice readiness, checks eyes and mouth sync, checks menu display sync, runs field readiness, checks version handshake, checks the local dashboard JSON, validates release/log helpers, runs KoalaByte Doctor, installs boot services, checks antenna readiness, prepares AntEater passive readiness, and records optional CAN status.

The dry run does the readiness checks without flashing firmware or installing services:

```bash
bash scripts/install_koalabyte_one_shot.sh --check-only
```

Important output files:

```text
logs/one_shot_install_status.json
logs/one_shot/control_surface_status.json
logs/one_shot/full_runtime_dependencies.json
logs/one_shot/field_readiness_status.json
logs/menu_actions/menu_action_manifest.json
logs/menu_sync/current_menu_state.json
logs/doctor/koalabyte_doctor_status.json
logs/version/koalabyte_version_handshake.json
logs/killerkoala/killerkoala_ai_readiness.json
logs/can/innomaker_optional_status.json
exports/koalabyte_logs_<timestamp>.zip
```

---

## Button map

```text
Button 1 -> Main Menu -> GPIO5
Button 2 -> Move Left / Back -> GPIO6
Button 3 -> Enter / Select -> GPIO13, hold 3s for shutdown event
Button 4 -> Move Right / Forward -> GPIO19
Button 5 -> Up -> GPIO26
Button 6 -> Down -> GPIO21
```

Wire one side of each button to its GPIO input and the opposite side to ground. Do not tie GPIO pins together.

---

## Antenna routing

```text
Heltec T114 LoRa connector -> region-matched LoRa antenna
Heltec T114 2.4 GHz connector -> 2.4 GHz antenna if your T114 board exposes one
ESP32-S3 DualEye 2.4 GHz connector -> ESP32-S3 Wi-Fi/BLE antenna if your board exposes one
Raspberry Pi 3B+ -> built-in Wi-Fi antenna; optional USB Wi-Fi adapter only
```

Do not swap LoRa and 2.4 GHz antennas. They are different radio paths.

---

## Main menu overview

| Main item | Plain-English meaning |
|---|---|
| Eucalyptus | Passive BLE logger controls and Koalagotchi mode. |
| Bluetooth Tools | Local Bluetooth/BLE inventory, summaries, BlueZ helper checks, protected lab-only actions, and defensive review tools. |
| Didgeridoo | Heltec T114, GNSS/GPS, Meshtastic, mesh, and protected location tools. |
| CAN Bench Tools | Optional InnoMaker USB-to-CAN bench tools. |
| Reports & Reviews | Report builders, defensive review templates, and Boomerang camera-awareness logbook. |
| System / Companion | KillerKoala voice, XP/status, buttons, settings, and helper controls. |
| Lab | A shorter authorized-lab menu with safe review items and protected BlueZ helpers. |

### Common action groups

```text
Eucalyptus Canopy Status / Start / Stop / Restart
Eucalyptus Koalagotchi Mode
Heltec Link
Radio/GPS
T114 Quick BLE Test Scan
Didgeridoo Status
Didgeridoo Nodes
Didgeridoo GPS Info
Koala Kan Kommander
CAN Bench Safety Check
Report
Authorized BLE Inventory
Defensive Lab Report
KillerKoala Voice
Buttons
Level / Status
Settings
```

Protected Bluetooth actions use the protected-actions password gate. Target-specific protected actions also require:

```bash
export KOALABYTE_BLUEZ_LAB_TARGET=AA:BB:CC:DD:EE:FF
export KOALABYTE_BLUEZ_OWNED_DEVICE=1
```

---

## KillerKoala AI companion

KillerKoala is the device personality. It uses a fast phrase-first system by default and can use a local TinyLlama/Ollama fallback for more flexible banter.

Default local AI settings:

```text
INSTALL_KILLERKOALA_OLLAMA=auto
STRICT_KILLERKOALA_OLLAMA=0
KILLERKOALA_BASE_MODEL=tinyllama:1.1b
KILLERKOALA_LLM_MODEL=killerkoala-tinyllama:latest
```

AI helper:

```bash
bash scripts/setup_killerkoala_ollama.sh
```

Common voice patterns:

```text
killerkoala open Eucalyptus
killerkoala open Didgeridoo
killerkoala run T114 Quick BLE Test Scan
killerkoala open Reports & Reviews
killerkoala status
killerkoala level
killerkoala buttons
```

The face system syncs ESP32-S3 DualEye visuals with the Heltec status path. Menu inactivity and completed actions return the display to the AI face until B1/menu or touchscreen double-tap reopens the menu.

---

## Field readiness tools

```bash
# Doctor
bash scripts/koalabyte_doctor.sh --quick
bash scripts/koalabyte_doctor.sh

# Safe mode
bash scripts/koalabyte_safe_mode.sh
bash scripts/koalabyte_safe_mode.sh --terminal
bash scripts/koalabyte_safe_mode.sh --doctor

# Stable device names
bash scripts/install_koalabyte_udev_rules.sh --check-only
bash scripts/install_koalabyte_udev_rules.sh

# Boot services
bash scripts/install_koalabyte_boot_services.sh --check-only
bash scripts/install_koalabyte_boot_services.sh

# Version handshake and dashboard JSON
PYTHONPATH=pi-companion python3 scripts/check_koalabyte_version_handshake.py
PYTHONPATH=pi-companion python3 scripts/run_koalabyte_status_server.py --json

# Local dashboard
PYTHONPATH=pi-companion python3 scripts/run_koalabyte_status_server.py --host 0.0.0.0 --port 8080

# Log export and logrotate
bash scripts/export_koalabyte_logs.sh
bash scripts/install_koalabyte_logrotate.sh --check-only
bash scripts/install_koalabyte_logrotate.sh
```

Release package:

```bash
bash scripts/build_koalabyte_release_package.sh
```

Expected output:

```text
dist/KoalaByte-Blue-install-package.zip
```

---

## Manual verification commands

```bash
python3 scripts/check_repo_readiness.py
bash scripts/preflight_all_hardware.sh --profile heltec
PYTHONPATH=pi-companion python3 scripts/check_full_runtime_dependencies.py
PYTHONPATH=pi-companion python3 scripts/check_one_shot_controls.py
PYTHONPATH=pi-companion python3 scripts/check_field_readiness.py
PYTHONPATH=pi-companion python3 scripts/check_menu_actions.py
PYTHONPATH=pi-companion python3 scripts/check_t114_status_dashboard.py
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_face_mouth_sync.py --emit-test
PYTHONPATH=pi-companion python3 scripts/check_menu_display_sync.py
PYTHONPATH=pi-companion python3 scripts/check_koalabyte_version_handshake.py
PYTHONPATH=pi-companion python3 scripts/run_koalabyte_status_server.py --json
bash scripts/koalabyte_doctor.sh --quick
bash scripts/install_koalabyte_udev_rules.sh --check-only
bash scripts/install_koalabyte_boot_services.sh --check-only
bash scripts/install_koalabyte_logrotate.sh --check-only
bash scripts/configure_koalabyte_external_antennas.sh --check-only
PYTHONPATH=pi-companion python3 scripts/run_anteater.py status
```

Optional CAN status:

```bash
cat logs/can/innomaker_optional_status.json
```

Expected optional CAN statuses:

```text
OPTIONAL_CAN_CHECK_RECORDED
OPTIONAL_CAN_SKIPPED_NOT_PRESENT
OPTIONAL_CAN_CHECK_ONLY
```

---

## Troubleshooting

### Start with Doctor

```bash
bash scripts/koalabyte_doctor.sh --quick
cat logs/doctor/koalabyte_doctor_status.json
```

### The Pi cannot see a board

```bash
lsusb
python3 scripts/discover_koalabyte_ports.py --profile heltec
bash scripts/install_koalabyte_udev_rules.sh --check-only
```

Use USB data cables, not charge-only cables.

### ESP32 flashing fails

```bash
ESP32_PORT=/dev/ttyUSB0 bash scripts/install_koalabyte_one_shot.sh
```

### Heltec flashing fails

```bash
STRICT_T114_PLUG_FLASH=0 bash scripts/install_koalabyte_one_shot.sh
python3 scripts/discover_koalabyte_ports.py --profile heltec
```

### Local AI setup is slow

```bash
INSTALL_KILLERKOALA_OLLAMA=0 bash scripts/install_koalabyte_one_shot.sh
```

### CAN is missing

That is okay unless you requested strict CAN. In normal mode, if the adapter is not detected, the installer skips CAN setup and continues.

```bash
cat logs/can/innomaker_optional_status.json
```

### Export logs for debugging

```bash
bash scripts/export_koalabyte_logs.sh
ls exports/
```

---

## Safety boundary

KoalaByte Blue is for lawful owned-device labs and defensive review. The repository focuses on passive observation, local status, reports, readiness checks, companion UI, password-protected lab-only helpers, and isolated bench workflows. Do not use it on systems, vehicles, networks, radios, or devices you do not own or do not have permission to test.
