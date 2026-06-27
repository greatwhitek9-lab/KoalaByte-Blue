# KoalaByte Blue V2 Heltec Edition

KoalaByte Blue V2 Heltec Edition is the beginner-friendly Raspberry Pi 3B+ build of the KillerKoala cyber companion. It combines a Raspberry Pi, an ESP32-S3 DualEye display board, a Heltec Mesh Node T114, six front buttons, optional antennas, and an optional InnoMaker USB-to-CAN kit.

The project is designed for lawful owned-device labs, defensive Bluetooth observation, Koalagotchi-style companion feedback, Didgeridoo mesh/GNSS status, safe local reports, voice control, protected lab-only helper actions, field-readiness checks, and optional isolated CAN bench work.

Use KoalaByte Blue only on your own equipment, your own lab traffic, or systems you have written permission to test.

---

## What is new in the current default branch

The default branch now includes the newer field-readiness install path:

| New item | What it adds |
|---|---|
| One-shot `--check-only` | Runs a dry-run validation without flashing firmware or installing services. |
| KoalaByte Doctor | Runs a quick or full diagnostic sweep and writes a status report. |
| Field readiness checker | Verifies the new install helpers, service templates, version manifest, and dashboard helpers. |
| Stable udev names | Adds install/check support for stable `/dev/koalabyte-*` serial aliases. |
| Boot service templates | Adds systemd templates for the menu, menu sync, and doctor check. |
| Version handshake | Checks Pi/ESP32/Heltec protocol readiness and writes a version status report. |
| Local status dashboard | Provides a local JSON/HTML status dashboard helper. |
| Log export | Bundles useful logs into `exports/`. |
| Log rotation | Adds a logrotate config and installer for `/etc/logrotate.d/koalabyte-blue`. |
| Release ZIP package | Adds a local package builder and GitHub Actions release-package workflow. |

Quick dry-run:

```bash
bash scripts/install_koalabyte_one_shot.sh --check-only
```

Quick doctor check:

```bash
bash scripts/koalabyte_doctor.sh --quick
```

---

## Beginner summary

Think of the device as five main parts working together:

| Part | Simple role | What it does in KoalaByte Blue |
|---|---|---|
| Raspberry Pi 3B+ | Main brain | Runs the installer, menus, logs, voice commands, KillerKoala companion, local services, field checks, and most processing. |
| ESP32-S3 DualEye | Face and local display | Runs the eyes, face feedback, DualEye screen, button/UI feedback, and built-in mic bridge support. |
| Heltec Mesh Node T114 | Radio/GPS board | Provides the T114 nRF52840 path, primary BLE/GNSS status, LoRa/Meshtastic-related checks, and Heltec status/mouth sync. |
| Six 4-pin buttons | Physical controls | Let you move through menus without a keyboard. |
| InnoMaker USB-to-CAN | Optional CAN bench adapter | Used only for isolated owned-bench CAN checks. The one-shot installer skips this path when the adapter is absent. |

No custom PCB is required for this profile.

---

## Hardware needed

### Required

```text
Raspberry Pi 3B+
128 GB or larger microSD card recommended
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
Small speaker/amp path for ESP32-S3 if your board supports it
Small fan for the Raspberry Pi case
```

Power rule: do not feed raw battery voltage into the Pi, ESP32-S3, Heltec T114, or CAN adapter. Use regulated USB power.

---

## Board roles

### Raspberry Pi 3B+

The Pi is the host computer. It boots Raspberry Pi OS from the SD card and runs the KoalaByte Blue software. It owns the main menu, Python companion code, logs, system services, voice command routing, KillerKoala AI fallback, BLE node manager, CAN helper scripts, protected action gates, field-readiness tools, and readiness checks.

### ESP32-S3 DualEye

The ESP32-S3 DualEye is the face/display board. In this build it handles the animated eyes, local face state, display feedback, and voice bridge support for the built-in mic path. The installer flashes the ESP32-S3 DualEye firmware with PlatformIO.

### Heltec Mesh Node T114

