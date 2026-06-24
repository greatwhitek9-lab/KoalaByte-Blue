# KoalaByte Blue / killerkoala AI Companion Firmware RevA25

<p align="center">
  <strong>Your Bluetooth sidekick in the wild.</strong><br>
  Raspberry Pi 3B+ + ESP32-S3 DualEye firmware and Pi companion scripts for lawful, owned-device Bluetooth lab work, passive observation, companion UI, reporting, and optional isolated CAN bench work.
</p>

<p align="center">
  <img src="docs/images/koalabyte-blue-menu-overview.svg" alt="KoalaByte Blue jungle eucalyptus menu overview" width="760">
</p>

> **Use it right:** KoalaByte Blue is for lawful education, owned-device research, defensive testing, and authorized Bluetooth/CAN assessment only. Keep scans, captures, reviews, and bench tests inside your own lab, your own devices, or written scope.

---

## Main branch hardware profile

The `main` branch is the USB-module production branch. It is intentionally scoped to common USB modules and does not require a custom PCB.

| Component | Exact model / type | Connection | Purpose |
|---|---|---|---|
| Main SBC | Raspberry Pi 3 Model B+ | Main host | Linux companion, menus, logs, reports, voice/AI wrapper. |
| Display/UI board | Waveshare ESP32-S3-DualEye-LCD-1.28 | USB data cable | Boot splash, menu UI, eyes, buttons, and optional local BLE observations. |
| CAN adapter | InnoMaker USB to CAN Converter kit | USB | Optional isolated bench-simulator or owned-harness CAN work. |
| Power | PIFFA-style 50000 mAh USB power bank, 22.5 W class | USB regulated output | Main simplified production power source. |

Power path:

```text
USB power bank
  -> Raspberry Pi 3B+ micro-USB power input

Raspberry Pi USB ports or optional powered USB hub
  -> ESP32-S3 DualEye
  -> optional InnoMaker USB-to-CAN adapter
```

Do **not** route raw lithium battery voltage into the Pi, ESP32-S3, or CAN adapter.

---

## BLE node roles on main

The normal main-branch BLE layout is:

| Node | Role | Notes |
|---|---|---|
| ESP32-S3 DualEye BLE | Primary local node | Local display/controller-side BLE observations for the Eucalyptus Mode UI and companion state. |
| Raspberry Pi onboard BlueZ | Host observer / fallback | Linux observer for enrichment, logging, and fallback BLE status checks. |

The Pi-side service is:

```text
koalabyte-ble-node-manager.service
```

It writes merged logs to:

```text
logs/ble_nodes/ble_events.jsonl
logs/ble_nodes/ble_state.json
logs/ble_nodes/service.log
logs/ble_nodes/service.err
```

Detailed role notes are in:

```text
docs/MAIN_BLE_NODE_ROLES.md
```

---

## One-shot install / flash

Start with Raspberry Pi OS Lite 64-bit, enable SSH, clone the repo, and run the readiness check:

```bash
sudo apt update
sudo apt install -y git

git clone https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
python3 scripts/check_repo_readiness.py
```

Normal one-shot install:

```bash
bash scripts/flash_all_components.sh --install-firmware
```

That one command installs/updates the Pi companion, prepares firmware tooling, flashes the ESP32-S3 DualEye when connected, installs/enables the BLE node manager service, and runs the CAN manifest check.

Useful variants:

```bash
# Pi companion only
bash scripts/flash_all_components.sh --pi

# ESP32-S3 DualEye only
ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32

# Build/package without flashing or installing services
bash scripts/flash_all_components.sh --all --build-only

# Safe smoke checks after selected actions
bash scripts/flash_all_components.sh --all --smoke
```

---

## Boot / flash mode instructions

Use this section before running the one-shot install or any individual flash target.

| Hardware | Needs manual boot mode? | When to do it |
|---|---|---|
| **ESP32-S3 DualEye** | Usually no. The USB serial bridge normally auto-enters download mode. Manual BOOT mode may be needed if upload stalls at `Connecting...`. | Before `--install-firmware`, `--all`, or `--esp32` only if auto-upload fails. |
| **InnoMaker USB-to-CAN Converter kit** | No. KoalaByte does not flash firmware to it. | Never for KoalaByte setup. Plug it in by USB only after the Pi is running, or before install if you only want manifest/status checks. |
| **Raspberry Pi onboard BLE / BlueZ** | No. | Never. It is configured by Linux packages/services, not board boot mode. |

### ESP32-S3 DualEye normal flashing path

1. Connect the ESP32-S3 DualEye to the Pi with a USB **data** cable.
2. Check the port:

```bash
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

3. Flash normally:

```bash
ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32
```

4. If upload works, do not use BOOT mode.

### ESP32-S3 DualEye manual BOOT/download mode

Use this only if the ESP32 upload stalls at `Connecting...`, fails to sync, or repeatedly resets without accepting firmware.

1. Hold the **BOOT** button.
2. Tap **RESET/EN** once while still holding **BOOT**.
3. Release **RESET/EN**.
4. Keep holding **BOOT** for about two seconds.
5. Release **BOOT**.
6. Run the flash command again:

```bash
ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32
```

7. After flashing, tap **RESET/EN** once to boot the app if the board stays in download mode.

### InnoMaker USB-to-CAN kit

The InnoMaker USB-to-CAN kit does **not** need a boot mode for KoalaByte. Do not press, short, or reflash anything on the CAN adapter for this project.

1. Plug the InnoMaker adapter into the Pi by USB.
2. Confirm Linux sees it:

```bash
lsusb
ip link
```

3. Use KoalaByte only for manifest/status or isolated bench-simulator workflows:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
```

---

## Key safe actions

- Safe local BLE inventory and passive observation.
- Eucalyptus Mode Koalagotchi Bluetooth scanner/logger screen.
- KillerKoala XP and ranks: Noob, Hacker, Legend.
- Local defensive monitor suite.
- Boomerang camera-awareness logbook.
- Authorized BLE inventory and report helpers.
- Optional InnoMaker USB-to-CAN bench-simulator workflows.

Eucalyptus Mode visualizes passive logs only. It does not start pairing, probing, disruption, access, or offensive Bluetooth workflows. CAN transmit remains gated for isolated bench-simulator or owned-harness use only.

---

## Useful docs

```text
docs/MAIN_BLE_NODE_ROLES.md
docs/FLASHING.md
docs/EUCALYPTUS_ALWAYS_ON_BLE_REVA8.md
docs/CAMERA_AWARENESS_LOGGER.md
docs/THATS_NOT_A_KNIFE_SERVICE.md
docs/KOALA_BLUEZ_TOOLS_REVA16.md
docs/ORDERABLE_PARTS_LIST.md
docs/PRODUCTION_FILES.md
docs/POWER_BANK_WIRING_MAIN.svg
production/RevA17-dongle-only/BATTERY_POWER_2S_18650.md
```

---

## Smoke checks

```bash
python3 scripts/check_repo_readiness.py
PYTHONPATH=pi-companion python3 scripts/check_eucalyptus_cyberpet.py
PYTHONPATH=pi-companion python3 scripts/check_thats_not_a_knife_monitors.py
PYTHONPATH=pi-companion python3 scripts/run_thats_not_a_knife_loop.py --once
```

---

## Project vibe

KoalaByte Blue is supposed to feel like a real little cyber field companion: practical enough for a bench, weird enough to be memorable, and safe enough to demo without turning your lab into chaos. killerkoala watches the canopy, eats Bluetooth eucalyptus data in Eucalyptus Mode, keeps a contentment meter, gains XP through approved successful actions, and only celebrates behavior that stays inside the lab scope.
