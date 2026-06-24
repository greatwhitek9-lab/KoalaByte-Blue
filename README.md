# KoalaByte Blue V2 Heltec Edition

KoalaByte Blue V2 Heltec Edition is the Raspberry Pi + ESP32-S3 DualEye + Heltec T114 build of the KillerKoala cyber companion. It is built for lawful owned-device labs, defensive Bluetooth observation, Didgeridoo mesh status, front-panel UI, AntEater passive BLE review, and optional isolated CAN bench work.

Use it only on your own equipment, your own lab traffic, or systems you have written permission to test.

---

## Full one-shot install

The preferred deployment flow is simple: plug the required boards into the Pi, run one command, and let the installer handle Pi setup, Heltec flashing, ESP32-S3 flashing, control checks, services, and readiness artifacts.

```bash
bash scripts/install_koalabyte_one_shot.sh
```

### Required hardware for the one-shot installer

Plug these in before running the command:

```text
Raspberry Pi 3B+ powered from regulated USB
ESP32-S3 DualEye -> Pi USB data cable
Heltec Mesh Node T114 -> Pi USB-C data cable
```

Optional hardware:

```text
InnoMaker CAN kit -> optional Pi USB data cable
```

The InnoMaker CAN kit is optional. If it is not plugged in, the one-shot installer records a non-failing optional CAN status and continues.

---

## What the one-shot installer flashes and prepares

The one-shot installer runs these phases in order.

### Phase 1 — Repository readiness

Command run by installer:

```bash
python3 scripts/check_repo_readiness.py
```

This confirms the branch has the required installer scripts, Didgeridoo menu wiring, antenna helpers, GPIO button files, face/mouth sync checker, and README deployment markers before touching firmware.

### Phase 2 — Raspberry Pi companion setup

Command run by installer:

```bash
bash scripts/install_pi.sh
```

This prepares the Pi-side companion environment. It installs/checks Python dependencies, creates runtime log folders, prepares service assets, generates protocol artifacts, and sets up the Heltec plug-in flashing flow.

The Pi is not “flashed” like a microcontroller. The installer prepares the Pi filesystem, Python companion app, services, logs, and helper scripts so the Pi can control the ESP32-S3, Heltec T114, menus, buttons, antennas, and companion workflows.

### Phase 3 — Heltec T114 plug-in firmware flash

The Heltec T114 is flashed from the Pi during the Pi install phase through:

```bash
bash scripts/flash_t114_when_plugged.sh
```

Default profile:

```bash
T114_PLUG_FLASH_PROFILE=color-mouth
```

The default `color-mouth` profile flashes the Heltec T114 color-mouth/status firmware. That firmware listens for the shared `killerkoala_face` USB JSON payload so the Heltec mouth/status face stays in sync with the ESP32-S3 eyes.

Alternative profile:

```bash
T114_PLUG_FLASH_PROFILE=hci-usb bash scripts/install_koalabyte_one_shot.sh
```

Use `hci-usb` only when you intentionally want the Heltec T114 nRF52840 exposed as a USB HCI controller profile instead of the color-mouth profile.

The installer waits for the Heltec on one of the normal USB paths or aliases, such as:

```text
/dev/koalabyte-heltec
/dev/ttyACM0
/dev/ttyACM1
/dev/ttyUSB0
/dev/ttyUSB1
```

Strict Heltec behavior is on by default:

```bash
STRICT_T114_PLUG_FLASH=1
```

That means a missing required Heltec T114 can fail the one-shot deployment. To keep the Pi/ESP32 setup moving while debugging a missing Heltec, use:

```bash
STRICT_T114_PLUG_FLASH=0 bash scripts/install_koalabyte_one_shot.sh
```

To skip Heltec plug-in flashing entirely:

```bash
FLASH_T114_ON_PLUG=0 bash scripts/install_koalabyte_one_shot.sh
```

### Phase 4 — ESP32-S3 DualEye firmware flash

Command run by installer:

```bash
bash scripts/flash_esp32.sh
```

This flashes the ESP32-S3 DualEye firmware. The ESP32-S3 handles the eyes, face display, local UI, front-panel integration, secondary local BLE node, and KillerKoala eye rendering.

The installer passes `NO_MONITOR=1` by default so the flash process does not hang by opening a serial monitor after upload.

If the ESP32-S3 port is detected automatically, no override is needed. If you know the port, set it explicitly:

```bash
ESP32_PORT=/dev/ttyUSB0 bash scripts/install_koalabyte_one_shot.sh
```

If upload stalls at `Connecting...`, put the ESP32-S3 into manual bootloader mode:

```text
Hold BOOT
Tap RESET/EN
Release RESET/EN
Wait about 2 seconds
Release BOOT
Run the one-shot command again
```

### Phase 5 — KillerKoala eyes and mouth sync

Command run by installer:

```bash
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_face_mouth_sync.py --emit-test
```

This sends a short shared `killerkoala_face` payload to both face targets:

```text
ESP32-S3 DualEye -> renders eyes
Heltec T114 color-mouth firmware -> renders mouth/status face
```

The sync checker confirms:

```text
payload type: killerkoala_face
transport: usb-cdc
left eye: UV/purple
right eye: green
states: wake, listening, thinking, speaking, action, success, error
```

By default, the protocol validation is required, but the physical serial write test is non-strict. To make deployment fail if either device does not accept the sync payload, run:

```bash
STRICT_FACE_MOUTH_SYNC=1 bash scripts/install_koalabyte_one_shot.sh
```

Status file:

```text
logs/killerkoala_face/face_mouth_sync_status.json
```

### Phase 6 — Menus, submenus, buttons, controls, commands, and antennas

Command run by installer:

