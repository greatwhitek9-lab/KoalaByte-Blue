# RevA13 KoalaByte Blue Boot Animation

## What was added

RevA13 adds a real animated boot splash path for KoalaByte Blue in two places:

1. **ESP32-S3 DualEye firmware boot animation**
   - `firmware/esp32-dualeye/src/boot_animation.cpp`
   - `firmware/esp32-dualeye/include/boot_animation.h`
   - called from `setup()` before button/BLE setup and before the JSON boot event is emitted.

2. **Raspberry Pi companion fullscreen boot splash**
   - `pi-companion/koalablue/boot_animation.py`
   - `scripts/run_boot_splash.py`
   - optional desktop autostart template at `pi-companion/autostart/koalabyte-blue-boot-splash.desktop`
   - installer at `scripts/install_boot_splash_autostart.sh`

Both versions use a dark KoalaByte Blue splash concept with:

```text
Purple left eye pulse
Blue right eye pulse
KoalaByte Blue title
Blue rendered as true blue
BOOTING... label
Animated progress bar
```

## ESP32 firmware behavior

The firmware now runs:

```cpp
setupDisplay();
runBootAnimation();
```

inside `setup()` before normal runtime initialization.

Feature toggles are in:

```text
firmware/esp32-dualeye/include/config.h
```

Relevant settings:

```cpp
#define ENABLE_DISPLAY_BOOT_ANIMATION 1
#define BOOT_ANIMATION_TOTAL_MS 2500
#define BOOT_ANIMATION_FRAME_MS 50
#define DISPLAY_ROTATION 0
```

The firmware boot JSON also reports:

```json
"boot_animation": 1
```

## ESP32 display dependency

The PlatformIO project includes:

```ini
bodmer/TFT_eSPI@^2.5.43
```

TFT_eSPI still needs the correct board display setup for the exact ESP32-S3 DualEye LCD revision. If the screen is blank, confirm the display driver, SPI pins, backlight pin, and rotation against the vendor example for the exact board.

## Install and validate ESP32 firmware

From the repo root:

```bash
python3 scripts/check_repo_readiness.py
bash scripts/flash_esp32.sh
```

The legacy `scripts/check_boot_animation_config.py` wrapper remains for older workflows, but new validation should use `scripts/check_repo_readiness.py`.

The flash helper cleans, builds, uploads, prints expected boot-animation behavior, and opens the serial monitor at 115200 baud.

## Pi companion boot splash

Install Pi companion dependencies:

```bash
bash scripts/install_pi.sh
```

Run a windowed test from the repository root:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
```

Run fullscreen:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --duration 3
```

Install desktop-session autostart:

```bash
bash scripts/install_boot_splash_autostart.sh
```

This installs:

```text
~/.config/autostart/koalabyte-blue-boot-splash.desktop
```

The autostart path runs when the Pi desktop session starts. For an earlier pre-desktop boot splash, use a graphical boot service after the display stack and framebuffer are confirmed on the target OS image.

## CI validation

The repository includes:

```text
.github/workflows/koalabyte-blue-ci.yml
scripts/check_repo_readiness.py
```

The workflow validates ready-to-flash repository wiring, compiles the Pi companion Python modules, checks nRF Connect SDK / Zephyr project structure, and builds the ESP32 PlatformIO firmware.

## Notes

This RevA13 implementation is procedural, not binary frame-based. That keeps the repo lightweight and easy to build. A later revision can replace the procedural drawing with RGB565 frame assets generated from the exact approved splash art.
