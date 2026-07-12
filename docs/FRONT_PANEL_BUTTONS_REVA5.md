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

## Automatic touch + speech fallback

The button board is no longer allowed to block the firmware install. During the Pi installation, `setup_gpio_buttons.py --check-only` performs a non-interactive GPIO initialization probe when it is running on a Raspberry Pi.

If the K1-K8 GPIO stack cannot initialize:

```text
Installer behavior: continue flashing
Control mode: touch_speech_only
Touchscreen: enabled
KillerKoala speech control: enabled
USB/Bluetooth keyboard: enabled
K1-K8 GPIO buttons: disabled
```

The selected mode is stored at:

```text
logs/control/control_mode.json
```

The boot launcher reads this artifact on every start. In `touch_speech_only` mode, the wrapped jungle UI still starts normally and the GPIO button manager is bypassed.

Only set strict mode when a button failure should stop installation:

```bash
STRICT_GPIO_BUTTONS=1 bash scripts/install_koalabyte_one_shot.sh --heltec-uf2-first
```

Force touch and speech mode manually:

```bash
PYTHONPATH=pi-companion python3 scripts/set_control_mode.py touch_speech_only --reason "button board unavailable"
sudo reboot
```

After repairing the board, probe the GPIO inputs and restore full controls:

```bash
PYTHONPATH=pi-companion python3 scripts/setup_gpio_buttons.py --probe
sudo reboot
```

You can also select full controls manually:

```bash
PYTHONPATH=pi-companion python3 scripts/set_control_mode.py full_controls --reason "button board repaired"
sudo reboot
```

A passive disconnected board with every line sitting HIGH can look identical to a healthy idle board during a non-interactive probe. Use the live test and press every key when you need to verify the actual board and wiring.

## K7 Power On/Off hardware note

A GPIO key cannot start a Pi that has no running power path. Use the battery bank button or add a supported power-control board for true front-panel start behavior. K7 is a safe shutdown request while the Pi is already running.

## K8 Reset / Reboot hardware note

K8 is a software reboot request. Do not wire K8 to raw battery voltage, 5V, ESP32 GPIO, Heltec GPIO, or Raspberry Pi RUN/reset pads unless a separate, documented reset circuit is added later.

## Test

```bash
PYTHONPATH=pi-companion python3 scripts/setup_gpio_buttons.py --check-only
PYTHONPATH=pi-companion python3 scripts/setup_gpio_buttons.py --probe
PYTHONPATH=pi-companion python3 scripts/setup_gpio_buttons.py --live-test --seconds 20
PYTHONPATH=pi-companion python3 scripts/set_control_mode.py --show
python3 scripts/test_gpio_buttons.py
```

Press K1 through K8 left-to-right and confirm the output matches the table.
