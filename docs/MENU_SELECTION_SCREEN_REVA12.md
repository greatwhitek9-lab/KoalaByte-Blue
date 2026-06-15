# RevA12 Menu Selection Screen / RevA14 Jungle Theme Update

## Purpose

The menu screen gives KoalaByte Blue one shared navigation model for six front-panel GPIO buttons, touchscreen scrolling, touchscreen long-press selection, keyboard validation, and the RevA14 large bubbly jungle/eucalyptus graphical menu.

## Shared full-function catalog

Both menu implementations use the same catalog:

```text
pi-companion/koalablue/menu_catalog.py
```

The catalog includes the available Pi companion commands, eucalyptus controls, capture/replay actions, lab report/checklist actions, settings, shutdown, and quit.

## Default menu

```text
01 Scan
02 Summary
03 Show Devices
04 eucalyptus Status
05 eucalyptus Start
06 eucalyptus Stop
07 eucalyptus Restart
08 eucalyptus Upload Status
09 Koala Kapture
10 Koala Kry
11 Ear Tag
12 Urban Poaching
13 Buttons
14 Level / Status
15 Report
16 Wake killerkoala
17 Authorized BLE Inventory
18 GATT Readiness Checklist
19 Pairing Security Review
20 Lab Beacon Plan
21 Packet Capture Notes
22 Defensive Lab Report
23 Restricted Placeholder [locked]
24 Settings
25 Lab
26 Shutdown
27 Quit
```

## RevA14 visual layer

The RevA14 renderer adds large rounded bubbly menu text, eucalyptus branch borders, leaf accents on selected rows, rounded pill menu rows, touch scrolling, and long-press selection.

Implementation files:

```text
pi-companion/koalablue/menu_theme.py
firmware/esp32-dualeye/include/menu_theme.h
firmware/esp32-dualeye/src/menu_theme.cpp
```

## Button mapping

```text
Button 1 = Main Menu
Button 2 = Move Left / Back / Previous item
Button 3 = Enter / Select
Button 3 hold = Shutdown confirmation path
Button 4 = Move Right / Forward / Next item
Button 5 = Up / Previous item
Button 6 = Down / Next item
```

## Touch behavior

```text
Drag / swipe vertically = scroll menu
Tap row = move selection to row
Long press row = select row
```

Default touch tuning for the themed menu:

```text
row_height_px = 64
scroll_threshold_px = 18
long_press_seconds = 0.75
```

## Validation runner

Terminal validation:

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py
```

Graphical jungle/eucalyptus menu:

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
```

Keyboard test controls:

```text
w = up
s = down
a = left/back/previous
d = right/forward/next
Enter = select
m = main menu
q = quit
```

GPIO buttons are enabled automatically when `gpiozero` is available and the script is running on the Pi.

## Implementation files

```text
pi-companion/koalablue/menu_catalog.py
pi-companion/koalablue/menu_ui.py
pi-companion/koalablue/menu_screen.py
pi-companion/koalablue/menu_theme.py
scripts/run_menu_screen.py
firmware/esp32-dualeye/include/menu_theme.h
firmware/esp32-dualeye/src/menu_theme.cpp
```
