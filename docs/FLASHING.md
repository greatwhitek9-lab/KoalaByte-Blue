# Flashing and Installation Guide

This repository contains three pieces of software:

1. **ESP32-S3 DualEye firmware** under `firmware/esp32-dualeye/`.
2. **Raspberry Pi 3B+ companion tools** under `pi-companion/` and `scripts/`.
3. **nRF Connect SDK / Zephyr firmware for nRF52840 DK Ear Tag TX Lab** under `firmware/nrf52840-dk-lab-peripheral/`.

The ESP32 firmware builds with PlatformIO. The Pi companion installs into a local Python virtual environment. The nRF52840 DK lab firmware builds with nRF Connect SDK / Zephyr.

> Safety boundary: this code is for authorized Bluetooth research, BLE inventory, local logging, AI companion behavior, synthetic owned-device lab advertising, and safe lab validation only. Koala Kry remains offline metadata replay only.

---

## 1. Validate repository wiring

From the repo root:

```bash
python3 scripts/check_boot_animation_config.py
```

Expected result:

```text
KoalaByte Blue RevA16 config check passed.
```

---

## 2. ESP32-S3 DualEye firmware

Install PlatformIO:

```bash
python3 -m pip install --user platformio
pio --version
```

Build and flash:

```bash
bash scripts/flash_esp32.sh
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

## 3. nRF52840 DK nRF Connect SDK / Zephyr firmware

Requirements:

- Nordic nRF52840 DK / PCA10056
- nRF Connect SDK installed
- `west` command available
- USB cable connected to the DK debug USB port

Build only:

```bash
bash scripts/build_nrf52840_dk_lab.sh
```

Build and flash:

```bash
bash scripts/flash_nrf52840_dk_lab.sh
```

Manual build/flash:

```bash
west build -b nrf52840dk_nrf52840 firmware/nrf52840-dk-lab-peripheral -d build/nrf52840-dk-lab-peripheral
west flash -d build/nrf52840-dk-lab-peripheral
```

Expected BLE advertisement name:

```text
EarTag-TX-Lab
```

The payload is synthetic service data with KBTX magic bytes, static pattern bytes, a sequence counter, and a simple check byte. It does not replay captured packets or captured identifiers.

Build all available firmware targets from one helper:

```bash
bash scripts/build_firmware_all.sh
```

---

## 4. Raspberry Pi companion and Koala BlueZ Tools

Install Raspberry Pi OS with Desktop if you want the fullscreen boot splash and graphical jungle menu. Raspberry Pi OS Lite works for terminal-only use.

Recommended packages:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip bluetooth bluez rfkill sqlite3 libsdl2-2.0-0
```

Install Python dependencies:

```bash
git clone https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
bash scripts/install_pi.sh
```

Test boot splash and menu:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
```

Koala BlueZ Tools:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py status
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py scan --duration 15
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py monitor --duration 20
```

Convenience wrappers:

```bash
bash scripts/run_koala_bluez_inventory.sh
bash scripts/run_koala_bluez_status.sh
bash scripts/run_koala_bluez_scan.sh --duration 15
bash scripts/run_koala_bluez_monitor.sh --duration 20
```

Output is written to:

```text
logs/koala_bluez/
```

---

## 5. Available Pi companion tools

Koala Kapture passive BLE metadata capture:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kapture.py --duration-seconds 30
```

Koala Kry offline replay:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kry.py
```

Koala Kry review manifest:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kry.py --request-rf-transmit --lab-setting --owned-device
```

Ear Tag TX Lab plan artifact:

```bash
PYTHONPATH=pi-companion python3 scripts/run_ear_tag_tx_lab.py
```

Urban Poaching authorized lab game:

```bash
PYTHONPATH=pi-companion python3 scripts/run_urban_poaching.py
```

---

## 6. Passive BLE capture outputs

Koala Kapture writes passive metadata captures to:

```text
/blecaptures/koala_kapture/
```

Capture outputs include:

```text
koala_kapture_YYYYMMDD_HHMMSS.jsonl
koala_kapture_YYYYMMDD_HHMMSS.csv
koala_kapture_YYYYMMDD_HHMMSS_manifest.json
```

Raw MAC logging is enabled in `pi-companion/config.default.json`. Only use this in authorized environments and comply with local law and platform rules.

---

## 7. First functional test

```bash
bash scripts/install_pi.sh
bash scripts/build_firmware_all.sh
bash scripts/flash_nrf52840_dk_lab.sh
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_kapture.py --duration-seconds 30 --target-name EarTag-TX-Lab
```

Expected behavior:

- ESP32 shows the KoalaByte Blue animated boot splash before normal runtime.
- Serial JSON includes `"boot_animation":1`.
- nRF52840 DK advertises as `EarTag-TX-Lab` with synthetic service data.
- Pi splash opens in windowed or fullscreen mode.
- Menu validation screen uses the large bubbly jungle/eucalyptus style.
- Koala BlueZ inventory reports available local BlueZ commands.
- Passive BLE capture writes authorized metadata artifacts under `/blecaptures/koala_kapture/`.
