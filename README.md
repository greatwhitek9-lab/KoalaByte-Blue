# KoalaByte Blue / killerkoala AI Companion Firmware RevA25

<p align="center">
  <strong>Your Bluetooth sidekick in the wild.</strong><br>
  Raspberry Pi 3B+ + ESP32-S3 DualEye + Heltec Mesh Node T114 firmware/runtime notes and Pi companion scripts for lawful, owned-device Bluetooth lab work, passive observation, LoRa/Meshtastic-style side-node experiments, companion UI, reporting, and optional isolated CAN bench work.
</p>

<p align="center">
  <img src="docs/images/koalabyte-blue-menu-overview.svg" alt="KoalaByte Blue jungle eucalyptus menu overview" width="760">
</p>

> **Use it right:** KoalaByte Blue is for lawful education, owned-device research, defensive testing, and authorized Bluetooth/CAN/LoRa assessment only. Keep scans, captures, reviews, mesh experiments, and bench tests inside your own lab, your own devices, or written scope.

---

## Main branch hardware profile

The `main` branch is the USB-module production branch. It is intentionally scoped to common USB modules and does not require a custom PCB.

| Component | Exact model / type | Connection | Purpose |
|---|---|---|---|
| Main SBC | Raspberry Pi 3 Model B+ | Main host | Linux companion, menus, logs, reports, voice/AI wrapper. |
| Display/UI board | Waveshare ESP32-S3-DualEye-LCD-1.28 | USB data cable | Boot splash, menu UI, eyes, buttons, and optional local BLE observations. |
| LoRa/BLE side node | Heltec Mesh Node T114 Rev. 2.0 / HT-N5262 class board | USB-C data cable / CDC ACM serial | Optional LoRa, Meshtastic-style, GNSS-aware, or BLE-adjacent side-node workflow. |
| CAN adapter | InnoMaker USB to CAN Converter kit | USB | Optional isolated bench-simulator or owned-harness CAN work. |
| Power | PIFFA-style 50000 mAh USB power bank, 22.5 W class | USB regulated output | Main simplified production power source. |

### Heltec Mesh Node T114 board notes

The Heltec Mesh Node T114 is an optional KoalaByte Blue side-node board, not the main display/eyes board. Treat it as the LoRa/BLE radio node that can sit above or behind the ESP32-S3 DualEye in the stacked case.

| Heltec T114 item | README-level detail |
|---|---|
| MCU | Nordic nRF52840, ARM Cortex-M4F, 64 MHz, 256 KB RAM, 1 MB flash. |
| LoRa radio | Semtech SX1262 sub-GHz LoRa transceiver. |
| Wireless roles | BLE 5.0, IEEE 802.15.4/OpenThread-capable silicon, and LoRa/Meshtastic-style side-node experiments. |
| Optional onboard display | 1.14 inch 135×240 TFT, ST7789V over SPI, when using a T114 variant that includes the screen. |
| GNSS | GNSS module interface using NMEA over UART on supported builds/variants. |
| USB | USB-C device connection that appears as a CDC ACM serial device. |
| Board IO | One user button, one green LED, SK6812 RGB LED strip support, and 2×13 2.54 mm expansion headers. |
| Power connectors | Li-Po battery and solar panel JST-style 2-pin 1.25 mm connectors are present on the board, but KoalaByte Blue should normally power it from regulated USB unless the power design has been reviewed. |

Power path:

```text
USB power bank
  -> Raspberry Pi 3B+ micro-USB power input

Raspberry Pi USB ports or optional powered USB hub
  -> ESP32-S3 DualEye
  -> Heltec Mesh Node T114 USB-C
  -> optional InnoMaker USB-to-CAN adapter
```

Do **not** route raw lithium battery voltage into the Pi, ESP32-S3, Heltec T114 USB input, or CAN adapter.

---

## BLE / LoRa node roles on main

The normal main-branch wireless layout is:

| Node | Role | Notes |
|---|---|---|
| ESP32-S3 DualEye BLE | Primary local UI node | Local display/controller-side BLE observations for the Eucalyptus Mode UI and companion state. |
| Heltec Mesh Node T114 | Optional LoRa/BLE side node | USB-C serial side node for LoRa, Meshtastic-style, GNSS-aware, or supplemental BLE-adjacent workflows. |
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

# Discover KoalaByte ports with Heltec T114 priority
python3 scripts/discover_koalabyte_ports.py --profile heltec

# Full non-flashing preflight for the Heltec T114 profile
python3 scripts/preflight_all_hardware.py --profile heltec

# Build/package without flashing or installing services
bash scripts/flash_all_components.sh --all --build-only

# Safe smoke checks after selected actions
bash scripts/flash_all_components.sh --all --smoke
```

The Heltec T114 is currently documented as a USB-C serial side node in this README. Use the Heltec-specific preflight commands to confirm the Pi sees it before adding or flashing any future T114 firmware target.

---

## Boot / flash mode instructions

Use this section before running the one-shot install or any individual flash target.

| Hardware | Needs manual boot mode? | When to do it |
|---|---|---|
| **ESP32-S3 DualEye** | Usually no. The USB serial bridge normally auto-enters download mode. Manual BOOT mode may be needed if upload stalls at `Connecting...`. | Before `--install-firmware`, `--all`, or `--esp32` only if auto-upload fails. |
| **Heltec Mesh Node T114** | Not for normal KoalaByte runtime/preflight. Firmware work depends on the T114 build target or installed bootloader. | Plug in by USB-C data cable for serial discovery/preflight. Use a dedicated T114 firmware workflow only after it is added and reviewed. |
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

### Heltec Mesh Node T114 serial check

1. Connect the Heltec T114 to the Pi with a USB-C **data** cable.
2. Check for a CDC ACM serial device:

```bash
ls /dev/ttyACM* /dev/serial/by-id/* 2>/dev/null
```

3. Run KoalaByte's Heltec-priority port discovery:

```bash
python3 scripts/discover_koalabyte_ports.py --profile heltec
```

4. Review the generated environment file:

```bash
cat logs/preflight/koalabyte_ports.env
```

5. The expected runtime variable for the board is:

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0
```

Use the detected path from the preflight output if your Pi assigns a different port.

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
- Heltec T114 LoRa/Meshtastic-style side-node discovery and preflight.
- KillerKoala XP and ranks: Noob, Hacker, Legend.
- Local defensive monitor suite.
- Boomerang camera-awareness logbook.
- Authorized BLE inventory and report helpers.
- Optional InnoMaker USB-to-CAN bench-simulator workflows.

Eucalyptus Mode visualizes passive logs only. It does not start pairing, probing, disruption, access, or offensive Bluetooth workflows. Heltec T114 LoRa work should stay limited to lawful, local, owned, or licensed/scope-approved mesh experiments. CAN transmit remains gated for isolated bench-simulator or owned-harness use only.

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
```

---

## Smoke checks

```bash
python3 scripts/check_repo_readiness.py
PYTHONPATH=pi-companion python3 scripts/check_eucalyptus_cyberpet.py
PYTHONPATH=pi-companion python3 scripts/check_thats_not_a_knife_monitors.py
PYTHONPATH=pi-companion python3 scripts/run_thats_not_a_knife_loop.py --once
python3 scripts/preflight_all_hardware.py --profile heltec
```

---

## Project vibe

KoalaByte Blue is supposed to feel like a real little cyber field companion: practical enough for a bench, weird enough to be memorable, and safe enough to demo without turning your lab into chaos. killerkoala watches the canopy, eats Bluetooth eucalyptus data in Eucalyptus Mode, keeps a contentment meter, gains XP through approved successful actions, and only celebrates behavior that stays inside the lab scope. The Heltec T114 gives the build a proper long-range radio tail without changing the ESP32-S3 DualEye's job as the face and front-panel UI.
