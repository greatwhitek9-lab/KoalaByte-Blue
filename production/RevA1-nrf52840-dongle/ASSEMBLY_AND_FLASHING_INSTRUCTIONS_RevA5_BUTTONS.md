# KoalaByte Blue RevA14 Assembly, Flashing, Buttons, Boot Animation, and Jungle Menu Guide

## RevA14 changes

- Keeps the six-button front-panel GPIO layout from RevA6.
- Keeps Nordic nRF52840 Dongle / PCA10059 as the production BLE board.
- Keeps Nordic nRF52840 DK / PCA10056 as the optional development/debug board.
- Keeps ESP32-S3 DualEye animated boot splash firmware path from RevA13.
- Adds Raspberry Pi companion large bubbly jungle/eucalyptus menu renderer.
- Adds ESP32 display helper functions for eucalyptus branch borders and bubbly menu rows.
- Adds validation scripts and CI checks for ESP32 firmware build and Pi companion Python modules.

## Boot animation behavior

The KoalaByte Blue boot screen includes:

```text
Dark KoalaByte face
Purple pulsing left eye
Blue pulsing right eye
KoalaByte Blue title, with Blue actually blue
BOOTING... label
Animated segmented progress bar
```

ESP32 firmware files:

```text
firmware/esp32-dualeye/src/boot_animation.cpp
firmware/esp32-dualeye/include/boot_animation.h
firmware/esp32-dualeye/include/config.h
```

Pi companion splash files:

```text
pi-companion/koalablue/boot_animation.py
scripts/run_boot_splash.py
scripts/install_boot_splash_autostart.sh
```

## Jungle/eucalyptus menu behavior

The function menu now uses:

```text
large rounded bubbly menu item styling
eucalyptus branch border
leaf accents on selected rows
touch drag scrolling
long-press selection
six front-panel button navigation
```

Pi companion menu theme files:

```text
pi-companion/koalablue/menu_theme.py
pi-companion/koalablue/menu_ui.py
pi-companion/koalablue/menu_screen.py
scripts/run_menu_screen.py
```

ESP32 menu theme helper files:

```text
firmware/esp32-dualeye/include/menu_theme.h
firmware/esp32-dualeye/src/menu_theme.cpp
```

## Button hardware

The nRF52840 Dongle includes one tiny onboard user button, but it is not enough for a front-panel user interface. The production build uses:

```text
Adafruit Tactile Button switch (6mm) x 20 pack, Product ID 367
```

Use six buttons from the pack:

```text
1 Main Menu | 2 Left/Back | 3 Enter/Select + hold Shutdown | 4 Right/Forward | 5 Up | 6 Down
```

## Button wiring

| Button # | Function | Pi BCM GPIO | Pi physical pin | Button other side |
|---:|---|---:|---:|---|
| 1 | Main Menu | GPIO5 | 29 | GND |
| 2 | Move Left / Back | GPIO6 | 31 | GND |
| 3 | Enter / Select; hold for Shutdown | GPIO13 | 33 | GND |
| 4 | Move Right / Forward | GPIO19 | 35 | GND |
| 5 | Up | GPIO26 | 37 | GND |
| 6 | Down | GPIO21 | 40 | GND |
| Shared ground | GND bus | GND | 39 | All button grounds |

Each button is normally open. One leg goes to the assigned GPIO pin, and the other leg goes to GND. The software uses internal pull-up resistors.

## Step-by-step software installation

From the repository root on the Raspberry Pi:

```bash
bash scripts/install_pi.sh
```

For Raspberry Pi OS with Desktop, test the boot splash:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
```

Test the jungle/eucalyptus menu in a window:

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
```

Install desktop-session autostart:

```bash
bash scripts/install_boot_splash_autostart.sh
```

Run the terminal menu validation screen:

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py
```

## Step-by-step button build

1. Print the front-panel/button bezel from the production ZIP. The previous four-button bezel should be replaced by a six-button bezel or drilled panel with six 6mm tactile switch positions.
2. Dry-fit six tactile switches in the bezel/front panel and label the positions left-to-right as 1 through 6.
3. Solder or crimp one signal wire to each button.
4. Daisy-chain the other side of all six buttons to a shared black GND wire.
5. Connect Button 1 to Pi GPIO5 / physical pin 29.
6. Connect Button 2 to Pi GPIO6 / physical pin 31.
7. Connect Button 3 to Pi GPIO13 / physical pin 33.
8. Connect Button 4 to Pi GPIO19 / physical pin 35.
9. Connect Button 5 to Pi GPIO26 / physical pin 37.
10. Connect Button 6 to Pi GPIO21 / physical pin 40.
11. Connect the shared ground to Pi physical pin 39.
12. Add heat-shrink and strain relief so the button harness cannot pull on the Pi header.
13. Run the six-button GPIO test from the repo root:

```bash
python3 scripts/test_gpio_buttons.py
```

14. Press each button from left to right and verify the output matches buttons 1 through 6.
15. Hold Button 3 for 3 seconds and verify a `shutdown` hold event is printed.

## ESP32 flashing

From the repo root:

```bash
bash scripts/flash_esp32.sh
```

Expected ESP32 display behavior:

```text
KoalaByte Blue animated boot splash appears first
Left eye pulses purple
Right eye pulses blue
Progress bar completes
Firmware then emits normal serial JSON boot message
```

Expected serial JSON includes:

```json
{"boot_animation":1}
```

If the display remains blank but serial boot JSON appears, confirm the exact TFT_eSPI LCD setup for the ESP32-S3 DualEye board revision.

## Optional nRF52840 DK flashing

```bash
bash scripts/flash_nrf52840_dk_lab.sh
```

## Validation checklist

- [ ] Pi boots without undervoltage warning.
- [ ] Pi companion dependencies install with `scripts/install_pi.sh`.
- [ ] Pi boot splash runs in windowed test mode.
- [ ] Pi jungle/eucalyptus graphical menu runs in windowed test mode.
- [ ] Terminal menu shows eucalyptus branch preview.
- [ ] Optional Pi desktop autostart file is installed.
- [ ] ESP32 firmware builds with PlatformIO.
- [ ] ESP32 boot animation appears on the DualEye display.
- [ ] ESP32 serial JSON boot message includes `boot_animation`.
- [ ] ESP32 menu theme helper files are present for display menu integration.
- [ ] nRF52840 Dongle enumerates on USB.
- [ ] All six front buttons generate GPIO button events.
- [ ] Button 3 short press emits `select`.
- [ ] Button 3 hold emits `shutdown`.
- [ ] Shared GND bus is secure.
- [ ] Button harness has strain relief.
- [ ] Case closes without pinching wires.
- [ ] 5V rail remains within 5.05 V to 5.15 V under load.
