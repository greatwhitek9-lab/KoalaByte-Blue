# KoalaByte Blue V2 Heltec Edition Flashing and Installation Guide

This repo now documents the `koalabyte_blue_v2_heltec_edition` USB-module software set:

1. **Raspberry Pi 3B+ companion tools** under `pi-companion/` and `scripts/`.
2. **ESP32-S3 DualEye firmware** under `firmware/esp32-dualeye/` for the face, eyes, buttons, UI, and secondary BLE node.
3. **Heltec Mesh Node T114 onboard nRF52840** as the primary BLE board and core Heltec Edition LoRa radio board, discovered over USB-C CDC serial.
4. **Raspberry Pi onboard BlueZ** as the secondary/fallback host BLE node.
5. **Koala Kan Kommander support for the InnoMaker USB to CAN Converter kit** through the Pi companion.
6. **Legacy external nRF52840 Dongle firmware targets** remain present as explicit opt-in compatibility targets only. They are not the default BLE architecture for the Heltec Edition.

Readiness keywords: `flash_all_components.sh`, `scripts/setup_heltec_t114_tools.sh`, `Heltec Mesh Node T114`, `KOALABYTE_PRIMARY_BLE_PORT`, `ESP32-S3 DualEye`, `InnoMaker USB to CAN Converter kit`.

Safety boundary: this code is for authorized Bluetooth research, BLE inventory, local logging, AI companion behavior, owned-device lab validation, scoped CAN observation, and isolated CAN bench simulator testing only. Koala Kan Kommander transmit requires both `--bench-simulator` and `--confirm-transmit`.

---

## Fast path: one helper for the Heltec Edition

From the repo root, run the readiness check first:

```bash
python3 scripts/check_repo_readiness.py
```

Run the all-component helper:

```bash
bash scripts/flash_all_components.sh --all
```

Useful variants:

```bash
# Pi companion only
bash scripts/flash_all_components.sh --pi

# ESP32-S3 DualEye only
ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32

# Install/start the BLE node manager with the Heltec T114 as primary BLE
KOALABYTE_PRIMARY_BLE_PORT=/dev/koalabyte-heltec bash scripts/flash_all_components.sh --ble-node-manager

# Discover Heltec Edition ports without flashing
python3 scripts/discover_koalabyte_ports.py --profile heltec
python3 scripts/preflight_all_hardware.py --profile heltec

# Build/package without flashing or installing services
bash scripts/flash_all_components.sh --all --build-only

# Safe local smoke checks after selected actions
bash scripts/flash_all_components.sh --all --smoke
```

The helper runs the repo readiness check, installs the Pi companion when requested, runs `scripts/setup_heltec_t114_tools.sh`, flashes the ESP32-S3 DualEye when requested, installs the BLE node manager service with the Heltec T114 nRF52840 as the primary BLE board, and writes Koala Kan Kommander status artifacts for the InnoMaker USB to CAN Converter kit.

---

## Heltec T114 dependencies

The Heltec dependency helper is now part of the flasher and Pi installer:

```bash
bash scripts/setup_heltec_t114_tools.sh
```

It checks or installs:

- Python runtime modules: `pyserial` and `bleak`.
- USB/udev/BlueZ commands: `lsusb`, `udevadm`, `bluetoothctl`, and `rfkill`.
- Stable udev aliases, especially `/dev/koalabyte-heltec`.
- Heltec-priority port discovery through `scripts/discover_koalabyte_ports.py --profile heltec`.
- Optional `west`, `nrfutil`, and nRF Connect SDK tooling for future Heltec T114 nRF52840 firmware targets.

Strict runtime dependency check:

```bash
STRICT_HELTEC_T114_TOOLS=1 bash scripts/setup_heltec_t114_tools.sh
```

Optional Zephyr/NCS preparation for future Heltec T114 firmware work:

```bash
INSTALL_HELTEC_NRF_TOOLS=1 bash scripts/setup_heltec_t114_tools.sh
```

The normal Heltec Edition flasher runs this automatically before the BLE node manager service is installed:

```bash
bash scripts/flash_all_components.sh --install-firmware
```

---

## BLE node manager architecture

The Heltec Edition BLE architecture is:

| Node | Role | Port variable |
|---|---|---|
| Heltec Mesh Node T114 onboard nRF52840 | Primary BLE board | `KOALABYTE_PRIMARY_BLE_PORT` / `KOALABYTE_HELTEC_USB_PORT` |
| ESP32-S3 DualEye | Secondary local UI BLE node | `KOALABYTE_ESP32_FACE_PORT` / `ESP32_PORT` |
| Raspberry Pi onboard BlueZ | Secondary/fallback host BLE node | `KOALABYTE_PI_BLUEZ_NODE=1` |

