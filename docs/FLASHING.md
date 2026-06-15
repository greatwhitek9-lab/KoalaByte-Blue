# Flashing and Installation Guide

This repository contains two pieces of software:

1. **ESP32-S3 DualEye firmware** under `firmware/esp32-dualeye/`.
2. **Raspberry Pi 3B+ companion tools** under `pi-companion/` and `scripts/`.

The ESP32 firmware is ready to build/flash with PlatformIO. The Raspberry Pi companion is installed into a local Python virtual environment.

> Safety boundary: this code is for authorized Bluetooth research, BLE inventory, local logging, AI companion behavior, and lab placeholders only. Offensive lab entries intentionally return blocked placeholder responses and contain no working exploit, bypass, jamming, injection, or brute-force code.

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

### Validate boot/menu firmware wiring

From the repo root:

```bash
python3 scripts/check_boot_animation_config.py
```

Expected result:

```text
KoalaByte Blue boot/menu theme config check passed.
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

If your board's I2S microphone pins have not been mapped yet, the firmware will also report:

```json
{"type":"voice_backend","status":"mic_enabled_pin_mapping_required"}
```

That is expected. Mic wake is enabled by default, but real audio capture requires the exact DualEye board revision I2S pin mapping from the vendor schematic/example.

### Boot animation check

On boot, the ESP32 firmware now runs the procedural KoalaByte Blue splash before normal runtime startup:

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

If the serial boot JSON appears but the display is blank, the firmware is running but the TFT_eSPI display setup likely needs the exact LCD driver and pin mapping for your specific ESP32-S3 DualEye LCD board revision.

Check these first:

```text
firmware/esp32-dualeye/include/config.h
firmware/esp32-dualeye/platformio.ini
```

Then confirm the TFT_eSPI user setup values against the vendor display example for your exact board:

```text
LCD driver
TFT_MOSI
TFT_SCLK
TFT_CS
TFT_DC
TFT_RST
TFT_BL/backlight
rotation
screen width/height
```

### ESP32 menu theme helper

The ESP32 firmware also includes RevA14 menu-theme helper functions for future direct display menu rendering:

```cpp
drawEucalyptusMenuBorder(tft);
drawJungleMenuTitle(tft, "KoalaByte Blue");
drawJungleMenuItem(tft, row, label, selected, enabled);
```

These helpers live in:

```text
firmware/esp32-dualeye/include/menu_theme.h
firmware/esp32-dualeye/src/menu_theme.cpp
```

### One-command helper

From the repo root:

```bash
./scripts/flash_esp32.sh
```

The helper cleans, builds, uploads, prints the expected boot-animation behavior, and opens the serial monitor.

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

The installer creates/updates:

```text
pi-companion/.venv/
```

and runs a Python compile check across `pi-companion/` and `scripts/`.

### Test the Pi boot splash manually

Windowed desktop test:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
```

Fullscreen test:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --duration 3
```

Install desktop-session autostart:

```bash
bash scripts/install_boot_splash_autostart.sh
```

This creates:

```text
~/.config/autostart/koalabyte-blue-boot-splash.desktop
```

The splash will run after the Pi desktop session starts. This is the safest default because it does not alter low-level bootloader, framebuffer, or display-manager settings.

### Test the RevA14 jungle/eucalyptus menu

Terminal preview with eucalyptus branch border:

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py
```

Graphical windowed menu:

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
```

Graphical fullscreen menu:

```bash
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

Urban Poaching authorized lab game:

```bash
PYTHONPATH=pi-companion python3 scripts/run_urban_poaching.py
```

---

## 3. Passive BLE capture outputs

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

## 4. Optional WiGLE upload configuration

WiGLE upload support is present but disabled until credentials and a valid location source are configured.

Set environment variables on the Pi:

```bash
export WIGLE_API_NAME="your_api_name"
export WIGLE_API_TOKEN="your_api_token"
```

Then edit:

```text
pi-companion/config.default.json
```

Required fields:

```json
{
  "wigle": {
    "enabled": true,
    "latitude": 0.0,
    "longitude": 0.0
  }
}
```

Use real coordinates only for your own authorized collection area.

---

## 5. First functional test

1. Flash ESP32.
2. Confirm the boot animation appears or confirm serial JSON reports `"boot_animation":1`.
3. Connect ESP32 to Pi by USB.
4. Install the Pi companion dependencies:

```bash
bash scripts/install_pi.sh
```

5. Test the splash and menu:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
```

6. Optional passive BLE capture test:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kapture.py --duration-seconds 10 --max-records 50
```

Expected behavior:

- ESP32 shows the KoalaByte Blue animated boot splash before normal runtime.
- Serial JSON includes `"boot_animation":1`.
- Pi splash opens in windowed or fullscreen mode.
- Menu validation screen uses the large bubbly jungle/eucalyptus style and responds to keyboard/GPIO/touch input.
- Passive BLE capture writes authorized metadata artifacts under `/blecaptures/koala_kapture/`.
