# KoalaByte Blue Flashing and Installation Guide - RevA25

This repo keeps the current dongle-only, no-custom-PCB KoalaByte Blue software set:

1. **ESP32-S3 DualEye firmware** under `firmware/esp32-dualeye/`.
2. **Raspberry Pi 3B+ companion tools** under `pi-companion/` and `scripts/`.
3. **nRF Connect SDK / Zephyr firmware for the Nordic nRF52840 Dongle KoalaByte Lab profile** under `firmware/nrf52840-dongle-ear-tag-tx-lab/`.
4. **Koala Konnect** as an alternate nRF52840 Dongle USB HCI adapter profile.
5. **Pre-Boot Dongle Mode Selector** to choose KoalaByte Blue Lab Mode or Koala Konnect Mode before the normal boot splash/menu flow.
6. **Koala Kan Kommander InnoMaker CAN support** through the Pi companion.

Safety boundary: this code is for authorized Bluetooth research, BLE inventory, local logging, AI companion behavior, synthetic owned-device lab advertising, scoped CAN observation, completely isolated CAN bench simulator testing, and safe lab validation only. Koala Kry remains offline metadata replay/RF bench review only. Koala Kan Kommander transmit requires both `--bench-simulator` and `--confirm-transmit`.

---

## Fast path: one helper for all components

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
bash scripts/flash_all_components.sh --pi
ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --nrf-lab
bash scripts/flash_all_components.sh --all --build-only
bash scripts/flash_all_components.sh --all --smoke
```

The helper runs the repo readiness check, installs the Pi companion when requested, checks/prepares `west` and `nrfutil` before nRF workflows, flashes ESP32 when requested, builds/packages/flashes the nRF52840 Dongle when requested, and writes a Koala Kan Kommander InnoMaker manifest check. If `NRF_DFU_PORT` is not set, the nRF helper creates the DFU ZIP but does not flash.

---

## west and nrfutil setup

The nRF52840 Dongle build/flash path now includes a tool setup helper:

```bash
bash scripts/setup_nrf_tools.sh
```

It checks:

```text
west      Zephyr/nRF Connect SDK build tool
nrfutil   Nordic DFU package/USB serial flashing tool
```

Strict check:

```bash
STRICT_NRF_TOOLS=1 bash scripts/setup_nrf_tools.sh
```

Check only, without trying to install anything:

```bash
bash scripts/setup_nrf_tools.sh --check-only
```

Build-only nRF flows require `west`; package/flash/cache flows require both `west` and `nrfutil`. The helper is called automatically by:

```text
scripts/install_pi.sh
scripts/flash_all_components.sh
scripts/prepare_dongle_firmware_cache.sh
scripts/build_nrf52840_dongle_lab.sh
scripts/build_nrf52840_dongle_hci_usb_adapter.sh
scripts/flash_nrf52840_dongle_lab_dfu.sh
scripts/flash_nrf52840_dongle_koala_konnect_dfu.sh
```

---

## Pre-boot Lab/Konnect selector

The pre-boot selector runs before the normal KoalaByte Blue boot splash and grouped main menu. It lets the operator choose:

```text
1) KoalaByte Blue Lab Mode
2) Koala Konnect Mode
```

Interactive selector:

```bash
PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py
```

Direct mode selection:

```bash
PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --mode koalabyte_lab
PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --mode koala_konnect
```

Switch the physical nRF52840 Dongle when it is in DFU bootloader mode:

```bash
NRF_DFU_PORT=/dev/ttyACM0 PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --mode koalabyte_lab
NRF_DFU_PORT=/dev/ttyACM0 PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --mode koala_konnect
```

Normal Pi-side startup wrapper:

```bash
bash scripts/koalabyte_blue_boot.sh
```

Wrapper order:

```text
pre-boot mode selector -> KoalaByte Blue boot splash -> grouped main menu
```

Notes:

- The selector does not change the Raspberry Pi bootloader.
- The nRF52840 Dongle can hold only one active profile at a time.
- If no `NRF_DFU_PORT` is available, the selector records the requested mode in `logs/preboot_mode_selection.json` but does not claim the physical dongle was switched.

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
bash scripts/setup_nrf_tools.sh --check-only
PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --noninteractive --no-apply
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

## RevA25 InnoMaker USB-to-CAN listen and transmit support

Koala Kan Kommander uses the optional **InnoMaker USB to CAN Converter kit**.

Physical path:

```text
Raspberry Pi 3B+ USB host
  -> short internal USB data cable
  -> InnoMaker USB to CAN Converter kit
  -> adapter-side CAN_H / CAN_L / GND / optional SHIELD
  -> isolated CAN bench simulator or owned bench harness
```

Do not use the earlier circular CAN panel-port concept. Mount the adapter internally or in a rectangular side/rear service bay with strain relief. Do not wire CAN_H or CAN_L directly to Raspberry Pi GPIO.

Optional Pi setup:

```bash
sudo apt install -y can-utils iproute2
ip link show
sudo ip link set can0 up type can bitrate 500000
ip -details -statistics link show can0
```

Listen/report checks:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py status --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py listen --interface can0 --duration 10
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py report --interface can0
```

Generate synthetic payloads without transmitting:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py generate-payloads --interface can0 --payload-profile all --base-id 0x600 --sequence-count 8 --tag KOALAKAN
```

Transmit to an isolated bench simulator:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py transmit --interface can0 --bench-simulator --confirm-transmit --payload-profile heartbeat --base-id 0x600 --sequence-count 3
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py listen-transmit --interface can0 --bench-simulator --confirm-transmit --can-id 0x600 --data "4B 42 01 00" --duration 10
```

`transmit-placeholder` remains a blocked legacy artifact and never sends frames.

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
bash scripts/setup_nrf_tools.sh --check-only
PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --noninteractive --no-apply
bash scripts/build_firmware_all.sh
NO_MONITOR=1 bash scripts/flash_esp32.sh
bash scripts/build_nrf52840_dongle_lab.sh
bash scripts/flash_nrf52840_dongle_lab_dfu.sh
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py inventory
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py status --xp 100
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py transmit --interface can0 --bench-simulator --confirm-transmit --can-id 0x600 --data "4B 42 01 00"
```

Expected behavior:

- Repo readiness check passes before flashing.
- `west` and `nrfutil` are checked by the flashing/install helpers before nRF build/package/flash actions.
- Pre-boot selector can choose KoalaByte Blue Lab Mode or Koala Konnect Mode.
- ESP32 shows the KoalaByte Blue boot splash before normal runtime.
- ESP32 serial JSON includes `"boot_animation":1`.
- nRF52840 Dongle advertises as `KoalaByte Lab` when Lab mode is flashed.
- Koala Konnect exposes the alternate USB HCI adapter profile when Konnect mode is flashed.
- Pi companion boot splash, grouped menu, BlueZ wrappers, killerkoala preview, and Koala Kan Kommander manifest checks run without missing-file errors.
- CAN transmit sends only when `--bench-simulator` and `--confirm-transmit` are both present.
