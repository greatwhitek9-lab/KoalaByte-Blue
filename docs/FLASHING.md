# Flashing and Installation Guide

This repository contains three pieces of software:

1. **ESP32-S3 DualEye firmware** under `firmware/esp32-dualeye/`.
2. **Raspberry Pi 3B+ companion tools** under `pi-companion/` and `scripts/`.
3. **nRF52840 DK Ear Tag TX Lab firmware** under `firmware/nrf52840-dk-lab-peripheral/`.

The ESP32 firmware is ready to build/flash with PlatformIO. The Raspberry Pi companion is installed into a local Python virtual environment. The nRF52840 DK lab firmware builds with nRF Connect SDK / Zephyr.

> Safety boundary: this code is for authorized Bluetooth research, BLE inventory, local logging, AI companion behavior, synthetic owned-device lab advertising, and safe lab validation only. Koala Kry remains offline metadata replay only.

---

## 1. Flash the ESP32-S3 DualEye

### Requirements

Install on your desktop/laptop:

- Python 3.10+
- PlatformIO Core, or VS Code with the PlatformIO extension
- USB-C data cable

### Install PlatformIO Core

```bash
python3 -m pip install --user platformio
```

Verify:

```bash
pio --version
```

### Connect the board

1. Plug the ESP32-S3 DualEye into your computer with a USB-C data cable.
2. Put the board in normal boot mode.
3. If upload fails, hold **BOOT**, tap **RESET**, release **BOOT**, and retry.

### Validate boot/menu/Ear Tag wiring

From the repo root:

```bash
python3 scripts/check_boot_animation_config.py
```

Expected result:

```text
KoalaByte Blue boot/menu/Kry/EarTag config check passed.
```

### Build firmware

```bash
cd firmware/esp32-dualeye
pio run
```

### Flash firmware

```bash
pio run -t upload
```

### Open serial monitor

```bash
pio device monitor -b 115200
```

Expected boot output includes JSON similar to:

```json
{"type":"boot","device":"esp32-dualeye","companion":"killerkoala","wake_word":"killerkoala","boot_animation":1}
```

### Boot animation check

On boot, the ESP32 firmware runs the procedural KoalaByte Blue splash before normal runtime startup:

```cpp
setupDisplay();
runBootAnimation();
```

Expected display behavior:

```text
Dark KoalaByte face
Purple pulsing left eye
Blue pulsing right eye
KoalaByte Blue title, with Blue actually blue
BOOTING... label
Animated segmented progress bar
```

If the serial boot JSON appears but the display is blank, confirm the TFT_eSPI LCD setup for your specific ESP32-S3 DualEye LCD board revision.

### One-command helper

From the repo root:

```bash
./scripts/flash_esp32.sh
```

---

## 2. Install the Raspberry Pi 3B+ companion

### Install Raspberry Pi OS

1. Flash Raspberry Pi OS with Desktop to a 32 GB or larger microSD card if you want the fullscreen boot splash and graphical jungle menu.
2. Use Raspberry Pi OS Lite only if you do not need the graphical boot splash or graphical menu.
3. Enable SSH if desired.
4. Boot the Pi and connect to network.

### Install system packages

For the Pi companion with graphical boot splash/menu:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip bluetooth bluez sqlite3 libsdl2-2.0-0
```

### Install KoalaByte Blue Python dependencies

```bash
git clone https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
bash scripts/install_pi.sh
```

The installer creates/updates `pi-companion/.venv/` and runs a Python compile check across `pi-companion/` and `scripts/`.

### Test the Pi boot splash manually

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --duration 3
```

### Test the RevA14 jungle/eucalyptus menu

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical
```

### Run available Pi companion tools manually

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

## 3. Flash the nRF52840 DK Ear Tag TX Lab firmware

### Requirements

- Nordic nRF52840 DK / PCA10056
- nRF Connect SDK installed
- `west` command available
- USB cable connected to the DK debug USB port

### Build and flash

```bash
bash scripts/flash_nrf52840_dk_lab.sh
```

Manual commands:

```bash
west build -b nrf52840dk_nrf52840 firmware/nrf52840-dk-lab-peripheral -d build/nrf52840-dk-lab-peripheral
west flash -d build/nrf52840-dk-lab-peripheral
```

Expected BLE advertisement name:

```text
EarTag-TX-Lab
```

The payload is synthetic service data with KBTX magic bytes, static pattern bytes, a sequence counter, and a simple check byte. It does not replay captured packets or captured identifiers.

---

## 4. Passive BLE capture outputs

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

## 5. First functional test

1. Flash ESP32.
2. Confirm the boot animation appears or confirm serial JSON reports `"boot_animation":1`.
3. Install the Pi companion dependencies.
4. Flash the nRF52840 DK Ear Tag TX Lab firmware.
5. Confirm passive scan sees `EarTag-TX-Lab`.

```bash
bash scripts/install_pi.sh
bash scripts/flash_nrf52840_dk_lab.sh
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
PYTHONPATH=pi-companion python3 scripts/run_koala_kapture.py --duration-seconds 30 --target-name EarTag-TX-Lab
```

Expected behavior:

- ESP32 shows the KoalaByte Blue animated boot splash before normal runtime.
- Serial JSON includes `"boot_animation":1`.
- Pi splash opens in windowed or fullscreen mode.
- Menu validation screen uses the large bubbly jungle/eucalyptus style and responds to keyboard/GPIO/touch input.
- nRF52840 DK advertises as `EarTag-TX-Lab` with synthetic service data.
- Passive BLE capture writes authorized metadata artifacts under `/blecaptures/koala_kapture/`.
