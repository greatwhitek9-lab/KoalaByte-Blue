# KoalaByte Blue Flashing and Installation Guide - Heltec T114 Edition

This branch is the **KoalaByte Blue v2 Heltec Edition**. It targets the **Heltec Mesh Node T114 v2 onboard nRF52840** plus the Raspberry Pi 3B+, ESP32-S3 DualEye display, InnoMaker USB-CAN adapter, and companion software.

It does **not** use the separate Nordic nRF52840 USB Dongle lab firmware path.

Current component set:

1. **ESP32-S3 DualEye firmware** under `firmware/esp32-dualeye/`.
2. **Heltec T114 mouth/BLE/GNSS firmware** under `firmware/heltec-mouth/`.
3. **Optional Heltec T114 Koala Konnect USB-HCI profile** built for the T114 onboard nRF52840, not the Nordic USB Dongle.
4. **Raspberry Pi 3B+ companion tools** under `pi-companion/` and `scripts/`.
5. **Koala Kan Kommander support for the InnoMaker USB to CAN Converter kit** through the Pi companion.
6. **Greatwhite Wireshark/tshark wrapper** for owned-lab packet review.

Readiness keywords: `koalabyte_blue_v2_heltec_edition`, `Heltec Mesh Node T114 v2`, `KOALABYTE_HELTEC_USB_PORT`, `flash_all_components.sh`, `InnoMaker USB to CAN Converter kit`.

Safety boundary: this code is for authorized Bluetooth research, BLE inventory, local logging, AI companion behavior, scoped CAN observation, completely isolated CAN bench simulator testing, packet-review readiness checks, and safe lab validation only. Koala Kry remains offline metadata replay/RF bench review only. Koala Kan Kommander transmit requires both `--bench-simulator` and `--confirm-transmit`.

---

## Fast path: one helper for all Heltec Edition components

From the repo root, run the readiness check first:

```bash
python3 scripts/check_repo_readiness.py
```

Run the all-component helper:

```bash
bash scripts/flash_all_components.sh --all
```

Useful variants:

```bash
bash scripts/flash_all_components.sh --pi
ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --heltec-t114
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_all_components.sh --nrf-konnect
bash scripts/flash_all_components.sh --greatwhite
bash scripts/flash_all_components.sh --all --build-only
bash scripts/flash_all_components.sh --all --smoke
```

The helper runs the repo readiness check, installs the Pi companion when requested, flashes ESP32 when requested, flashes the normal Heltec mouth/BLE/GNSS firmware when requested, optionally builds/flashes the Heltec T114 Koala Konnect USB-HCI profile, and writes Koala Kan Kommander manifest/inventory/status checks for the InnoMaker USB-CAN adapter.

The same flow installs KillerKoala voice/TTS support through `scripts/setup_system_packages.sh` when system packages are enabled. Raspberry Pi OS installs `espeak-ng`, `espeak`, ALSA utilities/plugins, PulseAudio CLI utilities, PortAudio, and `python3-pyaudio`.

Enable spoken Boomerang/KillerKoala alerts after installation with:

```bash
KOALABYTE_TTS=1 PYTHONPATH=pi-companion python3 scripts/run_boomerang.py
```

---

## Heltec T114 firmware rule

Use the **Heltec T114 onboard nRF52840** for this branch.

Do not use this old dongle-only path on `koalabyte_blue_v2_heltec_edition`:

```text
firmware/nrf52840-dongle-ear-tag-tx-lab/
```

Do not use this old dongle board target for this branch:

```text
nrf52840dongle_nrf52840
```

Use the Heltec T114 target instead:

```text
heltec_t114_v2/nrf52840
```

---

## Heltec T114 mouth / BLE / GNSS firmware

This is the normal Heltec firmware for the KoalaByte Blue v2 Heltec Edition.

Requirements:

- Heltec Mesh Node T114 v2 connected over a USB-C **data** cable.
- PlatformIO available for the Arduino/PlatformIO firmware path.
- `KOALABYTE_HELTEC_USB_PORT` set when auto-discovery does not find the board.