The Heltec Mesh Node T114 is the radio/GNSS board for this edition. The normal firmware profile is:

```bash
T114_PLUG_FLASH_PROFILE=combined-safe bash scripts/install_koalabyte_one_shot.sh
```

The T114 provides BLE/GNSS controller status over USB serial JSON, GPS/GNSS handoff to the Pi, Didgeridoo/Meshtastic status paths, LoRa antenna readiness, and Heltec face/mouth/status sync.

### Six front buttons

```text
Button 1 -> Main Menu -> GPIO5
Button 2 -> Move Left / Back -> GPIO6
Button 3 -> Enter / Select -> GPIO13, hold 3s for shutdown event
Button 4 -> Move Right / Forward -> GPIO19
Button 5 -> Up -> GPIO26
Button 6 -> Down -> GPIO21
```

Use one side of each button for the GPIO input and the opposite side for ground. Do not tie GPIO pins together.

### InnoMaker USB-to-CAN kit

The InnoMaker CAN kit is optional. During the one-shot install:

```text
If the adapter is present:
  KoalaByte runs CAN setup/status checks and records the result.

If the adapter is not present:
  KoalaByte skips CAN setup, writes a skipped status, and continues.
```

Status is written here:

```text
logs/can/innomaker_optional_status.json
```

Strict hardware builds can require CAN with:

```bash
STRICT_INNOMAKER_CAN=1 bash scripts/install_koalabyte_one_shot.sh
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

## Very simple install and flashing guide

### Step 1: Flash Raspberry Pi OS

Use Raspberry Pi Imager. Choose Raspberry Pi OS Lite for Raspberry Pi 3B+. Enable SSH in the imager settings so you can log in after boot.

### Step 2: Boot the Pi

```bash
sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

### Step 3: Plug in the boards

```text
ESP32-S3 DualEye -> Pi USB port
Heltec Mesh Node T114 -> Pi USB port with USB-C data cable
Optional InnoMaker CAN kit -> Pi USB port, only if you are using CAN bench tools
```

The InnoMaker CAN kit does not need to be plugged in for a normal install. If it is absent, the one-shot installer skips CAN setup and continues.

### Step 4: Run the installer

From a fresh Pi, run:

```bash
curl -fsSL -o koalabyte-install.sh https://raw.githubusercontent.com/greatwhitek9-lab/KoalaByte-Blue/koalabyte-blue-v2-heltec-edition/install.sh
bash koalabyte-install.sh
```

If you already cloned the repo, run either:

```bash
bash install.sh
```

or:

```bash
bash scripts/install_koalabyte_one_shot.sh
```

### Step 5: Dry-run before flashing, optional but recommended

Before a full install, you can validate the repo, helper scripts, menu controls, field-readiness files, dashboard JSON, version-handshake path, and optional CAN policy without flashing firmware or installing services:

```bash
bash scripts/install_koalabyte_one_shot.sh --check-only
```

This is the safest first command on a new clone or GitHub Actions runner.

### Step 6: Let it finish

The one-shot installer prepares dependencies, flashes firmware, checks menus, checks the boards, sets up services, writes logs, runs field-readiness checks, runs KoalaByte Doctor, checks the local dashboard JSON path, checks release/log helpers, and creates readiness artifacts. For the optional CAN kit, it auto-detects the adapter: present means setup/checks run; absent means the installer writes `OPTIONAL_CAN_SKIPPED_NOT_PRESENT` and moves on.

### Step 7: Reboot and start using it

```bash
sudo reboot
cd ~/KoalaByte-Blue
bash scripts/koalabyte_blue_boot.sh
```

---

## Useful installer options

```bash
# Normal one-shot install
bash scripts/install_koalabyte_one_shot.sh

# Dry-run: no firmware flashing and no service install
bash scripts/install_koalabyte_one_shot.sh --check-only

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

# Default optional CAN behavior: setup if present, skip if absent
INSTALL_INNOMAKER_CAN=optional bash scripts/install_koalabyte_one_shot.sh

# Force optional CAN to be skipped
INSTALL_INNOMAKER_CAN=0 bash scripts/install_koalabyte_one_shot.sh

# Make CAN strict for a complete hardware build
STRICT_INNOMAKER_CAN=1 bash scripts/install_koalabyte_one_shot.sh
```

