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
- Primary BLE advertisement observation from the T114 nRF52840, emitted to the Pi as `ble_adv_seen` JSON.

### Raspberry Pi

The Pi remains the orchestrator. It sends face/action state to the ESP32 and Heltec over their USB serial ports. The Pi bridge prefers `KOALABYTE_HELTEC_USB_PORT`, then `KOALABYTE_HELTEC_FACE_PORT`, then `HELTEC_PORT`, and can auto-search common Linux/macOS USB serial paths.

The Pi-side BLE node manager runs as `koalabyte-ble-node-manager.service` after one-shot install. It starts the Heltec T114 as the primary passive BLE node, treats ESP32-S3 and Pi BlueZ as secondary/fallback observers, deduplicates observations, and writes logs under `logs/ble_nodes/`.

---

## One-script install

The Heltec branch now folds the manual firmware and BLE node-manager sequence into a single command:

```bash
HELTEC_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --install-firmware
```

That option performs the equivalent of:

```bash
git checkout heltec
python3 scripts/check_repo_readiness.py
BUILD_ONLY=1 bash scripts/flash_all_components.sh --all
HELTEC_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --heltec-t114
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 bash scripts/install_ble_node_manager_service.sh
```

It checks out the `heltec` branch, runs the readiness check, does a build-only preflight, installs/updates the Pi companion, flashes the ESP32-S3 DualEye if connected/configured, flashes the Heltec T114 BLE-primary firmware over USB-C, installs/enables/starts the BLE node manager service, and runs the CAN manifest check.

---

## Boot / DFU / flash mode instructions

Use this before running the one-shot install or any individual flash target.

| Hardware | Needs manual boot/DFU mode? | When to do it |
|---|---|---|
| **Heltec Mesh Node T114 v2** | Usually no. Try normal USB-C upload first. Manual bootloader mode may be needed if PlatformIO cannot open/upload to the port. | Before `--install-firmware` or `--heltec-t114` only if normal upload fails or the port does not appear. |
| **ESP32-S3 DualEye** | Usually no. The USB serial bridge normally auto-enters download mode. Manual BOOT mode may be needed if upload stalls at `Connecting...`. | Before `--install-firmware` or `--esp32` only if auto-upload fails. |
| **Nordic nRF52840 USB Dongle / PCA10059** | Yes, when flashing the optional legacy dongle profile. It must be in DFU/bootloader mode for `nrfutil dfu`. | Before `--nrf-lab` or `--nrf-konnect` if you are flashing the optional dongle on this branch. |
| **InnoMaker USB-to-CAN Converter kit** | No. KoalaByte does not flash firmware to it. | Never for KoalaByte setup. Plug it in by USB only after the Pi is running, or before install if you only want manifest/status checks. |
| **Raspberry Pi onboard BLE / BlueZ** | No. | Never. It is configured by Linux packages/services, not board boot mode. |

### Heltec T114 normal flashing path

1. Connect the Heltec T114 to the Raspberry Pi with a real USB-C **data** cable.
2. Check which serial device appeared:

```bash
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

3. Use that port for the one-shot install:

```bash
HELTEC_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --install-firmware
```

4. If the upload works, do not press any boot buttons.

### Heltec T114 manual bootloader recovery

Use this only if PlatformIO cannot upload, the port disappears, or the upload helper cannot find the board.

1. Keep the Heltec T114 plugged into the Pi by USB-C.
2. Open a second SSH window and watch USB serial changes:

```bash
dmesg -w
```

3. Try the reset-only method first: tap **RESET/RST** once.
4. Run the port check again:

```bash
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

5. If reset-only does not expose a bootloader/upload port, use the button-combo method:
   - Hold **BOOT**, **USER**, or **PRG**. The exact label depends on the T114 board revision.
   - While holding it, tap **RESET/RST** once.
   - Release **RESET/RST**.
   - Wait two seconds.
   - Release **BOOT/USER/PRG**.
6. Re-run the flash command with the newly visible port:

```bash
HELTEC_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --heltec-t114
```

7. After a successful flash, tap **RESET/RST** once to boot the new firmware if it does not restart by itself.

### ESP32-S3 DualEye normal flashing path

1. Connect the ESP32-S3 DualEye to the Pi with a USB **data** cable.
2. Check the port:

```bash
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

3. Flash normally:

```bash
ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32
```

4. If upload works, do not use BOOT mode.

### ESP32-S3 DualEye manual BOOT/download mode

Use this only if the ESP32 upload stalls at `Connecting...`, fails to sync, or repeatedly resets without accepting firmware.

1. Hold the **BOOT** button.
2. Tap **RESET/EN** once while still holding **BOOT**.
3. Release **RESET/EN**.
4. Keep holding **BOOT** for about two seconds.
5. Release **BOOT**.
6. Run the flash command again:

```bash
ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32
```

7. After flashing, tap **RESET/EN** once to boot the app if the board stays in download mode.

### Optional nRF52840 Dongle DFU mode

The Heltec branch normally uses the Heltec T114 as the main BLE device. Only follow this section if you are also flashing the optional separate Nordic nRF52840 Dongle.

1. Plug the nRF52840 Dongle into the Pi or powered USB hub.
2. Put the Dongle into bootloader/DFU mode by pressing the Dongle **RESET** button once. If your enclosure covers the button, use the reset access hole you designed into the case.
3. Watch for the DFU serial port:

```bash
ls /dev/ttyACM* 2>/dev/null
dmesg | tail -40
```

4. Set the DFU port and flash the optional profile:

```bash
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --nrf-lab
```

5. After DFU completes, the Dongle reboots into the flashed profile. If the runtime serial port changes, update the relevant runtime port variable.

### InnoMaker USB-to-CAN kit

The InnoMaker USB-to-CAN kit does **not** need a boot mode for KoalaByte. Do not press, short, or reflash anything on the CAN adapter for this project.

1. Plug the InnoMaker adapter into the Pi by USB.
2. Confirm Linux sees it:

```bash
lsusb
ip link
```

3. Use KoalaByte only for manifest/status or isolated bench-simulator workflows:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
```

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

Build everything without flashing or installing services:

```bash
bash scripts/flash_all_components.sh --all --build-only
```

Flash the ESP32-S3 DualEye only:

```bash
ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32
```

Flash the Heltec T114 color mouth/GNSS/BLE-primary firmware over USB-C:

```bash
HELTEC_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --heltec-t114
```

Install/start only the BLE node manager service:

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --ble-node-manager
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

BLE advertisement events from the T114 primary node use this JSON shape:

```json
{"type":"ble_adv_seen","device":"heltec-t114","source":"heltec-t114","role":"primary","transport":"usb-cdc","addr":"AA:BB:CC:DD:EE:FF","addr_type":"random","rssi":-61,"active_scan":false}
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
docs/HELTEC_BLE_NODE_ROLES.md
pi-companion/koalablue/ble_event_log.py
pi-companion/koalblue/ble_node_manager.py
pi-companion/koalablue/killerkoala_face_bridge.py
scripts/flash_heltec_mouth.sh
scripts/flash_all_components.sh
scripts/install_ble_node_manager_service.sh
scripts/run_ble_node_manager.py
scripts/run_ble_node_manager_service.sh
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
