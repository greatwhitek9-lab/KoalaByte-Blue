# KoalaByte Blue V2 Heltec Edition

KoalaByte Blue V2 Heltec Edition is the beginner-friendly Raspberry Pi 3B+ build of the KillerKoala cyber companion. It combines a Raspberry Pi, an ESP32-S3 DualEye display board, a Heltec Mesh Node T114, six front buttons, optional antennas, and an optional InnoMaker USB-to-CAN kit.

The project is designed for lawful owned-device labs, defensive Bluetooth observation, Koalagotchi-style companion feedback, Didgeridoo mesh/GNSS status, safe local reports, voice control, and optional isolated CAN bench work.

Use KoalaByte Blue only on your own equipment, your own lab traffic, or systems you have written permission to test.

---

## Beginner summary

Think of the device as four main parts working together:

| Part | Simple role | What it does in KoalaByte Blue |
|---|---|---|
| Raspberry Pi 3B+ | Main brain | Runs the installer, menus, logs, voice commands, KillerKoala companion, local services, and most processing. |
| ESP32-S3 DualEye | Face and local display | Runs the eyes, face feedback, DualEye screen, button/UI feedback, and built-in mic bridge support. |
| Heltec Mesh Node T114 | Radio/GPS board | Provides the T114 nRF52840 path, primary BLE/GNSS status, LoRa/Meshtastic-related checks, and Heltec status/mouth sync. |
| Six 4-pin buttons | Physical controls | Let you move through menus without a keyboard. |
| InnoMaker USB-to-CAN | Optional CAN bench adapter | Used only for isolated owned-bench CAN checks. The InnoMaker CAN kit is optional. |

No custom PCB is required for this profile.

---

## What the boards do

### Raspberry Pi 3B+

The Pi is the host computer. It boots Raspberry Pi OS from the SD card and runs the KoalaByte Blue software. It owns the main menu, Python companion code, logs, system services, voice command routing, KillerKoala AI fallback, BLE node manager, CAN helper scripts, and readiness checks.

The Pi connects to the other boards over USB data cables. Power the Pi from a regulated USB power source or power bank. Do not feed raw lithium battery voltage directly into the Pi.

### ESP32-S3 DualEye

The ESP32-S3 DualEye is the face/display board. In this build it handles the animated eyes, local face state, display feedback, and voice bridge support for the built-in mic path. The installer flashes the ESP32-S3 DualEye firmware with PlatformIO.

The ESP32-S3 connects to the Pi by USB data cable. If your board has an IPEX/u.FL 2.4 GHz connector, use the correct pigtail/antenna. Do not solder directly to an IPEX/u.FL connector.

### Heltec Mesh Node T114

The Heltec Mesh Node T114 is the main T114 radio/GNSS board for this edition. The one-shot installer defaults to the combined-safe firmware profile:

```bash
T114_PLUG_FLASH_PROFILE=combined-safe bash scripts/install_koalabyte_one_shot.sh
```

In this project the T114 provides:

- T114 nRF52840 primary BLE/GNSS controller status over USB serial JSON.
- GNSS/GPS status and current fix handoff to the Pi.
- Didgeridoo and Meshtastic-related status checks.
- LoRa antenna readiness and mesh-node support paths.
- Heltec face/mouth/status sync used by the KillerKoala face system.

The T114 connects to the Pi with a USB-C data cable. Use the correct LoRa antenna for your region before using LoRa/Meshtastic hardware.

### Six front buttons

The six front buttons let you control the device without a keyboard.

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

The InnoMaker CAN kit is optional. It is used for isolated bench CAN workflows only. If it is not plugged in, the one-shot installer records a non-failing optional CAN status and continues.

To make CAN required during a strict hardware build, run:

```bash
STRICT_INNOMAKER_CAN=1 bash scripts/install_koalabyte_one_shot.sh
```

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

## Antenna routing

Use the antenna connector that belongs to each board.

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

Insert the SD card, power the Pi, and SSH into it. Then update the Pi:

