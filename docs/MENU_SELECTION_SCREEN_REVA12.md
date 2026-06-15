# RevA12 Menu Selection Screen

## Purpose

The RevA12 menu screen gives KoalaByte Blue one shared navigation model for:

- The six front-panel GPIO buttons.
- Touchscreen scrolling.
- Touchscreen long-press select.
- Terminal validation during development.

## Shared full-function catalog

Both menu implementations now use the same catalog:

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

The menu state machine consumes the existing command names from `gpio_buttons.py`:

```text
main_menu
move_left
select
shutdown
move_right
up
down
```

## Touch behavior

```text
Drag / swipe vertically = scroll menu
Tap row = move selection to row
Long press row = select row
```

Default touch tuning:

```text
row_height_px = 48
scroll_threshold_px = 18
long_press_seconds = 0.75
```

## Validation runner

Run a terminal validation menu on the Pi:

```bash
cd pi-companion
source .venv/bin/activate
PYTHONPATH=. python ../scripts/run_menu_screen.py
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
scripts/run_menu_screen.py
```