```bash
PYTHONPATH=pi-companion python3 scripts/check_one_shot_controls.py
```

This confirms the deployed control surface is complete. It checks:

```text
all main menu items
all submenu routes
all enabled menu command handlers
Didgeridoo mesh commands
T114 helper commands
Meshtastic helper commands
location-gate helper commands
six-button front-panel GPIO map
required command/control helper scripts
antenna readiness status files
shared face/mouth protocol
```

Status file:

```text
logs/one_shot/control_surface_status.json
```

### Phase 7 — BLE node manager service

Command run by installer:

```bash
bash scripts/install_ble_node_manager_service.sh
```

This installs or refreshes the Pi service that listens to the Heltec T114 primary BLE serial path, optional ESP32 face path, and Pi BlueZ fallback path. The expected primary Heltec path is usually:

```text
/dev/koalabyte-heltec
```

The installer uses environment fallbacks so these also work:

```text
KOALABYTE_PRIMARY_BLE_PORT
KOALABYTE_HELTEC_USB_PORT
HELTEC_PORT
```

### Phase 8 — Didgeridoo/menu action readiness

Command run by installer:

```bash
PYTHONPATH=pi-companion python3 scripts/check_menu_actions.py
```

This generates the menu action manifest and confirms every enabled menu leaf has a handler and every submenu target exists.

Status files:

```text
logs/menu_actions/menu_action_manifest.json
logs/menu_actions/menu_action_status.json
```

### Phase 9 — External antenna readiness

Command run by installer:

```bash
bash scripts/configure_koalabyte_external_antennas.sh --check-only
```

This records the expected antenna routing:

```text
Heltec T114 LoRa connector -> region-matched LoRa antenna
Heltec T114 2.4 GHz connector -> additional case-mounted 2.4 GHz antenna
ESP32-S3 DualEye 2.4 GHz connector -> ESP32-S3 2.4 GHz antenna
Raspberry Pi 3B+ -> no required external antenna; optional USB wireless adapter only
```

Status files:

```text
logs/koalabyte_external_antenna_status.json
logs/t114_lora_external_antenna_status.json
logs/t114_2g4_antenna_status.json
logs/esp32s3_dualeye_2g4_antenna_status.json
logs/pi_2g4_external_antenna_status.json
```

### Phase 10 — AntEater passive-readiness status

The installer writes AntEater readiness without starting a live scan.

Status file:

```text
logs/anteater/status.json
```

The readiness marker confirms AntEater is passive/ad-only and does not pair, connect, write, jam, spoof, or run live activity during flashing.

### Phase 11 — Optional InnoMaker CAN kit

The installer checks InnoMaker CAN support only as an optional step.

If the CAN kit is missing, deployment continues and the installer writes:

```text
logs/can/innomaker_optional_status.json
```

To skip optional CAN checks completely:

```bash
INSTALL_INNOMAKER_CAN=0 bash scripts/install_koalabyte_one_shot.sh
```

To make CAN strict only when you intentionally want it to block deployment:

```bash
STRICT_INNOMAKER_CAN=1 bash scripts/install_koalabyte_one_shot.sh
```

---

## Quick deployment command

Use this for normal deployment:

```bash
bash scripts/install_koalabyte_one_shot.sh
```

Use this when you need to specify the ESP32 upload port:

```bash
ESP32_PORT=/dev/ttyUSB0 bash scripts/install_koalabyte_one_shot.sh
```

Use this when you want the Heltec HCI USB profile instead of the default color-mouth profile:

```bash
T114_PLUG_FLASH_PROFILE=hci-usb bash scripts/install_koalabyte_one_shot.sh
```

---

## Manual verification after flashing

After the one-shot installer completes, run:

```bash
python3 scripts/check_repo_readiness.py
PYTHONPATH=pi-companion python3 scripts/check_menu_actions.py
PYTHONPATH=pi-companion python3 scripts/check_one_shot_controls.py
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_face_mouth_sync.py --emit-test
python3 scripts/run_didgeridoo.py status
bash scripts/configure_koalabyte_external_antennas.sh --check-only
PYTHONPATH=pi-companion python3 scripts/run_anteater.py status
python3 scripts/preflight_all_hardware.py --profile heltec
```

For physical button testing, run this and press each button once:

```bash
python3 scripts/test_gpio_buttons.py
```

The button map is:

```text
Button 1 -> Main Menu -> GPIO5
Button 2 -> Move Left / Back -> GPIO6
Button 3 -> Enter / Select -> GPIO13, hold 3s for shutdown event
Button 4 -> Move Right / Forward -> GPIO19
Button 5 -> Up -> GPIO26
Button 6 -> Down -> GPIO21
```

---

## What this branch is for

This branch is the deployable Heltec Edition profile for:

- Raspberry Pi 3B+ as the Linux companion host.
- Waveshare ESP32-S3-DualEye-LCD-1.28 as the face, eyes, buttons, UI display, and secondary local BLE node.
- Heltec Mesh Node T114 as the primary BLE board, LoRa board, Didgeridoo mesh board, and color-mouth/status face target.
- InnoMaker USB-to-CAN adapter as an optional isolated CAN bench accessory.
- USB power bank / regulated USB power, not raw battery voltage.

No custom PCB is required for this profile.

---

## Hardware layout

| Part | Role | Connection |
|---|---|---|
| Raspberry Pi 3B+ | Main host, menus, logs, voice, services | Pi power + USB devices |
| ESP32-S3 DualEye | Eyes, face, UI, buttons, secondary BLE | USB data cable |
| Heltec Mesh Node T114 | Primary BLE, LoRa, Didgeridoo mesh, GNSS-aware workflows, mouth/status face | USB-C data cable |
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
