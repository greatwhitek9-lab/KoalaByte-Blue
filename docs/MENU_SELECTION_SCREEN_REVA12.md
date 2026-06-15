# RevA12 Menu Selection Screen

## Purpose

The RevA12 menu screen gives KoalaByte Blue one shared navigation model for:

- The six front-panel GPIO buttons.
- Touchscreen scrolling.
- Touchscreen long-press select.
- Terminal validation during development.

## Default menu

```text
eucalyptus
Koala Kapture
Koala Kry
Ear Tag
Urban Poaching
Reports
Settings
Lab
Shutdown
```

## Button mapping

```text
Button 1 = Main Menu
Button 2 = Move Left / Back
Button 3 = Enter / Select
Button 3 hold = Shutdown confirmation path
Button 4 = Move Right / Forward
Button 5 = Up
Button 6 = Down
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
a = left/back
d = right/forward
Enter = select
m = main menu
q = quit
```

GPIO buttons are enabled automatically when `gpiozero` is available and the script is running on the Pi.

## Implementation files

```text
pi-companion/koalablue/menu_ui.py
scripts/run_menu_screen.py
```
