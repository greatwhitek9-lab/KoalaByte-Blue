# KoalaByte Blue V2 Heltec Edition

KoalaByte Blue V2 Heltec Edition is the Raspberry Pi 3B+ + ESP32-S3 DualEye + Heltec Mesh Node T114 build of the KillerKoala cyber companion. It is built for lawful owned-device labs, defensive Bluetooth observation, Didgeridoo mesh status, Meshtastic/GNSS/LoRa checks, front-panel UI, AntEater passive BLE review, and optional isolated InnoMaker CAN bench work.

Use it only on your own equipment, your own lab traffic, or systems you have written permission to test.

---

## Fast install from a fresh Raspberry Pi 3B+

From a fresh Pi, download the bootstrapper, review it if desired, and run it:

```bash
curl -fsSL -o koalabyte-install.sh https://raw.githubusercontent.com/greatwhitek9-lab/KoalaByte-Blue/koalabyte-blue-v2-heltec-edition/install.sh
bash koalabyte-install.sh
```

That bootstrapper clones or updates this repo on the default deploy branch and then launches the one-shot installer.

Useful install modes:

```bash
bash koalabyte-install.sh install
bash koalabyte-install.sh check-only
bash koalabyte-install.sh repo-only
```

Useful overrides:

```bash
KOALABYTE_INSTALL_DIR=$HOME/KoalaByte-Blue bash koalabyte-install.sh
ESP32_PORT=/dev/ttyUSB0 bash koalabyte-install.sh
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 bash koalabyte-install.sh
INSTALL_INNOMAKER_CAN=0 bash koalabyte-install.sh
STRICT_INNOMAKER_CAN=1 bash koalabyte-install.sh
```

---

## Full one-shot install from a cloned repo

Plug the required boards into the Pi, then run:

```bash
bash install.sh
```

Or, if you are already inside the repository and do not need the bootstrap/update wrapper:

```bash
bash scripts/install_koalabyte_one_shot.sh
```

### Required hardware

```text
Raspberry Pi 3B+ powered from regulated USB
ESP32-S3 DualEye -> Pi USB data cable
Heltec Mesh Node T114 -> Pi USB-C data cable
```

### Optional hardware

```text
InnoMaker CAN kit -> optional Pi USB data cable
```

The InnoMaker CAN kit is optional. If it is not plugged in, the one-shot installer records a non-failing optional CAN status and continues.

---

## What the one-shot installer prepares

The one-shot installer runs these phases:

1. **Repository readiness** — validates README markers, required scripts, firmware folders, menu wiring, GPIO button files, face/mouth sync files, antenna helpers, and shell syntax.
2. **Raspberry Pi companion setup** — prepares the Pi filesystem, Python virtual environment, runtime folders, logs, service assets, and helper scripts.
3. **Heltec T114 plug-in firmware flash** — defaults to `T114_PLUG_FLASH_PROFILE=color-mouth`, which flashes the Heltec mouth/status firmware for shared KillerKoala face-state sync.
4. **ESP32-S3 DualEye firmware flash** — builds and uploads the PlatformIO firmware that drives eyes, local UI, buttons, and companion display feedback.
5. **KillerKoala eyes and mouth sync** — validates the shared `killerkoala_face` USB JSON protocol used by ESP32 eyes and Heltec mouth/status firmware.
6. **Menus, submenus, controls, commands, and antennas** — confirms main menu items, submenu routes, command handlers, six-button GPIO mapping, and antenna readiness status.
7. **BLE node manager service** — installs or refreshes the Pi-side service that listens to the Heltec T114 primary path, optional ESP32 face path, and Pi BlueZ fallback path.
8. **Didgeridoo/menu action readiness** — generates menu action status artifacts for mesh, GNSS, Meshtastic, and protected location-gate flows.
9. **External antenna readiness** — records the expected Heltec LoRa, Heltec 2.4 GHz, ESP32-S3 2.4 GHz, and optional Pi adapter antenna paths.
10. **AntEater passive-readiness status** — writes readiness without starting a live scan.
11. **Optional InnoMaker CAN check** — records optional CAN setup/inventory/status without blocking deployment unless strict CAN mode is requested.

---

## Heltec T114 flashing profiles

Default profile:

```bash
T114_PLUG_FLASH_PROFILE=color-mouth bash scripts/install_koalabyte_one_shot.sh
```

Use this for the normal KoalaByte Blue build. The Heltec board acts as the primary T114/nRF52840 board, LoRa/GNSS/Meshtastic node, and mouth/status face target.

