# KoalaByte Blue Theme and Menu System

## Current status

This is the current RevA23 theme/menu guide. It replaces the older separate RevA12/RevA13/RevA14 menu-theme and boot-animation notes.

Current approved theme:

```text
jungle_jumanji_eucalyptus
```

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

## Menu rules

The approved menu layout uses:

```text
no overlapping words
all labels and descriptions inside their rounded row borders
selected row with cyber-green glow
descriptions wrapped in the right-side description area
B1-B6 footer strip inside its border
leafy eucalyptus border around the menu
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
