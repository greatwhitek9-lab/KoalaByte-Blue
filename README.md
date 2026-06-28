# KoalaByte Blue V2 Heltec Edition

**KoalaByte Blue is a pocket-sized koala cyberdeck with attitude.** It uses a Raspberry Pi 3B+ as the main Linux brain, an ESP32-S3 DualEye for animated eyes/face feedback and voice-front-end work, a Heltec Mesh Node T114 with onboard nRF52840 for primary BLE/GNSS/LoRa duties, six front buttons, a shared jungle/eucalyptus menu UI, KillerKoala voice responses, Meshtastic App helpers, defensive Bluetooth visibility, Wi-Fi/BLE survey mapping, GreatWhite Reef packet-analysis review, local reports, and optional InnoMaker CAN bench support.

KoalaByte Blue is for lawful owned-device labs, defensive review, education, and your own hardware. Do not use it on systems, vehicles, radios, networks, or devices you do not own or do not have permission to test.

---

## Quick build profile

| Part | Role |
|---|---|
| Raspberry Pi 3B+ | Main Linux brain, installer, menus, logs, reports, local services, voice routing, main Wi-Fi controller, GreatWhite Reef PCAP review, and readiness checks. |
| ESP32-S3 DualEye | Animated eyes and mouth/face feedback, mic/voice bridge path, secondary Wi-Fi survey node, BLE support node, and visual personality. |
| Heltec Mesh Node T114 / nRF52840 | Primary BLE node plus GNSS and LoRa/Meshtastic path. It is not a Wi-Fi node. |
| Six 4-pin buttons | Front-panel controls for menu navigation and select. |
| USB power bank / regulated USB supply | Production power source. No loose 18650/raw battery wiring is required. |
| InnoMaker USB-to-CAN kit | Optional isolated owned-bench CAN adapter. InnoMaker CAN kit is optional and skipped if absent. |

No custom PCB is required for this profile.

---

## Current radio roles

```text
Heltec T114 / nRF52840 -> primary BLE node, GNSS node, and LoRa/Meshtastic node; no Wi-Fi
Raspberry Pi 3B+       -> main Wi-Fi controller, BLE support/fallback node, and PCAP review host
ESP32-S3 DualEye       -> secondary Wi-Fi survey node and BLE support node
```

Koala Kombat Kruisin uses the Pi as the main Wi-Fi controller, the ESP32-S3 DualEye as the extra Wi-Fi survey node, and the Heltec T114/nRF52840 as the primary BLE/GNSS/LoRa path.

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
| Cleaned jungle menu | Removes redundant front-end rows while keeping branded tools, wrapped BlueZ tools, and GreatWhite Reef. |
| GreatWhite Reef | Adds a full wrapped submenu for TigerShark (`tshark`) and Great Wire Shark (`wireshark`) PCAP/PCAPNG review. |
| GreatWhite selectable PCAPs | Syncs `.pcap`/`.pcapng` files into `logs/greatwhite_reef/pcaps/`, then exposes selectable `PCAP N: filename` menu rows. |
| Menu theme fit checks | Validates jungle/eucalyptus menu identity and keeps terminal menu text inside its border frame with `check_menu_theme_fit.py`. |
| Menu prompt UI checks | Validates menu-managed prompt controls and pop-up text input with `scripts/check_menu_prompt_ui.py`. |
| Pop-up text input | Opens only from actual text-input rows for WiGLE name/key, protected local lock/unlock, and Meshtastic message/destination text. |
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
USB or Bluetooth keyboard for faster text entry
```

### Software tools installed by the Pi helper

```text
TigerShark -> tshark
Great Wire Shark -> wireshark
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

Open Imager settings before writing the card:

```text
Set hostname: koalabyte-blue
Enable SSH: yes
Set username/password: your choice
Configure Wi-Fi: only if you are not using Ethernet
Set locale/timezone: your region
```

Write the card, eject it safely, insert it into the Raspberry Pi 3B+, connect Ethernet or Wi-Fi, then power the Pi from a regulated USB power supply or power bank.

### 2. SSH into the Pi

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

# Make system command dependency checks strict on a real Pi image
STRICT_FULL_RUNTIME_DEPENDENCIES=1 bash scripts/install_koalabyte_one_shot.sh

# Extra folders to sync into GreatWhite Reef PCAP review
KOALABYTE_REEF_PCAP_IMPORT_DIRS="/home/pi/captures:/mnt/usb/pcaps" bash scripts/install_koalabyte_one_shot.sh --check-only

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

The normal one-shot path prepares the Pi companion, checks the repo, handles udev names, flashes the ESP32-S3 DualEye firmware, prepares/flashes the Heltec T114 combined-safe profile, validates KillerKoala AI/voice readiness, checks eyes and mouth sync, checks menu display sync, checks jungle/eucalyptus theme fit, validates menu-managed prompt UI controls, validates GreatWhite Reef module/docs/runtime dependencies, runs field readiness, checks version handshake, checks the local dashboard JSON, validates release/log helpers, runs KoalaByte Doctor, installs boot services, checks antenna readiness, prepares AntEater passive readiness, and records optional CAN status.