```bash
sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

### Step 3: Plug in the boards

Plug these into the Pi:

```text
ESP32-S3 DualEye -> Pi USB port
Heltec Mesh Node T114 -> Pi USB port with USB-C data cable
Optional InnoMaker CAN kit -> Pi USB port
```

### Step 4: Run the installer

From a fresh Pi, run:

```bash
curl -fsSL -o koalabyte-install.sh https://raw.githubusercontent.com/greatwhitek9-lab/KoalaByte-Blue/koalabyte-blue-v2-heltec-edition/install.sh
bash koalabyte-install.sh
```

That bootstrapper clones or updates the repository, then runs the one-shot installer.

If you already cloned the repo, run either:

```bash
bash install.sh
```

or:

```bash
bash scripts/install_koalabyte_one_shot.sh
```

### Step 5: Let it finish

The one-shot installer prepares dependencies, flashes firmware, checks menus, checks the boards, sets up services, writes logs, and creates readiness artifacts.

### Step 6: Reboot and start using it

After the install completes:

```bash
sudo reboot
```

Then open the menu:

```bash
cd ~/KoalaByte-Blue
bash scripts/koalabyte_blue_boot.sh
```

---

## Useful installer options

Run the normal one-shot install:

```bash
bash scripts/install_koalabyte_one_shot.sh
```

Use the normal Heltec combined-safe profile explicitly:

```bash
T114_PLUG_FLASH_PROFILE=combined-safe bash scripts/install_koalabyte_one_shot.sh
```

Skip Heltec flashing while debugging USB/ports:

```bash
FLASH_T114_ON_PLUG=0 bash scripts/install_koalabyte_one_shot.sh
```

Do not fail the whole install if the T114 is not ready yet:

```bash
STRICT_T114_PLUG_FLASH=0 bash scripts/install_koalabyte_one_shot.sh
```

Make full runtime and command dependency checks strict:

```bash
STRICT_FULL_RUNTIME_DEPENDENCIES=1 bash scripts/install_koalabyte_one_shot.sh
```

Make the live T114 dashboard require a connected T114:

```bash
STRICT_T114_STATUS_DASHBOARD=1 bash scripts/install_koalabyte_one_shot.sh
```

Skip optional CAN:

```bash
INSTALL_INNOMAKER_CAN=0 bash scripts/install_koalabyte_one_shot.sh
```

Make optional CAN strict:

```bash
STRICT_INNOMAKER_CAN=1 bash scripts/install_koalabyte_one_shot.sh
```

---

## What the one-shot installer prepares

The one-shot installer now checks and prepares the full build path:

1. **Repository readiness** — checks required files, scripts, firmware folders, menu wiring, shell syntax, and expected README markers.
2. **Raspberry Pi companion setup** — installs system packages, Python dependencies, the virtual environment, runtime folders, and helper scripts.
3. **KillerKoala AI setup** — prepares the phrase engine and optional TinyLlama/Ollama fallback path.
4. **Heltec T114 combined-safe firmware** — builds/flashes the T114 profile used by BLE/GNSS/status dashboard paths.
5. **ESP32-S3 DualEye firmware** — builds/flashes the DualEye firmware for eyes, face, and display behavior.
6. **KillerKoala eyes and mouth sync** — validates the shared face-state protocol between the ESP32-S3 and Heltec T114.
7. **Menus, buttons, antennas, controls, and commands** — confirms menu routing, front button mapping, antenna readiness, and helper scripts.
8. **Full runtime dependencies and board helpers** — checks required Python imports, project modules, board helper files, and command availability.
9. **BLE node manager service** — installs the Pi-side node service with the T114 as the primary board path.
10. **T114 live dashboard status phrases** — verifies the live dashboard phrases used by Heltec Link, Radio/GPS, and Lab Beacon TX.
11. **Didgeridoo/menu action readiness** — validates that menu actions and display-only status rows are registered correctly.
12. **External antenna readiness** — writes antenna status files for Heltec LoRa, Heltec 2.4 GHz, ESP32-S3 2.4 GHz, and optional Pi adapter paths.
13. **AntEater passive readiness** — prepares passive-readiness status without starting a live scan.
14. **Optional InnoMaker CAN** — records CAN setup/inventory/status without blocking deployment unless strict CAN mode is enabled.

Important readiness artifacts:

```text
logs/one_shot_install_status.json
logs/one_shot/control_surface_status.json
logs/one_shot/full_runtime_dependencies.json
logs/menu_actions/menu_action_manifest.json
logs/menu_actions/t114_status_dashboard_status.json
logs/killerkoala/killerkoala_ai_readiness.json
logs/killerkoala/ollama_setup_status.json
```

---

## Main menu overview

The main menu is the top-level screen. Each item opens a submenu.

| Main item | Plain-English meaning |
|---|---|
| Eucalyptus | Always-on passive BLE logger controls and Koalagotchi mode. |
| Bluetooth Tools | Local Bluetooth/BLE inventory, summaries, helper checks, and defensive review tools. |
| Didgeridoo | Heltec T114, GNSS/GPS, Meshtastic, mesh, and protected location tools. |
| CAN Bench Tools | Optional InnoMaker USB-to-CAN bench tools. |
| Reports & Reviews | Report builders, defensive review templates, and Boomerang camera-awareness logbook. |
| System / Companion | KillerKoala voice, XP/status, buttons, settings, and helper controls. |
| Lab | A shorter authorized-lab menu with the most common safe lab review items. |
| Power & Exit | Shutdown, quit, and return controls. |

---

## Eucalyptus submenu

Eucalyptus is the always-on passive BLE logger and Koalagotchi area. It is separate from the T114 Quick BLE Test Scan. Eucalyptus is for longer-running background logging and companion feedback.

| Item | What it does |
|---|---|
| Eucalyptus Canopy Status | Shows whether the passive BLE logger is running and where it is writing status. |
| Eucalyptus Canopy Start | Starts always-on passive BLE logging. |
| Eucalyptus Canopy Stop | Stops always-on passive BLE logging. |
| Eucalyptus Canopy Restart | Restarts the passive BLE logger. |
| Eucalyptus Upload Trail | Shows upload/readiness status for saved observation trails. |
| Eucalyptus Koalagotchi Mode | Opens the Koalagotchi screen where KillerKoala reacts to observed BLE activity like a cyber pet. |
| Back to Main Canopy | Returns to the main menu. |

---

## Bluetooth Tools submenu

Bluetooth Tools is the local BLE toolbox. It is built around safe inventory, local status, report generation, and owned-lab helpers.

| Item | What it does |
|---|---|
| Scan | Runs a safe local BLE inventory scan. |
| Summary | Summarizes observed local BLE devices. |
| Show Devices | Shows the current local BLE device table. |
| Koala Kapture | Records authorized lab observation metadata. |
| Koala Kry | Replays saved local metadata into the report pipeline. |
| Ear Tag | Named lab BLE beacon helper. |
| KoalaByte Lab | Synthetic owned-device BLE lab advertisement helper. |
| Gumleaf Gear Check | Inventories local BlueZ helper tools. |
| Eucalyptus Bus Scout | Collects local adapter/controller status. |
| Dropbear Discovery Sweep | Runs bounded local discovery with safe defaults. |
| Billabong HCI Watch | Runs bounded local HCI capture for local analysis. |
| Kookaburra Safe Nest Run | Runs local inventory, status, and bounded discovery together. |
| that’s not a knife | Defensive local BLE pressure guard. |
| AntEater | Passive BLE risk triage with redacted reports. |
| Urban Poaching | Authorized BLE RSSI lab game. |
| Back to Main Canopy | Returns to the main menu. |

---

## Didgeridoo submenu

Didgeridoo is the T114 / GNSS / mesh area. It includes display-only dashboard rows and clickable actions.

### Live dashboard rows

These rows actively check current status and display only the phrase that matches the current state.

| Item | What it shows |
|---|---|
| Heltec Link | Shows the live T114 link state, such as `Heltec Link: Connected`, `Heltec Link: Waiting`, or `Heltec Link: Disconnected`. |
| Radio/GPS | Shows the current T114 radio/GPS phrase, such as `Radio/GPS: BLE ready · GPS fix`, `Radio/GPS: BLE ready · GPS waiting`, or `Radio/GPS: Offline`. |
| Lab Beacon TX | Shows the safe lab beacon state, such as `Lab Beacon TX: On`, `Lab Beacon TX: Off`, or `Lab Beacon TX: Blocked`. |

### Didgeridoo actions

| Item | What it does |
|---|---|
| T114 Quick BLE Test Scan | Runs a short bounded passive BLE test through the T114 primary radio path. Use this as a quick hardware check, not as the always-on logger. |
| Sextant | Gets the current GPS/GNSS location from the Heltec T114 stream, with protected location handling still respected. |
| Didgeridoo Status | Shows local Meshtastic/Didgeridoo node status. |
| Didgeridoo Nodes | Shows the Meshtastic node table. |
| Didgeridoo GPS Info | Shows GPS/GNSS information from the connected Meshtastic/T114 path. |
| Protected Location Gate Status | Shows whether the protected location gate is configured/unlocked. |
| Protected GNSS Current Fix | Shows the current GNSS fix only when the protected location gate allows it. |
| Back to Main Canopy | Returns to the main menu. |

---

## CAN Bench Tools submenu

CAN tools are optional and only for isolated bench-simulator or owned-harness workflows.

| Item | What it does |
|---|---|
| Koala Kan Kommander | Opens the InnoMaker USB-to-CAN listen/check workflow. |
| CAN Bench Safety Check | Opens the CAN safe manifest, inventory, and status workflow. |
| Back to Main Canopy | Returns to the main menu. |

---

## Reports & Reviews submenu

Reports & Reviews creates notes, checklists, and defensive reports.

| Item | What it does |
|---|---|
| Koala Kry RF Review | Writes RF bench isolation and authorization review notes. No RF is sent by this report item. |
| Report | Writes a Markdown session report. |
| Boomerang | Opens a camera-awareness logbook for manual public observations. It stays open until you quit. |
| Authorized BLE Inventory | Creates a lab inventory from local observations. |
| GATT Readiness Checklist | Generates a pre-test checklist for owned-device GATT review. |
| Pairing Security Review | Reviews owned-device pairing and access-control posture. |
| Lab Beacon Plan | Creates a safe ESP32 demo beacon/peripheral testing plan. |
| Packet Capture Notes | Creates protocol-analysis notes. |
| Defensive Lab Report | Generates a defensive lab report template. |
| Back to Main Canopy | Returns to the main menu. |

---

## System / Companion submenu

System / Companion is where KillerKoala, buttons, XP/status, and settings live.

| Item | What it does |
|---|---|
| Koala Mode Switcher | Builds, packages, or selects KoalaByte Lab / Koala Konnect for the legacy nRF52840 dongle path. |
| KillerKoala Voice | Previews event reactions and vocabulary by XP rank. |
| Buttons | Shows/checks front-panel GPIO button status. |
| Level / Status | Shows XP and rank. |
| Wake killerkoala | Tests the wake-word flow. |
| Restricted Placeholder | Locked non-operational slot reserved for future safe features. |
| Settings | Device and companion settings. |
| Back to Main Canopy | Returns to the main menu. |

---

## Lab submenu

The Lab submenu groups common authorized-lab review items in one place.

| Item | What it does |
|---|---|
| Authorized BLE Inventory | Creates a lab inventory from local observations. |
| GATT Readiness Checklist | Generates a pre-test checklist for owned-device GATT review. |
| Pairing Security Review | Reviews owned-device pairing/access-control posture. |
| Lab Beacon Plan | Creates a safe ESP32 demo beacon/peripheral testing plan. |
| CAN Bench Safety Check | Opens Koala Kan safe manifest/inventory/status workflow. |
| Protected Location Gate Status | Shows protected-actions password gate state. |
| Back to Main Canopy | Returns to the main menu. |

---

## Power & Exit submenu

| Item | What it does |
|---|---|
| Shutdown | Confirms safe shutdown. |
| Quit | Exits the Pi companion UI. |
| Back to Main Canopy | Returns to the main menu. |

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

The helper script is:

```bash
bash scripts/setup_killerkoala_ollama.sh
```

The model status file is:

```text
logs/killerkoala/ollama_setup_status.json
```

If the model is missing or too slow, KillerKoala still works with the built-in vocabulary system.

---

## Voice commands

The wake word is:

```text
killerkoala
```

Common voice patterns are:

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
killerkoala open Reports & Reviews
killerkoala status
```

