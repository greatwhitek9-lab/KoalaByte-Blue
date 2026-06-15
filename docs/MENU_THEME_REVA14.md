# RevA14 Jungle/Eucalyptus Menu Theme

## What changed

RevA14 changes the KoalaByte Blue function menu styling to a large rounded jungle-title look bordered by eucalyptus branches.

The theme is applied to:

```text
pi-companion/koalablue/menu_theme.py
pi-companion/koalablue/menu_ui.py
pi-companion/koalablue/menu_screen.py
scripts/run_menu_screen.py
pi-companion/config.default.json
firmware/esp32-dualeye/include/menu_theme.h
firmware/esp32-dualeye/src/menu_theme.cpp
```

## Style notes

The menu uses:

```text
large rounded/bubbly menu item typography
eucalyptus branch border
leaf accents on the selected row
rounded pill-style menu selections
touch scrolling
long-press selection
front-panel button navigation
```

No commercial or third-party font files are bundled. The renderer attempts to use rounded system fonts such as Cooper Black or Arial Rounded when available, then falls back to DejaVu Sans.

## Pi touchscreen / desktop menu

Run the graphical jungle menu in a window:

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
```

Run fullscreen:

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical
```

The same script still supports terminal validation mode:

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py
```

## Controls

```text
Keyboard: w/s/a/d or arrow keys, Enter/Space select, m main menu, q quit
Buttons: B1 menu, B2 previous/back, B3 select/hold shutdown, B4 next, B5 up, B6 down
Touch: drag/scroll through menu rows, long press to select
```

## ESP32 display helper

The ESP32 firmware now includes reusable menu theme helpers:

```cpp
drawEucalyptusMenuBorder(tft);
drawJungleMenuTitle(tft, "KoalaByte Blue");
drawJungleMenuItem(tft, row, label, selected, enabled);
```

These helpers are staged for the ESP32 display menu path and use the same visual language as the Pi menu: eucalyptus border, rounded/bubbly text treatment, leaf accents, and selected-row highlighting.

## Validation

Run:

```bash
python3 scripts/check_boot_animation_config.py
python -m compileall pi-companion scripts
```

The GitHub Actions workflow also runs the boot/menu theme config check, compiles Python modules, and builds the ESP32 PlatformIO firmware.
