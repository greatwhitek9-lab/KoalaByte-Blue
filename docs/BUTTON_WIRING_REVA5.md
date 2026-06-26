# RevA6 Six-Button Wiring Guide

## Parts

- 6x 6mm tactile pushbuttons from Adafruit Product ID 367 or equivalent 6x6x5mm 4-pin momentary tactile switches.
- 40-pin Raspberry Pi GPIO extender / ribbon harness.
- 26-28 AWG stranded hookup wire.
- Heat-shrink, JST, Dupont, or soldered strain relief.
- Shared ground bus to Raspberry Pi GND.

## Physical layout

Number the buttons **1 through 6 from left to right** across the front panel.

```text
[1 Main Menu] [2 Left/Back] [3 Enter/Select] [4 Right/Forward] [5 Up] [6 Down]
```

## How the 4-pin tactile button legs work

A 4-pin tactile button has two internally connected pairs of legs. The two legs on one side are already connected together, and the two legs on the opposite side are already connected together.

```text
Top view of switch legs:

[ A ]     [ B ]

[ A ]     [ B ]
```

When the button is pressed, side **A** connects to side **B**.

For each button:

```text
GPIO signal wire -> one leg on side A
GND wire         -> one leg on side B
```

Do **not** solder the GPIO and GND wires to two legs on the same side of the switch, because that side is already internally common.

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

The Pi software enables the Raspberry Pi internal pull-up resistor with `gpiozero.Button(..., pull_up=True)`.

```text
Not pressed / idle = HIGH
Pressed            = LOW
```

Each button is a normally-open switch that shorts the assigned GPIO pin to GND only while pressed. This keeps the wiring simple and avoids extra resistors.

## 40-pin GPIO extender wiring pattern

Use one GPIO signal wire per button plus one shared ground bus.

```text
Physical pin 29 / GPIO5  -> F1 signal
Physical pin 31 / GPIO6  -> F2 signal
Physical pin 33 / GPIO13 -> F3 signal
Physical pin 35 / GPIO19 -> F4 signal
Physical pin 37 / GPIO26 -> F5 signal
Physical pin 40 / GPIO21 -> F6 signal
Physical pin 39 / GND    -> common ground bus
```

Button circuit pattern:

```text
GPIO5  -> F1 -> GND
GPIO6  -> F2 -> GND
GPIO13 -> F3 -> GND
GPIO19 -> F4 -> GND
GPIO26 -> F5 -> GND
GPIO21 -> F6 -> GND
```

## Harness routing

Route the six signal wires and one ground wire along the right interior wall of the case. Add strain relief before the harness reaches the Pi GPIO header so button pulls do not stress the header pins.

Use a small perfboard or button carrier board if possible. Direct soldering to the tactile switch legs works, but a small board is stronger and easier to service.

## Validation

Run:

```bash
python3 scripts/test_gpio_buttons.py
```

Press each button left-to-right and confirm the event output matches button numbers 1 through 6. Hold button 3 for 3 seconds and confirm it prints a `shutdown` hold event.