Run discovery:

```bash
python3 scripts/discover_koalabyte_ports.py --profile heltec
cat logs/preflight/koalabyte_ports.env
```

Manual service runner:

```bash
KOALABYTE_PRIMARY_BLE_PORT=/dev/koalabyte-heltec \
KOALABYTE_ESP32_FACE_PORT=/dev/koalabyte-esp32-eyes \
PYTHONPATH=pi-companion python3 scripts/run_ble_node_manager.py --duration 30
```

Install the persistent service:

```bash
bash scripts/install_ble_node_manager_service.sh
```

---

## Raspberry Pi 3B+ companion install

Recommended Raspberry Pi OS packages are installed by `scripts/setup_system_packages.sh`, including USB/udev/BlueZ support for the Heltec T114, `python3-serial`, CAN utilities, audio/TTS tools, and GPIO helpers.

Manual package baseline:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip python3-serial usbutils udev bluetooth bluez rfkill sqlite3 libsdl2-2.0-0 iproute2 can-utils espeak-ng espeak alsa-utils libasound2-plugins pulseaudio-utils portaudio19-dev python3-pyaudio
```

Install/update the companion environment:

```bash
git clone https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
bash scripts/install_pi.sh
```

Safe local tests:

```bash
bash scripts/setup_heltec_t114_tools.sh --check-only
python3 scripts/discover_koalabyte_ports.py --profile heltec
python3 scripts/preflight_all_hardware.py --profile heltec
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py inventory
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py status --xp 100
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
KOALABYTE_TTS=1 PYTHONPATH=pi-companion python3 scripts/run_boomerang.py
```

---

## ESP32-S3 DualEye firmware

Install PlatformIO:

```bash
python3 -m pip install --user platformio
pio --version
```

Build and flash:

```bash
bash scripts/flash_esp32.sh
```

Noninteractive flash without opening the serial monitor:

```bash
NO_MONITOR=1 ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_esp32.sh
```

Manual build:

```bash
cd firmware/esp32-dualeye
pio run
pio run -t upload
pio device monitor -b 115200
```

Expected serial boot JSON includes:

```json
{"type":"boot","device":"esp32-dualeye","companion":"killerkoala","wake_word":"killerkoala","boot_animation":1}
```

---

## Heltec Mesh Node T114 serial check

Connect the Heltec T114 to the Raspberry Pi with a USB-C **data** cable, then run:

```bash
ls /dev/ttyACM* /dev/serial/by-id/* 2>/dev/null
bash scripts/setup_heltec_t114_tools.sh --check-only
python3 scripts/discover_koalabyte_ports.py --profile heltec
cat logs/preflight/koalabyte_ports.env
```

Expected environment keys include:

```bash
KOALABYTE_PRIMARY_BLE_PORT=/dev/koalabyte-heltec
KOALABYTE_HELTEC_USB_PORT=/dev/koalabyte-heltec
```

Use the discovered path if your Pi assigns a different serial device.

---

## Legacy external nRF52840 Dongle targets

The old external dongle firmware folders and scripts are retained for compatibility and bench comparison only. They are **not** the default Heltec Edition BLE architecture.

Build legacy external dongle BLE observer firmware only when explicitly requested:

```bash
BUILD_LEGACY_NRF_DONGLE=1 bash scripts/build_firmware_all.sh
# or
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --nrf-ble-primary
```

Legacy Lab/Konnect profiles are also explicit opt-in paths:

```bash
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --nrf-lab
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --nrf-konnect
```

---

## CAN bench adapter

The InnoMaker USB-to-CAN kit does not get flashed by KoalaByte. The Pi uses Linux SocketCAN, `can-utils`, `python-can`, and Koala Kan Kommander scripts.

```bash
bash scripts/setup_can0.sh --interface can0 --bitrate 500000
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py inventory --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py status --interface can0
```

---

## KillerKoala voice/TTS

The same flow installs KillerKoala voice/TTS support through `scripts/setup_system_packages.sh` when system packages are enabled. Raspberry Pi OS installs `espeak-ng`, `espeak`, ALSA utilities/plugins, PulseAudio CLI utilities, PortAudio, and `python3-pyaudio`.

Enable spoken Boomerang/KillerKoala alerts after installation with:

```bash
KOALABYTE_TTS=1 PYTHONPATH=pi-companion python3 scripts/run_boomerang.py
```
