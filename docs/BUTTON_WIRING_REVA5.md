# RevA5 Button Wiring Guide

## Parts

- 4x 6mm tactile pushbuttons from Adafruit Product ID 367.
- 26-28 AWG stranded hookup wire.
- Heat-shrink or JST/Dupont leads for strain relief.
- Shared ground bus to Raspberry Pi GND.

## Wiring table

| Button | Pi BCM GPIO | Physical pin | Wire color suggestion |
|---|---:|---:|---|
| Back | GPIO5 | 29 | White |
| Select | GPIO6 | 31 | Blue |
| Next | GPIO13 | 33 | Green |
| Menu | GPIO19 | 35 | Yellow |
| Shared GND | GND | 39 | Black |

## Electrical behavior

The firmware uses internal pull-up mode:

- Idle button: reads HIGH.
- Pressed button: shorts GPIO to GND, reads LOW.

This keeps the wiring simple and avoids extra resistors.

## Harness routing

Route the four signal wires and one ground wire along the right interior wall of the case. Add strain relief before the harness reaches the Pi GPIO header so button pulls do not stress the header pins.