The voice path is checked by the one-shot installer and by:

```bash
PYTHONPATH=pi-companion python3 scripts/check_voice_menu_launch.py
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_ai.py
```

---

## Face, eyes, mouth, and vocabulary

The face system connects the ESP32-S3 DualEye and Heltec T114 through a shared `killerkoala_face` protocol.

| Feature | What it means |
|---|---|
| Eyes | The ESP32-S3 DualEye shows the main visual personality. |
| Mouth/status | The Heltec T114 participates in the shared face/status path. |
| Face sync | The Pi validates that eyes and mouth/status agree on the same face-state protocol. |
| Vocabulary | KillerKoala has gruff cyberpunk/Aussie-style phrases tied to events, XP, ranks, and menu activity. |
| XP / ranks | The companion can react differently as the user levels up. |

Check face/mouth sync with:

```bash
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_face_mouth_sync.py --emit-test
```

Check voice and vocabulary with:

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py
```

---

## Koalagotchi

Koalagotchi is the companion screen behavior for Eucalyptus mode. It turns passive local BLE observations and device events into a cyber-pet style experience.

In simple terms:

```text
Eucalyptus watches the local BLE environment.
Koalagotchi turns that activity into companion feedback.
KillerKoala gains status/XP-style reactions from what the device observes in your lab.
```

Open it from the menu:

```text
Eucalyptus -> Eucalyptus Koalagotchi Mode
```

Or from the command line:

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py
```

