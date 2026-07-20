# RevA7 / RevA25 8-Key Button Board Wiring Guide

## Parts

- 1x GODIYMODULES MOD-ST034-1 / ASIN B0FH9C88DJ 8 independent key button module with header pins `VCC`, `GND`, and `K1` through `K8`.
- 40-pin Raspberry Pi GPIO extender / ribbon harness.
- Female-to-female Dupont jumpers or a keyed harness.

The Amazon listing includes two modules. KoalaByte Blue only uses one module.

## Physical layout

Number the keys **K1 through K8 from left to right** across the front panel.

```text
[K1 Main Menu] [K2 Left/Back] [K3 Enter/Select] [K4 Right/Forward] [K5 Up] [K6 Down] [K7 Safe Shutdown] [K8 Reset / Reboot]
```

## Voltage rule

Use **3.3V only** for the module VCC when its K outputs connect to Raspberry Pi GPIO.

```text
Module VCC -> Pi 3.3V, physical pin 1 or 17
Module GND -> Pi GND, physical pin 39 or any Pi GND
```

Do not power this button module from Pi 5V unless the exact board is level-shifted and verified safe for 3.3V GPIO inputs. For this build, use Pi 3.3V only.

## Default wiring table

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
| K7 | Safe Shutdown | GPIO20 | 38 | Gray |
| K8 | Reset / Reboot | GPIO16 | 36 | Brown |

## Electrical behavior

The module is active-low.

```text
Not pressed / idle = HIGH
Pressed            = LOW
```

The board has pull-up behavior, and the Pi software also enables the Raspberry Pi internal pull-up resistor with `gpiozero.Button(..., pull_up=True)`.

## Default header wiring pattern

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

## K7 Safe Shutdown — default production wiring

The supported default is **K7 -> GPIO20 / physical pin 38**.

- A short press has no runtime action.
- Holding K7 for 2.5 seconds requests an orderly `sudo shutdown -h now`.
- Applying power to the Raspberry Pi starts it automatically.
- Once the Pi is halted but still powered, K7 on GPIO20 cannot wake it. Restart by cycling the external supply or using its power control.

## Optional K7 wake-from-halt / true on-off-style wiring

This is an optional alternate configuration, not the default production wiring.

To let the same K7 key request safe shutdown while Linux is running and wake a halted Raspberry Pi while external power remains connected:

1. Move the K7 signal wire from **GPIO20 / physical pin 38** to **GPIO3 / physical pin 5**.
2. Keep the button module ground connected to Pi ground.
3. Change the configured K7 BCM pin from `20` to `3` in `pi-companion/koalablue/gpio_buttons.py` and in the GPIO hardware-test mapping before installing the runtime.
4. Keep the existing 2.5-second software hold requirement for shutdown while Linux is running.

Behavior with this option:

- While Linux is running, hold K7 for 2.5 seconds for safe shutdown.
- While the Pi is halted but still receiving external power, pressing K7 pulls GPIO3 low and wakes the Pi.
- If external power is removed completely, K7 cannot start the Pi; restoring power starts it automatically.

Important constraints:

- GPIO3 / physical pin 5 is also the default I2C SCL pin. Do not use this option if another installed device needs that I2C clock line unless the complete bus design has been validated.
- Do not connect K7 to 5V, raw battery voltage, ESP32 GPIO, Heltec GPIO, or the Pi RUN/reset pads.
- The software pin configuration must match the physical K7 wire. Moving only the wire without changing the configured BCM pin leaves the runtime listening on GPIO20.

## K8 Reset / Reboot note

K8 requests a safe software reboot of the Raspberry Pi. It is not a hard reset line and should not be wired to power, reset pads, RUN pads, raw battery voltage, ESP32 GPIO, or Heltec GPIO.

## Validation

Run:

```bash
PYTHONPATH=pi-companion python3 scripts/setup_gpio_buttons.py --check-only
PYTHONPATH=pi-companion python3 scripts/setup_gpio_buttons.py --live-test --seconds 20
python3 scripts/test_gpio_buttons.py
```

Press K1 through K8 left-to-right and confirm the event output matches the selected wiring configuration.