# RevA7 / RevA25 8-Key Button Board Wiring Guide

## Parts

- 1x GODIYMODULES MOD-ST034-1 / ASIN B0FH9C88DJ 8 independent key button module with header pins `VCC`, `GND`, and `K1` through `K8`.
- 40-pin Raspberry Pi GPIO extender / ribbon harness.
- Female-to-female Dupont jumpers or a keyed harness.

The Amazon listing includes two modules. KoalaByte Blue only uses one module.

## Physical layout

Number the keys **K1 through K8 from left to right** across the front panel.

```text
[K1 Main Menu] [K2 Left/Back] [K3 Enter/Select] [K4 Right/Forward] [K5 Up] [K6 Down] [K7 Power On/Off] [K8 Reset / Reboot]
```

## Voltage rule

Use **3.3V only** for the module VCC when its K outputs connect to Raspberry Pi GPIO.

```text
Module VCC -> Pi 3.3V, physical pin 1 or 17
Module GND -> Pi GND, physical pin 39 or any Pi GND
```

Do not power this button module from Pi 5V unless the exact board is level-shifted and verified safe for 3.3V GPIO inputs. For this build, use Pi 3.3V only.

## Wiring table

| Module pin | Button label | Pi BCM GPIO | Pi physical pin | Wire color suggestion |
|---|---|---:|---:|---|
| VCC | 3.3V supply | 3.3V | 1 or 17 | Red |
| GND | Ground | GND | 39 or any GND | Black |
| K1 | Main Menu | GPIO5 | 29 | White |
| K2 | Move Left / Back | GPIO6 | 31 | Blue |
| K3 | Enter / Select | GPIO13 | 33 | Green |
| K4 | Move Right / Forward | GPIO19 | 35 | Yellow |
| K5 | Up | GPIO26 | 37 | Orange |
| K6 | Down | GPIO21 | 40 | Purple |
| K7 | Power On/Off | GPIO20 | 38 | Gray |
| K8 | Reset / Reboot | GPIO16 | 36 | Brown |

## Electrical behavior

The module is active-low.

```text
Not pressed / idle = HIGH
Pressed            = LOW
```

The board has pull-up behavior, and the Pi software also enables the Raspberry Pi internal pull-up resistor with `gpiozero.Button(..., pull_up=True)`.

## Header wiring pattern

```text
Pi pin 1 or 17 / 3.3V -> module VCC
Pi pin 39 / GND       -> module GND
Pi pin 29 / GPIO5     -> K1
Pi pin 31 / GPIO6     -> K2
Pi pin 33 / GPIO13    -> K3
Pi pin 35 / GPIO19    -> K4
Pi pin 37 / GPIO26    -> K5
Pi pin 40 / GPIO21    -> K6
Pi pin 38 / GPIO20    -> K7
Pi pin 36 / GPIO16    -> K8
```

## K7 Power On/Off note

K7 can request a clean runtime shutdown while the Pi is already running. Starting a fully unpowered Pi from the same front-panel key needs separate approved power-control hardware or the battery bank control.

## K8 Reset / Reboot note

K8 requests a safe software reboot of the Raspberry Pi. It is not a hard reset line and should not be wired to power, reset pads, RUN pads, raw battery voltage, ESP32 GPIO, or Heltec GPIO.

## Validation

Run:

```bash
PYTHONPATH=pi-companion python3 scripts/setup_gpio_buttons.py --check-only
PYTHONPATH=pi-companion python3 scripts/setup_gpio_buttons.py --live-test --seconds 20
python3 scripts/test_gpio_buttons.py
```

Press K1 through K8 left-to-right and confirm the event output matches the wiring table.
