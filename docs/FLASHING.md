# KoalaByte Blue Flashing and Installation Guide - RevA23

This repo keeps the current dongle-only, no-custom-PCB KoalaByte Blue software set:

1. **ESP32-S3 DualEye firmware** under `firmware/esp32-dualeye/`.
2. **Raspberry Pi 3B+ companion tools** under `pi-companion/` and `scripts/`.
3. **nRF Connect SDK / Zephyr firmware for the Nordic nRF52840 Dongle KoalaByte Lab profile** under `firmware/nrf52840-dongle-ear-tag-tx-lab/`.
4. **Optional Koala Kan Kommander InnoMaker CAN support** through the Pi companion. This is not a flashed firmware target; it is a passive SocketCAN status/listen/report plug-in.

Safety boundary: this code is for authorized Bluetooth research, BLE inventory, local logging, AI companion behavior, synthetic owned-device lab advertising, scoped CAN observation, and safe lab validation only. Koala Kry remains offline metadata replay only. Koala Kan Kommander does not transmit raw CAN frames.

---

## Fast path: one helper for all components

From the repo root, run the readiness check first:

```bash
python3 scripts/check_repo_readiness.py
```

Expected result:

```text
KoalaByte Blue repo readiness check passed.
Ready-to-flash file wiring is present for ESP32, nRF52840 Dongle/DFU, Pi companion, and Koala Kan Kommander InnoMaker CAN support.
```

Run the all-component helper:

```bash
bash scripts/flash_all_components.sh --all
```

Useful variants:

```bash
# Install/update only the Raspberry Pi companion
bash scripts/flash_all_components.sh --pi

# Flash only the ESP32-S3 DualEye; optional port override
ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32

# Build/package/flash the nRF52840 Dongle KoalaByte Lab profile
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --nrf-lab

# Build only without uploading firmware
bash scripts/flash_all_components.sh --all --build-only

# Run local safe smoke checks after install/flash actions
bash scripts/flash_all_components.sh --all --smoke
```

The helper runs the repo readiness check, installs the Pi companion when requested, flashes ESP32 when requested, builds/packages/flashes the nRF52840 Dongle when requested, and writes a Koala Kan Kommander InnoMaker manifest check. If `NRF_DFU_PORT` is not set, the nRF helper creates the DFU ZIP but does not flash.

---

## Raspberry Pi 3B+ companion install

Recommended Raspberry Pi OS packages:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip bluetooth bluez rfkill sqlite3 libsdl2-2.0-0 iproute2 can-utils
```

Install/update the companion environment:

```bash
git clone https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
bash scripts/install_pi.sh
```

Safe local tests:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py inventory
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py status --xp 100
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
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

## nRF52840 Dongle KoalaByte Lab firmware

Requirements:

- Nordic nRF52840 Dongle / PCA10059 / NRF52840-DONGLE.
- nRF Connect SDK installed.
- `west` command available.
- `nrfutil` available for DFU package/USB serial flashing.
- Dongle placed into bootloader mode for DFU flashing.

Build only:

```bash
bash scripts/build_nrf52840_dongle_lab.sh
```

Manual build:

```bash
west build -b nrf52840dongle_nrf52840 firmware/nrf52840-dongle-ear-tag-tx-lab -d build/nrf52840-dongle-lab
```

Create a DFU package without flashing:

```bash
bash scripts/flash_nrf52840_dongle_lab_dfu.sh
```

Flash after identifying the Dongle DFU serial port:

```bash
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_nrf52840_dongle_lab_dfu.sh
```

Expected BLE advertisement name:

```text
KoalaByte Lab
```

---

## Optional Koala Konnect profile

Koala Konnect is an alternate nRF52840 Dongle profile that turns the dongle into a USB HCI Bluetooth adapter. It cannot run at the same time as KoalaByte Lab on the same dongle.

```bash
bash scripts/build_koala_konnect.sh
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_koala_konnect.sh
```

For build-only multi-target checks:

```bash
BUILD_KOALA_KONNECT=1 bash scripts/build_firmware_all.sh
```

---

## RevA23 InnoMaker USB-to-CAN support

Koala Kan Kommander uses the optional **InnoMaker USB to CAN Converter kit**.

Physical path:

```text
Raspberry Pi 3B+ USB host
  -> short internal USB data cable
  -> InnoMaker USB to CAN Converter kit
  -> adapter-side CAN_H / CAN_L / GND / optional SHIELD
  -> authorized bench harness or owned-device test network
```

Do not use the earlier circular CAN panel-port concept. Mount the adapter internally or in a rectangular side/rear service bay with strain relief. Do not wire CAN_H or CAN_L directly to Raspberry Pi GPIO.

Optional Pi setup:

```bash
sudo apt install -y can-utils iproute2
ip link show
sudo ip link set can0 up type can bitrate 500000
ip -details -statistics link show can0
```

Passive plug-in checks:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py status --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py listen --interface can0 --duration 10
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py report --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py transmit-placeholder
```

`transmit-placeholder` writes a blocked-action artifact. It does not transmit CAN frames.

---

## Outback BlueZ Module Deck

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py status
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py scan --duration 15
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py monitor --duration 20
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py all-safe --duration 15
```

Target-specific notes require an owned/scope-approved target:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py gatt-readiness --target AA:BB:CC:DD:EE:FF --owned-device
```

The Outback BlueZ Module Deck hashes/redacts Bluetooth addresses by default unless `--raw-addresses` is explicitly passed.

---

## First functional test checklist

```bash
python3 scripts/check_repo_readiness.py
bash scripts/install_pi.sh
bash scripts/build_firmware_all.sh
NO_MONITOR=1 bash scripts/flash_esp32.sh
bash scripts/build_nrf52840_dongle_lab.sh
bash scripts/flash_nrf52840_dongle_lab_dfu.sh
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py inventory
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py status --xp 100
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
```

Expected behavior:

- Repo readiness check passes before flashing.
- ESP32 shows the KoalaByte Blue boot splash before normal runtime.
- ESP32 serial JSON includes `"boot_animation":1`.
- nRF52840 Dongle advertises as `KoalaByte Lab` with synthetic service data after DFU flashing.
- Pi companion boot splash, menu, BlueZ wrappers, killerkoala preview, and Koala Kan Kommander manifest checks run without missing-file errors.
