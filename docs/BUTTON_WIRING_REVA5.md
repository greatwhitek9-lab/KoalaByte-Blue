# RevA6 Six-Button Wiring Guide

## Parts

- 6x 6mm tactile pushbuttons from Adafruit Product ID 367.
- 26-28 AWG stranded hookup wire.
- Heat-shrink or JST/Dupont leads for strain relief.
- Shared ground bus to Raspberry Pi GND.

## Physical layout

Number the buttons **1 through 6 from left to right** across the front panel.

```text
[1 Main Menu] [2 Left/Back] [3 Enter/Select] [4 Right/Forward] [5 Up] [6 Down]
```

## Wiring table

| Button # | Button label | Pi BCM GPIO | Physical pin | Wire color suggestion |
|---:|---|---:|---:|---|
| 1 | Main Menu | GPIO5 | 29 | White |
| 2 | Move Left / Back | GPIO6 | 31 | Blue |
| 3 | Enter / Select / hold Shutdown | GPIO13 | 33 | Green |
| 4 | Move Right / Forward | GPIO19 | 35 | Yellow |
| 5 | Up | GPIO26 | 37 | Orange |
| 6 | Down | GPIO21 | 40 | Purple |
| Shared GND | Ground bus | GND | 39 | Black |

## Electrical behavior

The firmware uses internal pull-up mode:

- Idle button: reads HIGH.
- Pressed button: shorts GPIO to GND, reads LOW.

This keeps the wiring simple and avoids extra resistors.

## Harness routing

Route the six signal wires and one ground wire along the right interior wall of the case. Add strain relief before the harness reaches the Pi GPIO header so button pulls do not stress the header pins.

## Validation

Run:

```bash
python3 scripts/test_gpio_buttons.py
```

Press each button left-to-right and confirm the event output matches button numbers 1 through 6. Hold button 3 for 3 seconds and confirm it prints a `shutdown` hold event.
