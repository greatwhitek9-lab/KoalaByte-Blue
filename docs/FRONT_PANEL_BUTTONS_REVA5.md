# RevA7 Front Panel Button Mapping

## Button board

KoalaByte Blue now uses an **8 independent key button module** instead of six individual 4-pin tactile buttons.

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
| K7 | PWR | PWR control position | GPIO20 | Pin 38 |
| K8 | Reset | reset position | GPIO16 | Pin 36 |

## Wiring rule

```text
Module VCC -> Pi 3.3V, pin 1 or 17
Module GND -> Pi GND, pin 39 or any Pi GND
Module K1-K8 -> the GPIO pins in the table above
```

No external pull-up resistor is required. The Raspberry Pi internal pull-up is enabled by `gpiozero` in software.

```text
Idle / not pressed = HIGH
Pressed            = LOW
```

## PWR hardware note

A GPIO key cannot start a Pi that has no running power path. Use the battery bank button or add a supported power-control board for true front-panel start behavior.

## Test

```bash
PYTHONPATH=pi-companion python3 scripts/setup_gpio_buttons.py --check-only
PYTHONPATH=pi-companion python3 scripts/setup_gpio_buttons.py --live-test --seconds 20
```

Press K1 through K8 left-to-right and confirm the output matches the table.