Alternative profile:

```bash
T114_PLUG_FLASH_PROFILE=hci-usb bash scripts/install_koalabyte_one_shot.sh
```

Use `hci-usb` only when you intentionally want the T114 nRF52840 exposed as a USB HCI controller profile instead of the color-mouth profile.

Skip Heltec flashing while debugging:

```bash
FLASH_T114_ON_PLUG=0 bash scripts/install_koalabyte_one_shot.sh
```

Allow Pi/ESP32 setup to continue while investigating a missing Heltec:

```bash
STRICT_T114_PLUG_FLASH=0 bash scripts/install_koalabyte_one_shot.sh
```

---

## Manual verification after flashing

After the one-shot installer completes, run:

```bash
python3 scripts/check_repo_readiness.py
bash scripts/preflight_all_hardware.sh --profile heltec
PYTHONPATH=pi-companion python3 scripts/check_menu_actions.py
PYTHONPATH=pi-companion python3 scripts/check_one_shot_controls.py
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_face_mouth_sync.py --emit-test
python3 scripts/run_didgeridoo.py status
PYTHONPATH=pi-companion python3 scripts/run_meshtastic_app.py status
bash scripts/configure_koalabyte_external_antennas.sh --check-only
PYTHONPATH=pi-companion python3 scripts/run_anteater.py status
```

For physical button testing, run this and press each button once:

```bash
python3 scripts/test_gpio_buttons.py
```

Button map:

```text
Button 1 -> Main Menu -> GPIO5
Button 2 -> Move Left / Back -> GPIO6
Button 3 -> Enter / Select -> GPIO13, hold 3s for shutdown event
Button 4 -> Move Right / Forward -> GPIO19
Button 5 -> Up -> GPIO26
Button 6 -> Down -> GPIO21
```

---

## Hardware layout

| Part | Role | Connection |
|---|---|---|
| Raspberry Pi 3B+ | Main host, menus, logs, voice, services | Pi power + USB devices |
| ESP32-S3 DualEye | Eyes, face, UI, buttons, secondary local BLE node | USB data cable |
| Heltec Mesh Node T114 | Primary T114/nRF52840 board, LoRa, Didgeridoo mesh, Meshtastic/GNSS workflows, mouth/status face | USB-C data cable |
| InnoMaker USB-to-CAN | Optional isolated bench CAN workflow | USB data cable |
| Power bank | Main regulated power source | USB power output |

Power rule: do **not** feed raw lithium battery voltage into the Pi, ESP32-S3, Heltec T114, or CAN adapter.

No custom PCB is required for this profile.

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

---

## Menu map

| Main menu item | What it does |
|---|---|
| Eucalyptus | Passive BLE logger and Koalagotchi-style BLE screen. |
| Bluetooth Tools | Local safe BLE inventory, status, defensive review, AntEater, and lab-only helpers. |
| Didgeridoo | All mesh/T114/Meshtastic/GNSS actions. |
| CAN Bench Tools | Optional InnoMaker USB-to-CAN manifest and isolated bench-simulator workflow. |
| Reports & Reviews | Report generators, Boomerang, and defensive review templates. |
| System / Companion | KillerKoala voice/status, buttons, settings, and helper controls. |

The mesh stack lives under **Didgeridoo**. That submenu contains T114 controller checks, T114 status, Didgeridoo status, Didgeridoo nodes, Didgeridoo GPS info, protected location gate status, protected GNSS current fix, and Meshtastic status/actions.

---

## Core apps

### Eucalyptus

Passive BLE observation and Koalagotchi-style screen mode. It is for local observation, status, XP, and companion UI feedback.

### AntEater

Passive BLE payment-terminal risk triage from existing Heltec primary BLE logs. It does not pair, connect, probe, spoof, jam, or disrupt.

### Didgeridoo

The Didgeridoo app owns the mesh stack. It contains T114 checks, Meshtastic status, node listing, GPS/GNSS info, protected location gate status, and protected GNSS current fix.

### Koala Kan Kommander

Optional InnoMaker USB-to-CAN support for isolated bench-simulator or owned-harness workflows only. It is the only hardware module in the one-shot path that is optional by default.

### KillerKoala companion

Voice/status personality, XP/ranks, face state, buttons, and UI feedback. Ranks are Noob, Hacker, and Legend. Its shared face payload keeps the ESP32-S3 eyes and Heltec mouth synced.

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