---

## What the one-shot installer prepares

1. **Repository readiness** — checks required files, scripts, firmware folders, menu wiring, shell syntax, and expected README markers.
2. **Stable serial aliases** — installs or checks udev rules for `/dev/koalabyte-esp32-dualeye`, `/dev/koalabyte-heltec`, and `/dev/koalabyte-nrf52840`.
3. **Raspberry Pi companion setup** — installs system packages, Python dependencies, the virtual environment, runtime folders, and helper scripts.
4. **KillerKoala AI setup** — prepares the phrase engine and optional TinyLlama/Ollama fallback path.
5. **Heltec T114 combined-safe firmware** — builds/flashes the T114 profile used by BLE/GNSS/status dashboard paths.
6. **ESP32-S3 DualEye firmware** — builds/flashes the DualEye firmware for eyes, face, and display behavior.
7. **KillerKoala eyes and mouth sync** — validates the shared face-state protocol between the ESP32-S3 and Heltec T114.
8. **Menu display sync and AI-face controls** — verifies menu highlight/select sync, touchscreen long-press, double-tap menu reopen, B1 menu reopen, and the 30-second AI-face idle return.
9. **Menus, buttons, antennas, controls, and commands** — confirms menu routing, front button mapping, antenna readiness, BlueZ menu coverage, protected lab-only action coverage, and helper scripts.
10. **Full runtime dependencies and board helpers** — checks required Python imports, project modules, board helper files, BlueZ helper coverage, and command availability.
11. **Field readiness helpers** — validates doctor, udev, boot-service, safe-mode, log export, release package, protocol manifest, dashboard, and docs files.
12. **Version handshake readiness** — checks the Pi-side protocol manifest and attempts ESP32/Heltec version status readiness where ports are available.
13. **Local status dashboard JSON check** — confirms the status dashboard can emit JSON from current log/status files.
14. **Release and log helper checks** — validates the release package builder and log export helpers.
15. **KoalaByte Doctor quick check** — runs the quick diagnostic report.
16. **BLE node manager service** — installs the Pi-side node service with the T114 as the primary board path.
17. **Boot services** — installs or checks service templates for the menu, menu sync, and doctor.
18. **T114 live dashboard status phrases** — verifies the live dashboard phrases used by Heltec Link, Radio/GPS, and Lab Beacon TX.
19. **External antenna readiness** — writes antenna status files for Heltec LoRa, Heltec 2.4 GHz, ESP32-S3 2.4 GHz, and optional Pi adapter paths.
20. **AntEater passive readiness** — prepares passive-readiness status without starting a live scan.
21. **Optional InnoMaker CAN** — auto-detects the optional CAN kit. If present, setup/status checks run. If absent, `OPTIONAL_CAN_SKIPPED_NOT_PRESENT` is written and the installer continues.

Important readiness artifacts:

```text
logs/one_shot_install_status.json
logs/one_shot/control_surface_status.json
logs/one_shot/full_runtime_dependencies.json
logs/one_shot/field_readiness_status.json
logs/menu_actions/menu_action_manifest.json
logs/menu_actions/t114_status_dashboard_status.json
logs/menu_sync/current_menu_state.json
logs/doctor/koalabyte_doctor_status.json
logs/version/koalabyte_version_handshake.json
logs/killerkoala/killerkoala_ai_readiness.json
logs/killerkoala/ollama_setup_status.json
logs/koala_bluez/koala_bluez_module_manifest.json
logs/can/innomaker_optional_status.json
exports/koalabyte_logs_<timestamp>.zip
```

---

## KoalaByte Doctor

KoalaByte Doctor is the quickest way to ask, “Is the build healthy enough to keep going?”

Quick check:

```bash
bash scripts/koalabyte_doctor.sh --quick
```

Full check:

```bash
bash scripts/koalabyte_doctor.sh
```

Strict full check:

```bash
bash scripts/koalabyte_doctor.sh --strict
```

Doctor writes:

```text
logs/doctor/koalabyte_doctor_status.json
```

It checks important files, command availability, existing readiness JSON, disk/memory status, and supporting validation scripts.

---

## Release ZIP package

The repo can build a portable install package for the current branch.

Build locally:

```bash
bash scripts/build_koalabyte_release_package.sh
```

Expected output:

```text
dist/KoalaByte-Blue-install-package.zip
```

If `zip` is not installed, the builder falls back to:

```text
dist/KoalaByte-Blue-install-package.tar.gz
```

The GitHub Actions workflow also includes a release package workflow:

```text
.github/workflows/release-package.yml
```

The package includes the README, `install.sh`, scripts, Pi companion code, firmware folders, docs, systemd templates, udev rules, logrotate config, version manifest, and training/supporting files.

---

## Field readiness tools

### Stable device names

Check the udev rules template:

```bash
bash scripts/install_koalabyte_udev_rules.sh --check-only
```

Install stable aliases on the Pi:

```bash
bash scripts/install_koalabyte_udev_rules.sh
```

Expected aliases include:

```text
/dev/koalabyte-esp32-dualeye
/dev/koalabyte-heltec
/dev/koalabyte-nrf52840
```

### Boot services

Check service templates:

```bash
bash scripts/install_koalabyte_boot_services.sh --check-only
```

Install boot services:

```bash
bash scripts/install_koalabyte_boot_services.sh
```

Service templates:

```text
systemd/koalabyte-menu.service
systemd/koalabyte-menu-sync.service
systemd/koalabyte-doctor.service
```

### Safe mode

Safe mode disables strict optional services and starts from a recovery-friendly state:

```bash
bash scripts/koalabyte_safe_mode.sh
bash scripts/koalabyte_safe_mode.sh --terminal
bash scripts/koalabyte_safe_mode.sh --doctor
```

### Version handshake

```bash
PYTHONPATH=pi-companion python3 scripts/check_koalabyte_version_handshake.py
```

Status output:

```text
logs/version/koalabyte_version_handshake.json
```

### Local status dashboard

JSON check:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koalabyte_status_server.py --json
```

Run the local dashboard:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koalabyte_status_server.py --host 0.0.0.0 --port 8080
```

Then open from another device on the same network:

```text
http://koalabyte-blue.local:8080
```

### Log export

```bash
bash scripts/export_koalabyte_logs.sh
```

Output goes to:

```text
exports/
```

### Log rotation

Check the config:

```bash
bash scripts/install_koalabyte_logrotate.sh --check-only
```

Install the config:

```bash
bash scripts/install_koalabyte_logrotate.sh
```

It installs:

```text
/etc/logrotate.d/koalabyte-blue
```

Source config:

```text
logrotate/koalabyte-blue
```

---

## Main menu overview

| Main item | Plain-English meaning |
|---|---|
| Eucalyptus | Always-on passive BLE logger controls and Koalagotchi mode. |
| Bluetooth Tools | Local Bluetooth/BLE inventory, summaries, BlueZ helper checks, protected lab-only actions, and defensive review tools. |
| Didgeridoo | Heltec T114, GNSS/GPS, Meshtastic, mesh, and protected location tools. |
| CAN Bench Tools | Optional InnoMaker USB-to-CAN bench tools. |
| Reports & Reviews | Report builders, defensive review templates, and Boomerang camera-awareness logbook. |
| System / Companion | KillerKoala voice, XP/status, buttons, settings, and helper controls. |
| Lab | A shorter authorized-lab menu with common safe lab review items and protected BlueZ helpers. |

---

## Menu actions

### Eucalyptus

