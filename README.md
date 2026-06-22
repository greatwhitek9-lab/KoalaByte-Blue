# KoalaByte Blue / KillerKoala Heltec T114 Branch

<p align="center">
  <strong>Raspberry Pi host + ESP32-S3 DualEye eyes + Heltec Mesh Node T114 v2 color mouth/GNSS/LoRa/BLE.</strong><br>
  This branch is tuned for the Heltec Mesh Node T114 v2 / HT-n5262 board with nRF52840, SX1262, USB-C, 1.14 inch color TFT, and optional L76K GNSS add-on.
</p>

> **Use it right:** KoalaByte Blue is for lawful education, owned-device research, defensive testing, and authorized Bluetooth/CAN assessment only. Keep scans, captures, reviews, and bench tests inside your own lab, your own devices, or written scope.

---

## What this branch targets

The `heltec` branch is the KoalaByte Blue hardware profile for a USB-connected Heltec T114 board. The Heltec board is **not wired to the Raspberry Pi GPIO header** for GPS, LoRa, BLE, or the KillerKoala mouth display. It connects to the Pi by USB-C data cable and talks over USB CDC serial.

Core hardware in this branch:

| Component | Exact model / type | Connection to Pi | Purpose |
|---|---|---|---|
| Main SBC | Raspberry Pi 3 Model B+ | Main host | Linux companion, menu/actions, logs, voice/AI wrapper. |
| Eye display | Waveshare ESP32-S3-DualEye-LCD-1.28 | USB data cable | Animated KillerKoala eyes and KoalaByte UI screens. |
| Mouth / radio / GNSS board | Heltec Mesh Node T114 v2 / HT-n5262 | USB-C data cable | nRF52840 BLE, SX1262 LoRa, 1.14 inch ST7789 color TFT mouth, optional L76K GNSS forwarding. |
| GNSS add-on | Heltec L76K GNSS module | T114 8-pin 1.25 mm GNSS connector | GPS/GNSS data into the T114; forwarded to Pi over USB. |
| CAN adapter | InnoMaker USB to CAN Converter kit | USB data cable | Optional isolated bench-simulator or owned-harness CAN work. |
| BLE dongle | Nordic nRF52840 USB Dongle / PCA10059 | Optional USB | Legacy/alternate KoalaByte Lab or Koala Konnect target if you still want a separate BLE dongle. |

The clean physical wiring model is:

```text
Raspberry Pi USB port or powered USB hub
  -> ESP32-S3 DualEye USB data cable
  -> Heltec T114 USB-C data cable
  -> optional InnoMaker USB-to-CAN adapter
  -> optional separate Nordic nRF52840 USB Dongle

Heltec T114 GNSS connector
  -> L76K GNSS module cable

Heltec T114 RF connector
  -> correct LoRa antenna
```

Do **not** wire Heltec TX/RX to the Pi GPIO header for the KillerKoala face, GNSS, LoRa, BLE, or Meshtastic-style control path.

---

## Board roles

### ESP32-S3 DualEye

The ESP32-S3 DualEye firmware renders **eyes only** for the KillerKoala AI face. The physical case forms the koala head and ears. Koalagotchi applications such as Eucalyptus Mode can still use the display for their own UI, and the AI face is suppressed while those app screens are active.

### Heltec Mesh Node T114 v2

The Heltec T114 firmware is written around the correct board profile:

- nRF52840 target using the local `heltec_t114` PlatformIO board definition.
- Local `Heltec_T114_Board` Arduino variant with the T114 raw GPIO identity map.
- ST7789 color TFT renderer for the lower koala face channel.
- Solid orange animated mouth, black nose, fuzzy grey cheeks.
- USB CDC JSON command channel from the Pi.
- Optional L76K GNSS UART readout forwarded to the Pi over USB as `gnss_nmea` JSON.

### Raspberry Pi

The Pi remains the orchestrator. It sends face/action state to the ESP32 and Heltec over their USB serial ports. The Pi bridge prefers `KOALABYTE_HELTEC_USB_PORT`, then `KOALABYTE_HELTEC_FACE_PORT`, then `HELTEC_PORT`, and can auto-search common Linux/macOS USB serial paths.

---

## One-script install

The Heltec branch now folds the manual firmware sequence into a single command:

```bash
HELTEC_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --install-firmware
```

