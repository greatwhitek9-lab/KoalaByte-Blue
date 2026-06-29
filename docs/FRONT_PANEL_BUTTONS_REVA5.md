# RevA7 / RevA25 Front Panel Button Mapping

## Button board

KoalaByte Blue now uses an **8 independent key button module** instead of six individual 4-pin tactile buttons.

Current orderable board reference:

```text
GODIYMODULES 2PCS 8 Independent Key Button Touch Button Module
Model / part: MOD-ST034-1
ASIN: B0FH9C88DJ
```

The module header is treated as:

```text
VCC  GND  K1  K2  K3  K4  K5  K6  K7  K8
```

Use Pi **3.3V** for VCC and Pi GND for ground.

## 8-key map, left to right

| Module key | Front-panel label | Action | Raspberry Pi BCM GPIO | Physical pin |
|---|---|---|---:|---:|
| K1 | Main Menu | `main_menu` | GPIO5 | Pin 29 |
| K2 | Left / Back | `move_left` / `back` | GPIO6 | Pin 31 |
| K3 | Enter / Select | `select` | GPIO13 | Pin 33 |
| K4 | Right / Forward | `move_right` / `forward` | GPIO19 | Pin 35 |
| K5 | Up | `up` | GPIO26 | Pin 37 |
| K6 | Down | `down` | GPIO21 | Pin 40 |
| K7 | Power On/Off | `power_toggle` -> safe shutdown request | GPIO20 | Pin 38 |
| K8 | Reset / Reboot | `reset` -> safe reboot request | GPIO16 | Pin 36 |

## Wiring rule

```text
Module VCC -> Pi 3.3V, pin 1 or 17
Module GND -> Pi GND, pin 39 or any Pi GND
Module K1-K8 -> the GPIO pins in the table above
```

No external pull-up resistor is required. The button board has pull-up behavior, and the Raspberry Pi internal pull-up is enabled by `gpiozero` in software.

```text
Idle / not pressed = HIGH
Pressed            = LOW
```

## K7 Power On/Off hardware note

A GPIO key cannot start a Pi that has no running power path. Use the battery bank button or add a supported power-control board for true front-panel start behavior. K7 is a safe shutdown request while the Pi is already running.

## K8 Reset / Reboot hardware note

K8 is a software reboot request. Do not wire K8 to raw battery voltage, 5V, ESP32 GPIO, Heltec GPIO, or Raspberry Pi RUN/reset pads unless a separate, documented reset circuit is added later.

## Test

```bash
PYTHONPATH=pi-companion python3 scripts/setup_gpio_buttons.py --check-only
PYTHONPATH=pi-companion python3 scripts/setup_gpio_buttons.py --live-test --seconds 20
python3 scripts/test_gpio_buttons.py
```

Press K1 through K8 left-to-right and confirm the output matches the table.
