<p align="center">
  <img src="assets/code-signature/koalabyte-code-signature.svg" alt="KoalaByte Blue code signature" width="760">
</p>

# KoalaByte Blue

KoalaByte Blue is a Raspberry Pi 3B+-coordinated cyberpet and owned-device lab platform. The current runtime combines:

- Raspberry Pi OS Lite as the headless coordinator, action executor, menu state machine, voice/AI host, BLE node, Wi-Fi host, logging host, and report host.
- Waveshare ESP32-S3 DualEye as the animated cyberpunk koala eyes, local wake-word/menu interface, microphone endpoint, and Pi Wi-Fi node.
- Heltec T114 as the articulated Koalagotchi mouth, BLE controller, GNSS node, and LoRa/Meshtastic node.
- An eight-key K1-K8 GPIO board for physical menu and system controls.
- Optional external audio and an optional stock-firmware SocketCAN adapter.

Use the project only with devices, networks, radios, captures, vehicles, and test benches you own or are authorized to assess. The installer does not transmit RF, BLE, or CAN traffic.

## Current runtime contract

The Raspberry Pi owns:

- Headless K1-K8 menu navigation and action execution
- Menu and status synchronization to the ESP32-S3 and T114
- BLE coordination with the T114
- ESP32 voice-command escalation and Pi-side STT/AI execution
- Australian male William TTS output while preserving the spoken identity **KillerKoala**
- Koalagotchi health, mood, action, completion, and error-state fanout
- Runtime services, stable USB aliases, logging, diagnostics, and reports

The installer preserves all peripheral firmware. Firmware is developed and validated from the source trees under `firmware/`; it is not bundled into or flashed by the Pi installer.

## Canonical installation

There is one supported installer entrypoint:

```bash
cd ~/KoalaByte-Blue
KOALABYTE_SERVICE_USER="$(whoami)" bash one-shot-install.sh
```

For a clean Raspberry Pi without a repository checkout:

```bash
curl -fsSL -o koalabyte-install.sh \
  https://raw.githubusercontent.com/greatwhitek9-lab/KoalaByte-Blue/Main/install.sh
bash koalabyte-install.sh
```

Validate without changing the host:

```bash
bash one-shot-install.sh --check-only
```

Useful options:

```bash
bash one-shot-install.sh --skip-packages
bash one-shot-install.sh --skip-audio
bash one-shot-install.sh --skip-can
```

The installer configures:

- Required Raspberry Pi OS packages
- `pi-companion/.venv`
- Hardware groups for the service user
- Stable Heltec and ESP32 USB aliases
- Headless menu/K1-K8 service
- Menu display synchronization service
- BLE node manager service
- ESP32 voice bridge service
- Hardware doctor service
- External audio selection
- Optional SocketCAN service only when compatible hardware is present

It does **not** flash the ESP32-S3, T114, or InnoMaker and does not send CAN frames.

## Raspberry Pi OS Lite runtime

The Pi does not require HDMI, a desktop environment, or a local graphical session. The boot service runs:

```text
scripts/run_headless_menu.py
```

Service status:

```bash
systemctl status koalabyte-menu.service --no-pager -l
systemctl status koalabyte-menu-sync.service --no-pager -l
systemctl status koalabyte-ble-node-manager.service --no-pager -l
systemctl status koalabyte-dualeye-voice-bridge.service --no-pager -l
```

Runtime status files:

```text
logs/runtime/headless_menu_status.json
logs/preflight/koalabyte_ports.json
logs/gpio_buttons/gpio_button_status.json
logs/pi_hardware/pi_hardware_doctor.json
```

## K1-K8 button board

Use **3.3 V only**. Inputs use the Pi internal pull-ups: idle is HIGH and pressed is LOW.

| Key | Function | BCM | Physical pin |
|---|---|---:|---:|
| K1 | Main menu | 5 | 29 |
| K2 | Left / back | 6 | 31 |
| K3 | Select | 13 | 33 |
| K4 | Right / forward | 19 | 35 |
| K5 | Up | 26 | 37 |
| K6 | Down | 21 | 40 |
| K7 | Power on/off request | 20 | 38 |
| K8 | Reset/reboot request | 16 | 36 |

Power wiring:

```text
VCC -> Pi 3.3 V, physical pin 1 or 17
GND -> Pi ground, physical pin 39 recommended
```

K7 requires a deliberate 2.5-second hold. K8 requires a deliberate 3-second hold. The non-destructive wiring test is:

```bash
cd ~/KoalaByte-Blue
./pi-companion/.venv/bin/python scripts/test_gpio_buttons.py
```

## Device discovery

```bash
cd ~/KoalaByte-Blue
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

Run the hardware inventory:

```bash
./pi-companion/.venv/bin/python scripts/pi_hardware_doctor.py \
  --can-interface can0 --gpio-live
```

## Firmware policy

The working peripheral firmware is preserved by default:

- ESP32-S3 DualEye: current static-grammar wake/menu/response runtime
- Heltec T114: current original-texture articulated mouth and latched Koalagotchi lifecycle
- InnoMaker or other SocketCAN adapter: stock adapter firmware only

Firmware source remains under:

```text
firmware/esp32-dualeye/
firmware/t114-combined-safe/
```

Firmware builds and physical flashing are separate development/recovery operations. They are not part of `install.sh` or `one-shot-install.sh`.

## Validation

Repository and installer checks:

```bash
python3 scripts/check_repo_readiness.py
PYTHONPATH=pi-companion python3 scripts/check_one_shot_controls.py
bash scripts/check_deployability.sh
bash one-shot-install.sh --check-only
```

The CI contract verifies the headless Pi runtime, K1-K8 protection, menu/action catalog, voice/AI dependencies, display synchronization, USB rules, and no-flash installer policy.
