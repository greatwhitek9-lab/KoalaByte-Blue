# RevA23 KoalaByte Blue Boot Animation and Firmware Themes

## What was added

RevA23 adds a firmware-side theme system for KoalaByte Blue and makes the Jungle/Jumanji eucalyptus style the primary boot/menu theme.

The theme drop zone is:

```text
firmware/esp32-dualeye/themes/
```

Current approved theme files:

```text
firmware/esp32-dualeye/themes/active_theme.h
firmware/esp32-dualeye/themes/README.md
firmware/esp32-dualeye/themes/jungle_jumanji_eucalyptus/theme.json
firmware/esp32-dualeye/themes/jungle_jumanji_eucalyptus/boot_splash.svg
firmware/esp32-dualeye/themes/jungle_jumanji_eucalyptus/menu_background.svg
firmware/esp32-dualeye/themes/jungle_jumanji_eucalyptus/menu_preview_main.svg
firmware/esp32-dualeye/themes/jungle_jumanji_eucalyptus/menu_preview_tools.svg
firmware/esp32-dualeye/themes/jungle_jumanji_eucalyptus/standard_theme_settings_preview.svg
firmware/esp32-dualeye/themes/standard/theme.json
```

## Primary theme

The primary theme is:

```text
jungle_jumanji_eucalyptus
```

It uses:

```text
leafy eucalyptus branch borders
bark/gold jungle-style KoalaByte title text
blue BLUE title text
purple left eye
cyber green right eye
black jungle background
rounded dark text boxes with green edge glow
```

## Approved boot image direction

The approved boot splash now uses:

```text
KoalaByte Blue title at the top
large glowing-eye koala identity centered below the title
purple left eye and green right eye
jungle/eucalyptus border
bottom status: KILLERKOALA ONLINE
```

The approved source asset is:

```text
firmware/esp32-dualeye/themes/jungle_jumanji_eucalyptus/boot_splash.svg
```

The included SVG asset uses chunky jungle-style fallback lettering inspired by the poster reference. No third-party font file is bundled.

## Approved menu direction

The approved menu previews are:

```text
firmware/esp32-dualeye/themes/jungle_jumanji_eucalyptus/menu_preview_main.svg
firmware/esp32-dualeye/themes/jungle_jumanji_eucalyptus/menu_preview_tools.svg
firmware/esp32-dualeye/themes/jungle_jumanji_eucalyptus/standard_theme_settings_preview.svg
```

Menu layout rules:

```text
No overlapping words
All labels and descriptions stay inside the rounded row borders
Selected row uses a cyber-green glow
Descriptions wrap in the right-side text area
Bottom B1-B6 control strip stays inside its border
```

## ESP32 firmware behavior

The firmware still runs:

```cpp
setupDisplay();
runBootAnimation();
```

inside `setup()` before normal runtime initialization.

The procedural ESP32 boot animation now reads compile-time color constants from:

```text
firmware/esp32-dualeye/themes/active_theme.h
```

The active theme is named in:

```text
firmware/esp32-dualeye/include/config.h
```

```cpp
#define KOALABLUE_ACTIVE_THEME "jungle_jumanji_eucalyptus"
#define KOALABLUE_THEMES_DIR "firmware/esp32-dualeye/themes"
```

## Standard editable theme

The standard editable theme lives at:

```text
firmware/esp32-dualeye/themes/standard/theme.json
```

Users can change:

```text
background
font_family
textbox_color
textbox_border
text_color
accent_color
selected_item_color
```

For ESP32 firmware builds, `theme.json` is a source-of-truth manifest for future loaders and maker tooling. The active compile-time colors currently come from `active_theme.h` so the firmware remains simple and reliable on constrained hardware.

## Display dependency

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

The firmware boot JSON reports:

```json
"boot_animation": 1
```

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

## CI validation

The repository includes:

```text
.github/workflows/koalabyte-blue-ci.yml
scripts/check_repo_readiness.py
```

The workflow validates ready-to-flash repository wiring, compiles the Pi companion Python modules, checks nRF Connect SDK / Zephyr project structure, and builds the ESP32 PlatformIO firmware.

## Notes

The ESP32 animation remains procedural instead of relying on large binary frame assets. That keeps the repo lightweight and easy to build. The SVG theme assets are included as the approved visual source of truth for theme previews, Pi-side loaders, documentation, and future conversion into RGB565 assets if needed.