---

## Manual verification commands

After the installer completes, these commands are useful:

```bash
python3 scripts/check_repo_readiness.py
bash scripts/preflight_all_hardware.sh --profile heltec
PYTHONPATH=pi-companion python3 scripts/check_full_runtime_dependencies.py
PYTHONPATH=pi-companion python3 scripts/check_one_shot_controls.py
PYTHONPATH=pi-companion python3 scripts/check_menu_actions.py
PYTHONPATH=pi-companion python3 scripts/check_t114_status_dashboard.py
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_face_mouth_sync.py --emit-test
bash scripts/configure_koalabyte_external_antennas.sh --check-only
PYTHONPATH=pi-companion python3 scripts/run_anteater.py status
```

Test the six physical buttons:

```bash
python3 scripts/test_gpio_buttons.py
```

Check Heltec primary BLE/GNSS status paths:

```bash
python3 scripts/discover_koalabyte_ports.py --profile heltec
cat logs/preflight/koalabyte_ports.env
KOALABYTE_PRIMARY_BLE_PORT=/dev/koalabyte-heltec PYTHONPATH=pi-companion python3 scripts/run_ble_node_manager.py --duration 30
cat logs/gnss/current_fix.json
```

---

## Troubleshooting basics

### The Pi cannot see a board

Run:

```bash
lsusb
python3 scripts/discover_koalabyte_ports.py --profile heltec
```

Use USB data cables, not charge-only cables.

### ESP32 flashing fails

Try setting the port manually:

```bash
ESP32_PORT=/dev/ttyUSB0 bash scripts/install_koalabyte_one_shot.sh
```

### Heltec flashing fails

Try allowing the rest of the install to continue while you debug the T114:

```bash
STRICT_T114_PLUG_FLASH=0 bash scripts/install_koalabyte_one_shot.sh
```

Then verify the Heltec path:

```bash
python3 scripts/discover_koalabyte_ports.py --profile heltec
```

### Local AI setup is slow

The Pi 3B+ is limited. The phrase engine works even when the optional TinyLlama/Ollama path is slow or unavailable.

Skip model setup:

```bash
INSTALL_KILLERKOALA_OLLAMA=0 bash scripts/install_koalabyte_one_shot.sh
```

### CAN is missing

That is okay unless you requested strict CAN. The InnoMaker CAN kit is optional.

---

## Safety boundary

KoalaByte Blue is for lawful owned-device labs and defensive review. The repository focuses on passive observation, local status, reports, readiness checks, companion UI, and isolated bench workflows. Do not use it on systems, vehicles, networks, radios, or devices you do not own or do not have permission to test.