The dry run does the readiness checks without flashing firmware or installing services:

```bash
bash scripts/install_koalabyte_one_shot.sh --check-only
```

Important output files:

```text
logs/one_shot_install_status.json
logs/one_shot/control_surface_status.json
logs/one_shot/full_runtime_dependencies.json
logs/one_shot/menu_prompt_ui_readiness.json
logs/one_shot/koala_kry_menu_readiness.json
logs/one_shot/field_readiness_status.json
logs/greatwhite_reef/greatwhite_reef_status.json
logs/greatwhite_reef/pcaps/
logs/menu_actions/menu_action_manifest.json
logs/menu_actions/menu_theme_fit_status.json
logs/menu_sync/current_menu_state.json
logs/doctor/koalabyte_doctor_status.json
logs/version/koalabyte_version_handshake.json
logs/killerkoala/killerkoala_ai_readiness.json
logs/can/innomaker_optional_status.json
```

---

## Button, touchscreen, keyboard, and voice control

```text
Button 1 -> Main Menu -> GPIO5
Button 2 -> Move Left / Back -> GPIO6
Button 3 -> Enter / Select -> GPIO13, hold 3s for shutdown event
Button 4 -> Move Right / Forward -> GPIO19
Button 5 -> Up -> GPIO26
Button 6 -> Down -> GPIO21
```

Wire one side of each button to its GPIO input and the opposite side to ground. Do not tie GPIO pins together.

Every enabled leaf action can be started from the same menu path:

```text
scroll / highlight -> select with B3, Enter, touchscreen long press, USB/Bluetooth keyboard, or KillerKoala voice command
```

Submenu rows open another menu. Tool rows inside that submenu run the actual action. Pop-up keyboard mode only appears after selecting text input rows such as `Type WiGLE Name`, `Type WiGLE Key`, `Set Local Lock`, `Unlock Local Lock`, `Type Mesh Message`, or `Type Mesh Destination`.

Text entry controls:

```text
Buttons/touchscreen -> select on-screen keys
USB/Bluetooth keyboard -> type directly, Enter saves, Backspace deletes, Esc cancels
Voice-to-text -> say or route "keyboard text <words>" after the input page is open
```

Common voice patterns:

```text
killerkoala open Eucalyptus
killerkoala open Koala Kombat Kruisin
killerkoala open Meshtastic App
killerkoala open GreatWhite Reef
killerkoala run PCAP 1
killerkoala run PCAP 2
killerkoala run TigerShark Read Latest PCAP
killerkoala run Wi-Fi + BLE Survey
killerkoala run T114 BLE Check
killerkoala open Koala Kan Kommander
killerkoala run Platypus BT-Proxy
killerkoala run Type Mesh Message
killerkoala status
killerkoala level
killerkoala buttons
```

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

## Jungle menu overview

The visible UI uses one shared jungle-adventure/eucalyptus theme for terminal and touchscreen modes. The renderer uses a shared font stack, carved title text, leaf borders, and automatic text fitting/wrapping so menu labels and selected-item descriptions stay inside their dialogue borders.

### Main Canopy

| Main item | What it opens |
|---|---|
| Eucalyptus | Passive BLE logger controls, GPS trail builder, WiGLE text input/status/upload, and Koalagotchi mode. |
| Koala Kombat Kruisin | Passive Wi-Fi/BLE/GPS survey mapping, WiGLE text input, and WiGLE upload tools. |
| Bluetooth Tools | Custom BLE tools plus wrapped BlueZ tools with custom KoalaByte names. |
| Didgeridoo | Heltec T114/nRF52840 BLE, GNSS, LoRa/Meshtastic, Meshtastic App, protected lock input, and location helpers. |
| CAN Bench Tools | Optional InnoMaker USB-to-CAN bench workflow. |
| GreatWhite Reef | TigerShark and Great Wire Shark PCAP/PCAPNG review, selectable PCAP rows, and packet-analysis reporting. |
| Reports & Reviews | Documentation, review, inventory, and lab report builders. |
| System / Companion | KillerKoala voice, XP/status, buttons, settings, and helper controls. |
| Lab | Protected lab-focused BlueZ shortcuts and location gate status. |
| Power & Exit | Shutdown and quit controls. |

### Eucalyptus

```text
Eucalyptus Prompt Status
Type WiGLE Name
Type WiGLE Key
Eucalyptus GPS ON / OFF
Eucalyptus WiGLE Dry-Run ON / OFF
Eucalyptus WiGLE Upload ON / OFF
Eucalyptus Canopy Status / Start / Stop / Restart
Eucalyptus GPS Trail
Eucalyptus Upload Trail
Eucalyptus WiGLE Upload
Eucalyptus Koalagotchi Mode
```

### Koala Kombat Kruisin

```text
Kruisin Prompt Status
Type WiGLE Name
Type WiGLE Key
Kruisin GPS ON / OFF
Kruisin Nodes ON / OFF
Kruisin Default Ports
Kruisin WiGLE Dry-Run ON / OFF
Kruisin WiGLE Upload ON / OFF
Kruisin Status
Wi-Fi AP Survey
BLE Survey
Wi-Fi + BLE Survey
Kruisin GPS Status
Kruisin WiGLE Upload
```