Flash normal Heltec firmware:

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 bash scripts/flash_heltec_mouth.sh
```

Run through the all-component wrapper:

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --heltec-t114
```

Manual build:

```bash
cd firmware/heltec-mouth
pio run
```

Manual upload:

```bash
cd firmware/heltec-mouth
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 pio run -t upload --upload-port "$KOALABYTE_HELTEC_USB_PORT"
```

Expected behavior:

- T114 color TFT mouth/snout UI initializes.
- BLE observation status messages are available to the Pi companion.
- L76K GNSS serial path is initialized when enabled.
- USB CDC remains the Pi-to-T114 control path.

---

## Optional Heltec T114 Koala Konnect USB-HCI profile

Koala Konnect is an alternate firmware profile for the **T114 onboard nRF52840**. It exposes a USB Bluetooth HCI controller to the Pi for BlueZ-based local lab checks.

Important: flashing this profile replaces the normal Heltec mouth/BLE/GNSS firmware until you flash `firmware/heltec-mouth/` back onto the T114.

Build only:

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/build_koala_konnect_t114.sh
```

Build through the all-component wrapper:

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_all_components.sh --nrf-konnect --build-only
```

Flash Koala Konnect to the T114:

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_koala_konnect_t114.sh
```

Flash through the all-component wrapper:

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_all_components.sh --nrf-konnect
```

Return to normal Heltec mouth/BLE/GNSS mode:

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 bash scripts/flash_heltec_mouth.sh
```

---

## T114 BlueZ wrapper checks

When the T114 is running the optional USB-HCI Koala Konnect profile, use the local BlueZ wrapper to verify readiness.

Controller check:

```bash
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py controller-check
```

Safe local wrapper check:

```bash
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py all-safe
```

These checks do not implement pairing bypasses, unauthorized access, or offensive workflows.

---

## Raspberry Pi 3B+ companion install

Recommended Raspberry Pi OS packages:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip bluetooth bluez rfkill sqlite3 libsdl2-2.0-0 iproute2 can-utils tshark wireshark-common unzip espeak-ng espeak alsa-utils libasound2-plugins pulseaudio-utils portaudio19-dev python3-pyaudio
```

Install/update the companion environment:

```bash
git clone https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
git checkout koalabyte_blue_v2_heltec_edition
bash scripts/install_pi.sh
```

Safe local tests:

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py controller-check
PYTHONPATH=pi-companion python3 scripts/run_meshtastic_app.py status
PYTHONPATH=pi-companion python3 scripts/run_gw.py status
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py status
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py status --xp 100
KOALABYTE_TTS=1 PYTHONPATH=pi-companion python3 scripts/run_boomerang.py
```

---

## ESP32-S3 DualEye firmware

Install PlatformIO:

```bash
python3 -m pip install --user platformio
pio --version
```

Build and flash:

```bash
ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32
```

Manual build:

```bash
cd firmware/esp32-dualeye
pio run
```

Manual upload:

```bash
cd firmware/esp32-dualeye
ESP32_PORT=/dev/ttyUSB0 pio run -t upload --upload-port "$ESP32_PORT"
```

Expected serial boot JSON includes:

```json
{"type":"boot","device":"esp32-dualeye","companion":"killerkoala","wake_word":"killerkoala","boot_animation":1}
```

---

## Greatwhite Wireshark / tshark support

Greatwhite is a bounded packet-review helper for owned lab interfaces.

Check host tooling status:

```bash
PYTHONPATH=pi-companion python3 scripts/run_gw.py status
```

List local interfaces before capture:

```bash
PYTHONPATH=pi-companion python3 scripts/run_gw.py interfaces
```

Optional nRF Sniffer host-side check:

```bash
bash scripts/setup_nrf_sniffer_ble.sh --check-only
```

Greatwhite does not transmit packets. Capture actions require explicit interface selection and owned-lab confirmation.

---

## CAN bench support

Set up CAN only for an isolated bench adapter/simulator harness:

```bash
CAN_INTERFACE=can0 CAN_BITRATE=500000 bash scripts/flash_all_components.sh --can-check
```

Koala Kan Kommander transmit remains gated and requires a bench simulator confirmation.