| Item | What it does |
|---|---|
| Eucalyptus Canopy Status | Shows whether passive BLE logging is running. |
| Eucalyptus Canopy Start | Starts always-on passive BLE logging. |
| Eucalyptus Canopy Stop | Stops always-on passive BLE logging. |
| Eucalyptus Canopy Restart | Restarts passive BLE logging. |
| Eucalyptus Upload Trail | Shows upload/readiness status for saved observation trails. |
| Eucalyptus Koalagotchi Mode | Opens the Koalagotchi cyber-pet screen. |

### Bluetooth Tools

| Item | What it does |
|---|---|
| Scan | Runs a safe local BLE inventory scan. |
| Summary | Summarizes observed local BLE devices. |
| Show Devices | Shows the current local BLE device table. |
| Koala Kapture | Records authorized lab observation metadata. |
| Koala Kry | Replays saved local metadata into the report pipeline. |
| Ear Tag | Named lab BLE beacon helper. |
| KoalaByte Lab | Synthetic owned-device BLE lab advertisement helper. |
| Outback Module Deck | Shows the complete KoalaByte BlueZ module manifest. |
| Gumleaf Gear Check | Inventories local BlueZ helper tools. |
| Eucalyptus Bus Scout | Collects local adapter/controller status. |
| Dropbear Discovery Sweep | Runs bounded local discovery with safe defaults. |
| Billabong HCI Watch | Runs bounded local HCI capture for local analysis. |
| Kookaburra Safe Nest Run | Runs local inventory, status, and bounded discovery together. |
| Joey Target Dossier | Protected lab-only owned-device target info card. |
| Treehouse Service Trace | Protected lab-only owned-device service notes. |
| Gumnut GATT Gatecheck | Protected lab-only owned-device GATT readiness checklist. |
| Outback Radio Ledger | Protected lab-only local adapter ledger. |
| Classic Track Finder | Protected lab-only classic controller listing. |
| Treehouse RFCOMM Wiremap | Protected lab-only RFCOMM binding/status map. |
| Pouch Link Echo | Protected lab-only single owned-device link echo. Requires a target. |
| Gumnut GATT Ghostmap | Protected lab-only owned-device primary GATT service map. Requires a target. |
| that’s not a knife | Defensive local BLE pressure guard. |
| AntEater | Passive BLE risk triage with redacted reports. |
| Urban Poaching | Authorized BLE RSSI lab game. |

Protected Bluetooth actions use the protected-actions password gate. Target-specific protected actions also require:

```bash
export KOALABYTE_BLUEZ_LAB_TARGET=AA:BB:CC:DD:EE:FF
export KOALABYTE_BLUEZ_OWNED_DEVICE=1
```

### Didgeridoo

| Item | What it does |
|---|---|
| Heltec Link | Shows live T114 link state. |
| Radio/GPS | Shows live T114 radio/GPS state. |
| T114 Quick BLE Test Scan | Runs a short bounded passive BLE test through the T114 primary radio path. |
| Lab Beacon TX | Shows safe lab beacon state. |
| Sextant | Gets the current GPS/GNSS location from the Heltec T114 stream. |
| Didgeridoo Status | Shows local Meshtastic/Didgeridoo node status. |
| Didgeridoo Nodes | Shows the Meshtastic node table. |
| Didgeridoo GPS Info | Shows GPS/GNSS information. |
| Protected Location Gate Status | Shows protected-actions password gate state. |
| Protected GNSS Current Fix | Shows current GNSS fix only when the protected location gate allows it. |

### CAN Bench Tools

| Item | What it does |
|---|---|
| Koala Kan Kommander | Opens the InnoMaker USB-to-CAN listen/check workflow. |
| CAN Bench Safety Check | Opens the CAN safe manifest/inventory/status workflow. |

### Reports & Reviews

| Item | What it does |
|---|---|
| Koala Kry RF Review | Writes RF bench isolation and authorization review notes. |
| Report | Writes a Markdown session report. |
| Boomerang | Opens a camera-awareness logbook for manual public observations. |
| Authorized BLE Inventory | Creates a lab inventory from local observations. |
| GATT Readiness Checklist | Generates a pre-test checklist for owned-device GATT review. |
| Pairing Security Review | Reviews owned-device pairing/access-control posture. |
| Lab Beacon Plan | Creates a safe ESP32 demo beacon/peripheral testing plan. |
| Packet Capture Notes | Creates protocol-analysis notes. |
| Defensive Lab Report | Generates a defensive lab report template. |