That option performs the equivalent of:

```bash
git checkout heltec
python3 scripts/check_repo_readiness.py
BUILD_ONLY=1 bash scripts/flash_all_components.sh --all
HELTEC_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --heltec-t114
```

It checks out the `heltec` branch, runs the readiness check, does a build-only preflight, installs/updates the Pi companion, flashes the ESP32-S3 DualEye if connected/configured, flashes the Heltec T114 over USB-C, and runs the CAN manifest check.

---

## Fast flashing and build path

Start with Raspberry Pi OS Lite 64-bit, enable SSH, clone the repo, and run the readiness check:

```bash
sudo apt update
sudo apt install -y git

git clone https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
git checkout heltec

python3 scripts/check_repo_readiness.py
```

Build everything without flashing:

```bash
bash scripts/flash_all_components.sh --all --build-only
```

Flash the ESP32-S3 DualEye only:

```bash
ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32
```

Flash the Heltec T114 color mouth/GNSS firmware over USB-C:

```bash
HELTEC_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --heltec-t114
```

Flash the legacy separate nRF52840 Dongle profile only when you are using that extra dongle:

```bash
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --nrf-lab
```

Run the full branch flow without the checkout/build preflight wrapper:

```bash
bash scripts/flash_all_components.sh --all
```

The Heltec T114 target also has its own helper:

```bash
BUILD_ONLY=1 scripts/flash_heltec_mouth.sh
HELTEC_PORT=/dev/ttyACM0 scripts/flash_heltec_mouth.sh
```

---

## USB runtime ports

Set ports explicitly when the Pi has multiple serial devices:

```bash
export KOALABYTE_ESP32_FACE_PORT=/dev/ttyUSB0
export KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0
```

Then test the synchronized eyes and mouth:

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_face_demo.py --sequence
```

Ask the Heltec for GNSS status over USB by sending JSON to the Heltec port:

```json
{"type":"gnss_status"}
```

GNSS NMEA forwarding from the T114 to the Pi uses this JSON shape:

```json
{"type":"gnss_nmea","device":"heltec-t114","transport":"usb-cdc","nmea":"$GNRMC,..."}
```

---

## Main actions and safe scope

KoalaByte Blue keeps the same safe companion workflow from the main branch:

- Safe local BLE inventory and passive observation.
- Eucalyptus Mode Koalagotchi Bluetooth scanner/logger screen.
- KillerKoala XP and ranks: Noob, Hacker, Legend.
- “that’s not a knife” defensive monitor suite.
- Boomerang camera-awareness logbook.
- Authorized BLE inventory and report helpers.
- Optional InnoMaker USB-to-CAN bench-simulator workflows.

Eucalyptus Mode visualizes passive logs only. It does not start pairing, probing, disruption, access, or offensive Bluetooth workflows. CAN transmit remains gated for isolated bench-simulator or owned-harness use only.

---

## Heltec-specific files

```text
firmware/heltec-mouth/platformio.ini
firmware/heltec-mouth/boards/heltec_t114.json
firmware/heltec-mouth/variants/Heltec_T114_Board/variant.h
firmware/heltec-mouth/variants/Heltec_T114_Board/variant.cpp
firmware/heltec-mouth/include/config.h
firmware/heltec-mouth/src/main.cpp
firmware/heltec-mouth/README.md
scripts/flash_heltec_mouth.sh
scripts/flash_all_components.sh
pi-companion/koalablue/killerkoala_face_bridge.py
scripts/run_killerkoala_face_demo.py
```

---

## Smoke checks

```bash
python3 scripts/check_repo_readiness.py
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_face_demo.py --sequence
PYTHONPATH=pi-companion python3 scripts/check_eucalyptus_cyberpet.py
PYTHONPATH=pi-companion python3 scripts/check_thats_not_a_knife_monitors.py
PYTHONPATH=pi-companion python3 scripts/run_thats_not_a_knife_loop.py --once
```

---

## Project vibe

KoalaByte Blue is supposed to feel like a real little cyber field companion: practical enough for a bench, weird enough to be memorable, and safe enough to demo without turning your lab into chaos. KillerKoala watches the canopy, eats Bluetooth eucalyptus data in Eucalyptus Mode, keeps a contentment meter, gains XP through approved successful actions, and only celebrates behavior that stays inside the lab scope.
