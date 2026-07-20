# Raspberry Pi Hardware Stage

This stage prepares and validates the Raspberry Pi without reflashing the ESP32-S3 DualEye or Heltec T114 and without running the final one-shot installer.

## K1-K8 front-panel board

Use **3.3 V only**. The GPIO inputs use Pi internal pull-ups: idle is HIGH and a pressed key pulls the assigned input LOW.

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

Board power:

- `VCC` -> Pi 3.3 V, physical pin 1 or 17
- `GND` -> Pi ground, physical pin 39 recommended
- Never connect the button board VCC to Pi 5 V.

K7 and K8 are protected in the runtime. K7 must be held for 2.5 seconds and K8 must be held for 3 seconds before their commands are emitted. The hardware test script never shuts down or reboots the Pi.

## InnoMaker USB-to-CAN

The adapter is used through Linux SocketCAN. The setup loads `can`, `can_raw`, `can_dev`, and `gs_usb`, waits for a `can*` network interface, sets the requested bitrate, enables automatic bus-off recovery, and installs a systemd/udev hot-plug path.

Default interface and bitrate:

```bash
CAN_INTERFACE=can0
CAN_BITRATE=500000
```

CAN wiring for an authorized bench or vehicle connection:

- `CAN_H` -> CAN high
- `CAN_L` -> CAN low
- `GND` -> common signal ground
- Connect shield only when the installation design calls for it.
- Do not add termination blindly. A normal two-ended CAN bus should measure about 60 ohms between CAN_H and CAN_L with power removed.

The setup stage does not transmit CAN frames.

## Stage installation

From the repository root on the Raspberry Pi:

```bash
git pull
bash scripts/setup_pi_hardware_stage.sh
```

This performs the following:

- installs Raspberry Pi system dependencies
- creates or updates `pi-companion/.venv`
- installs Python requirements
- adds the service user to available hardware groups such as `gpio`, `dialout`, `audio`, `video`, `render`, and `plugdev`
- installs stable KoalaByte USB rules
- installs the InnoMaker SocketCAN service and `can*` hot-plug rule
- checks/selects the external audio output
- produces `logs/pi_hardware/pi_hardware_doctor.json`

It does **not** enable the complete KoalaByte runtime services unless explicitly requested:

```bash
bash scripts/setup_pi_hardware_stage.sh --install-runtime-services
```

## Validate the buttons

After rebooting or logging out and back in so the new group memberships apply:

```bash
pi-companion/.venv/bin/python scripts/test_gpio_buttons.py
```

Press and release K1 through K8 once. Expected result:

```text
GPIO_ALL_KEYS_PASS
```

Report:

```text
logs/pi_hardware/gpio_button_test.json
```

## Validate InnoMaker

Plug in the adapter, then run:

```bash
CAN_INTERFACE=can0 CAN_BITRATE=500000 bash scripts/setup_can0.sh
ip -details -statistics link show can0
```

For a passive receive test on an authorized, correctly wired bus:

```bash
candump can0
```

Stop with `Ctrl+C`. `candump` listens only; it does not send frames.

## Run the Pi doctor

```bash
pi-companion/.venv/bin/python scripts/pi_hardware_doctor.py --can-interface can0 --gpio-live
```

The report inventories:

- Raspberry Pi model, OS, user, and hardware groups
- K1-K8 pin availability and current electrical states
- InnoMaker USB/SocketCAN state and kernel modules
- ALSA/PipeWire/PulseAudio playback and capture devices
- ESP32 and Heltec stable serial aliases
- Python modules, host commands, and KoalaByte systemd services

Report:

```text
logs/pi_hardware/pi_hardware_doctor.json
```

Paste that report when a hardware item is missing or not ready; it is designed to identify the exact next correction without rerunning firmware flashing.