### System / Companion

| Item | What it does |
|---|---|
| Koala Mode Switcher | Builds, packages, or selects KoalaByte Lab / Koala Konnect for the legacy nRF52840 dongle path. |
| KillerKoala Voice | Previews event reactions and vocabulary by XP rank. |
| Buttons | Shows/checks front-panel GPIO button status. |
| Level / Status | Shows XP and rank. |
| Wake killerkoala | Tests the wake-word flow. |
| Settings | Device and companion settings. |

---

## KillerKoala AI companion overview

KillerKoala is the device personality. The companion is designed to be reliable on a Raspberry Pi 3B+, so it uses a phrase-first system by default and an optional local TinyLlama/Ollama fallback for flexible banter.

Default local AI settings:

```text
INSTALL_KILLERKOALA_OLLAMA=auto
STRICT_KILLERKOALA_OLLAMA=0
KILLERKOALA_BASE_MODEL=tinyllama:1.1b
KILLERKOALA_LLM_MODEL=killerkoala-tinyllama:latest
```

AI helper script:

```bash
bash scripts/setup_killerkoala_ollama.sh
```

Common voice patterns:

```text
killerkoala open <menu item>
killerkoala run <menu item>
killerkoala status
killerkoala level
killerkoala buttons
```

Examples:

```text
killerkoala open Eucalyptus
killerkoala open Didgeridoo
killerkoala run T114 Quick BLE Test Scan
killerkoala open Outback Module Deck
killerkoala open Reports & Reviews
killerkoala status
```

---

## Face, eyes, mouth, vocabulary, and Koalagotchi

The face system connects the ESP32-S3 DualEye and Heltec T114 through a shared `killerkoala_face` protocol.

| Feature | What it means |
|---|---|
| Eyes | The ESP32-S3 DualEye shows the main visual personality. |
| Mouth/status | The Heltec T114 participates in the shared face/status path. |
| Face sync | The Pi validates that eyes and mouth/status agree on the same face-state protocol. |
| Menu sync | The Pi syncs highlighted/selected menu items to Heltec and ESP32-S3 DualEye display paths. |
| AI-face idle return | After menu inactivity or action completion, the AI face returns until B1/menu or touchscreen double-tap reopens the menu. |
| Vocabulary | KillerKoala has gruff cyberpunk/Aussie-style phrases tied to events, XP, ranks, and menu activity. |
| Koalagotchi | Eucalyptus mode turns passive local observations and device events into cyber-pet feedback. |

Check face/mouth sync with:

```bash
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_face_mouth_sync.py --emit-test
```

Check menu/display sync with:

```bash
PYTHONPATH=pi-companion python3 scripts/check_menu_display_sync.py
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

Check optional CAN handling:

```bash
cat logs/can/innomaker_optional_status.json
```

Expected optional CAN statuses include:

```text
OPTIONAL_CAN_CHECK_RECORDED
OPTIONAL_CAN_SKIPPED_NOT_PRESENT
OPTIONAL_CAN_CHECK_ONLY
```

---

## Troubleshooting basics

### Start with Doctor

```bash
bash scripts/koalabyte_doctor.sh --quick
cat logs/doctor/koalabyte_doctor_status.json
```

### Run safe mode

```bash
bash scripts/koalabyte_safe_mode.sh
bash scripts/koalabyte_safe_mode.sh --doctor
bash scripts/koalabyte_safe_mode.sh --terminal
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

### Protected Bluetooth action is blocked

Set up the protected-actions password and, for target-specific checks, set the target variables:

```bash
PYTHONPATH=pi-companion python3 scripts/run_location_password_gate.py setup
export KOALABYTE_BLUEZ_LAB_TARGET=AA:BB:CC:DD:EE:FF
export KOALABYTE_BLUEZ_OWNED_DEVICE=1
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