### Bluetooth Tools

```text
Koala Kapture
Koala Kry
KoalaByte Lab
Outback Module Deck
Gumleaf Gear Check
Eucalyptus Bus Scout
Dropbear Discovery Sweep
Billabong HCI Watch
Kookaburra Safe Nest Run
Joey Target Dossier
Treehouse Service Trace
Gumnut GATT Gatecheck
Outback Radio Ledger
Classic Track Finder
Treehouse RFCOMM Wiremap
Pouch Link Echo
Gumnut GATT Ghostmap
Platypus BT-Proxy
that’s not a knife
AntEater
Urban Poaching
```

The generic `Scan`, `Summary`, `Show Devices`, and `Ear Tag` rows were removed from the visible menu to reduce clutter. Their useful behavior is covered by the branded/wrapped tools above.

### Didgeridoo

```text
Heltec Link
Radio/GPS
T114 BLE Check
Lab TX Status
Sextant
Set Local Lock
Unlock Local Lock
Location Unlock ON / OFF
Meshtastic App
Protected Location Gate Status
Protected GNSS Current Fix
```

### Meshtastic App

```text
Meshtastic Profile
Meshtastic Compatibility
Phone App Pairing
ESP32 Device Link
Use Heltec USB Serial
Use Network TCP
Use BLE Link
Meshtastic Status
Meshtastic Nodes
Meshtastic GPS Info
Meshtastic Listen Gate
Send Prompt Status
Type Mesh Message
Type Mesh Destination
Set Test Message
Set Check-In Message
Confirm Send ON / OFF
Clear Send Draft
Meshtastic Send Gate
```

The Meshtastic App row opens the Didgeridoo Meshtastic hub. It shows the saved local node profile and links safe status, nodes, GPS, protected listen, and protected send helpers without sending messages or starting a live listener by default.

### CAN Bench Tools

```text
Koala Kan Kommander
```

The duplicate `CAN Bench Safety Check` row was removed because it pointed to the same backend command.

### GreatWhite Reef

GreatWhite Reef is the wrapped packet-analysis submenu. It uses these KoalaByte names:

```text
TigerShark -> tshark
Great Wire Shark -> wireshark
```

GreatWhite Reef keeps PCAPs in:

```text
logs/greatwhite_reef/pcaps/
```

It automatically syncs `.pcap` and `.pcapng` files found under `logs/` into that folder. Extra folders can be added with `KOALABYTE_REEF_PCAP_IMPORT_DIRS`.

```text
Reef Status
TigerShark Install Check
TigerShark Interfaces
TigerShark PCAP Folder
TigerShark Read Latest PCAP
PCAP 1: <newest synced file>
PCAP 2: <next synced file>
Great Wire Shark Launch Notes
Great Wire Shark Folder Notes
GreatWhite Reef Report
```

The `PCAP N: filename` rows are dynamic. Highlight a PCAP with the front buttons, touchscreen, keyboard, or voice command. Selecting it runs that exact file through TigerShark Read and writes JSON output to `logs/greatwhite_reef/`.

### Reports & Reviews

```text
Koala Kry RF Review
Boomerang
Authorized BLE Inventory
GATT Readiness Checklist
Pairing Security Review
Lab Beacon Plan
Packet Capture Notes
Defensive Lab Report
```

The generic `Report` alias was removed because `Defensive Lab Report` is the canonical report builder.

### Lab

```text
Joey Target Dossier
Treehouse Service Trace
Gumnut GATT Gatecheck
Outback Radio Ledger
Classic Track Finder
Treehouse RFCOMM Wiremap
Pouch Link Echo
Gumnut GATT Ghostmap
Platypus BT-Proxy
Set Local Lock
Unlock Local Lock
Location Unlock ON / OFF
Protected Location Gate Status
```

The Lab submenu intentionally keeps protected BlueZ shortcuts for fast access. Repeated generic report rows were removed because they already live under Reports & Reviews.

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

The face system syncs ESP32-S3 DualEye visuals with the Heltec status path. Menu inactivity and completed actions return the display to the AI face until B1/menu or touchscreen double-tap reopens the menu.

---

## Field readiness tools

```bash
# Doctor
bash scripts/koalabyte_doctor.sh --quick
bash scripts/koalabyte_doctor.sh

# Safe mode
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

# Menu action, theme, prompt UI, Koala Kry, and GreatWhite Reef readiness
PYTHONPATH=pi-companion python3 scripts/check_menu_actions.py
PYTHONPATH=pi-companion python3 scripts/check_menu_theme_fit.py
PYTHONPATH=pi-companion python3 scripts/check_menu_prompt_ui.py
PYTHONPATH=pi-companion python3 scripts/check_koala_kry_menu.py
PYTHONPATH=pi-companion python3 scripts/check_full_runtime_dependencies.py
STRICT_FULL_RUNTIME_DEPENDENCIES=1 PYTHONPATH=pi-companion python3 scripts/check_full_runtime_dependencies.py
```
