# KoalaByte Blue Theme and Menu System

## Current status

This is the current RevA25 theme/menu guide. It replaces the older separate menu-theme and boot-animation notes.

Current approved theme package:

```text
jungle_jumanji_eucalyptus
```

Current approved visual direction:

```text
PORKCHOP-style handheld firmware menu, adapted for KoalaByte Blue
```

That means all menu screens should use the same dark jungle/cyber background, chunky yellow title treatment, green outline/shadow, warm orange accent lines, big rounded menu rows, and readable selected-item descriptions.

Theme source folder:

```text
firmware/esp32-dualeye/themes/
```

Approved visual source-of-truth assets:

```text
firmware/esp32-dualeye/themes/jungle_jumanji_eucalyptus/boot_splash.svg
firmware/esp32-dualeye/themes/jungle_jumanji_eucalyptus/menu_preview_main.svg
firmware/esp32-dualeye/themes/jungle_jumanji_eucalyptus/menu_preview_tools.svg
firmware/esp32-dualeye/themes/jungle_jumanji_eucalyptus/standard_theme_settings_preview.svg
docs/images/koalabyte-blue-menu-overview.svg
```

## Boot splash rules

The approved boot splash uses:

```text
KOALABYTE BLUE title at the top
purple left eye / green right eye koala identity centered below the title
jungle eucalyptus border
bottom boot status text kept clear and readable
```

Firmware path:

```text
firmware/esp32-dualeye/src/boot_animation.cpp
firmware/esp32-dualeye/include/boot_animation.h
firmware/esp32-dualeye/themes/active_theme.h
```

The ESP32 boot animation remains procedural for low memory use, but it should visually follow the approved SVG asset.

## Four menu groups

The Pi companion menu is rendered as four production-facing groups:

```text
Bluetooth Tools
CAN Bench Tools
Reports & Reviews
System / Companion
```

The command keys remain stable for scripts and CI. The menu catalog adds group metadata and the UI sorts the rendered menu by group.

Source-of-truth path:

```text
pi-companion/koalablue/menu_catalog.py
```

## PORKCHOP-style menu rules

The approved menu layout uses:

```text
No overlapping words
all labels and descriptions inside their rounded row borders
selected row with cyber-green glow
current group shown in the header area
section headers shown in terminal preview
B1-B6 footer strip inside its border
leafy eucalyptus border around the menu
chunky yellow/green title treatment
warm orange accent border on group and Boomerang-related panels
large rounded bubbly firmware font style using system fonts only
```

Main menu mode depiction rules:

```text
Eucalyptus Mode must show as a Koalagotchi BLE canopy screen.
Eucalyptus Mode description must mention KillerKoala eating passive Bluetooth eucalyptus leaves.
Boomerang must show as a camera-awareness logbook.
Boomerang description must mention manual public/visible observations, report notes, XP, and staying open until quit.
```

Pi companion menu paths:

```text
pi-companion/koalablue/menu_catalog.py
pi-companion/koalablue/menu_ui.py
pi-companion/koalablue/menu_theme.py
pi-companion/koalablue/menu_screen.py
scripts/run_menu_screen.py
```

Run terminal preview:

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py
```

Run graphical preview window:

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
```

Run fullscreen graphical menu:

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical
```

## Koalagotchi mode screen rules

Eucalyptus Mode and Boomerang use the same family of high-color firmware graphics as the main menu:

```text
chunky KOALAGOTCHI header
black/green jungle HUD background
purple left eye / green right eye KillerKoala mascot
large status cards
warm orange Boomerang accents
cyber-green Eucalyptus accents
B1-B6 / F1-F6 style bottom command strip
```

ESP32 display renderer paths:

```text
firmware/esp32-dualeye/src/koalagotchi_mode_screens.h
firmware/esp32-dualeye/src/koalagotchi_mode_screens.cpp
firmware/esp32-dualeye/src/main.cpp
```

The Pi can request a display screen over serial with a JSON line like:

```json
{"type":"screen","mode":"eucalyptus","mood":"calm","contentment":82,"xp_percent":88}
```

or:

```json
{"type":"screen","mode":"boomerang","mood":"rowdy","contentment":61,"xp_percent":88}
```

## Standard editable theme

User-editable standard theme file:

```text
firmware/esp32-dualeye/themes/standard/theme.json
```

Editable values:

```text
background
font_family
textbox_color
textbox_border
text_color
accent_color
selected_item_color
```

Do not commit third-party font files unless redistribution is permitted. The current firmware and SVG assets use system/fallback font names and procedural text rendering.

## Validation

Run:

```bash
python3 scripts/check_repo_readiness.py
python -m compileall pi-companion scripts
```

Primary flash path:

```bash
bash scripts/flash_all_components.sh --all
```
