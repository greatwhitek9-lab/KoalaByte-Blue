# Raspberry Pi Hardware and Runtime Setup

The supported Raspberry Pi path is the canonical Pi-only installer:

```bash
cd ~/KoalaByte-Blue
KOALABYTE_SERVICE_USER="$(whoami)" bash one-shot-install.sh
```

It is designed for Raspberry Pi OS Lite. No HDMI display or desktop session is required.

## What the installer configures

- Raspberry Pi system packages
- `pi-companion/.venv` and Python dependencies
- K1-K8 GPIO support
- Stable Heltec and ESP32 USB aliases
- Headless menu/action/display-sync service
- BLE node manager service
- ESP32 voice bridge service
- Hardware doctor service
- External audio selection
- Optional SocketCAN service only when compatible CAN hardware is present

It does not flash the ESP32-S3, Heltec T114, or CAN adapter and does not send CAN frames.

Check without changing the Pi:

```bash
bash one-shot-install.sh --check-only
```

## K1-K8 front-panel board

Use **3.3 V only**. Inputs use the Pi internal pull-ups: idle is HIGH and a pressed key pulls the input LOW.

| Key | Function | BCM GPIO | Pi physical pin |
|---|---|---:|---:|
| K1 | Main menu | 5 | 29 |
| K2 | Previous / back | 6 | 31 |
| K3 | Enter / select | 13 | 33 |
| K4 | Next / forward | 19 | 35 |
| K5 | Up | 26 | 37 |
| K6 | Down | 21 | 40 |
| K7 | Safe power-off request | 20 | 38 |
| K8 | Safe reboot request | 16 | 36 |

Power wiring:

```text
VCC -> Pi 3.3 V, physical pin 1 or 17
GND -> Pi ground, physical pin 39 recommended
```

Never connect the button-board VCC to Pi 5 V.

K7 requires a 2.5-second hold. K8 requires a 3-second hold. Test without executing shutdown or reboot:

```bash
./pi-companion/.venv/bin/python scripts/test_gpio_buttons.py
```

Expected completion marker:

```text
GPIO_ALL_KEYS_PASS
```

Report:

```text
logs/pi_hardware/gpio_button_test.json
```

## Headless runtime

The Pi menu service runs:

```text
scripts/run_headless_menu.py
```

It polls K1-K8, executes the Pi-owned menu actions, and synchronizes menu/action/face state to the ESP32-S3 and T114.

Inspect it with:

```bash
systemctl status koalabyte-menu.service --no-pager -l
journalctl -u koalabyte-menu.service -n 100 --no-pager
cat logs/runtime/headless_menu_status.json
```

## USB discovery

```bash
./pi-companion/.venv/bin/python scripts/discover_koalabyte_ports.py \
  --profile heltec --output-dir logs/preflight

ls -l /dev/koalabyte-* 2>/dev/null || true
```

Expected aliases when connected:

```text
/dev/koalabyte-heltec
/dev/koalabyte-heltec-t114
/dev/koalabyte-esp32-dualeye
```

## Optional SocketCAN adapter

SocketCAN support is optional and non-fatal. When a compatible adapter is present, the setup loads `can`, `can_raw`, `can_dev`, and `gs_usb`, then configures the selected `can*` interface.

```bash
CAN_INTERFACE=can0 CAN_BITRATE=500000 bash scripts/setup_can0.sh
ip -details -statistics link show can0
```

For passive receive-only observation on an authorized, correctly wired bus:

```bash
candump can0
```

Do not use `cansend` during installation or initial validation.

## Hardware doctor

```bash
./pi-companion/.venv/bin/python scripts/pi_hardware_doctor.py \
  --can-interface can0 --gpio-live
```

The doctor inventories the Pi model, OS, service user and groups, K1-K8 states, USB aliases, serial devices, audio devices, Bluetooth, optional SocketCAN state, dependencies, and installed services.

Report:

```text
logs/pi_hardware/pi_hardware_doctor.json
```
