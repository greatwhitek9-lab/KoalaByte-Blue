# T114 Plug-In Flashing

The KoalaByte Blue V2 Heltec Edition installer supports plug-in-triggered T114 firmware flashing.

## Default behavior

During `scripts/install_pi.sh`, after the repo readiness check and T114 protocol artifact generation, the installer runs:

```bash
bash scripts/flash_t114_when_plugged.sh
```

Because `scripts/flash_all_components.sh --install-firmware` and `scripts/flash_all_components.sh --all` both run `scripts/install_pi.sh`, those one-shot paths also use this plug-in flashing flow.

## Default profile

Default profile:

```bash
T114_PLUG_FLASH_PROFILE=combined-safe
```

`combined-safe` makes the **Heltec T114 onboard nRF52840** the primary KoalaByte Blue BLE transceiver. It emits normalized passive BLE advertisement JSON over USB CDC, accepts Pi-commanded bounded non-connectable lab-beacon TX commands, handles KillerKoala mouth/status JSON on the same serial stream, and exposes guarded GNSS/LoRa status hooks.

The Raspberry Pi remains the control plane. It processes menu actions, automated wrappers, logs, reports, and command routing. The ESP32-S3 DualEye BLE and Raspberry Pi BlueZ adapter remain secondary nodes handled by the Pi-side BLE node manager.

## Dependencies included by the one-shot path

The one-shot installer calls the Heltec setup helper before flashing. That helper covers:

```text
Pi system packages:
  bluetooth, bluez, bluez-tools, rfkill, usbutils, udev, build tools

Python runtime:
  pyserial, bleak

Heltec/nRF52840 build + flash tooling:
  west, nrfutil, nRF Connect SDK / Zephyr workspace

Stable device path:
  /dev/koalabyte-heltec through KoalaByte udev rules
```

The important split is:

```text
Raspberry Pi       -> action processing, BlueZ wrapped automation, logs, reports, service orchestration
Heltec nRF52840    -> main BLE receiver/transmitter over USB CDC JSON
ESP32-S3 DualEye   -> secondary BLE/UI/face node
Pi BlueZ adapter   -> secondary/fallback BLE node
```

## Other profiles

Legacy mouth-only profile:

```bash
T114_PLUG_FLASH_PROFILE=color-mouth
```

Optional HCI USB profile:

```bash
T114_PLUG_FLASH_PROFILE=hci-usb
```

Use `hci-usb` only when you intentionally want the T114 to behave as a USB Bluetooth adapter for the host instead of running the combined local BLE application.

Skip plug-in flashing:

```bash
FLASH_T114_ON_PLUG=0
```

Non-strict mode:

```bash
STRICT_T114_PLUG_FLASH=0
```

## What the plug-in helper does

`scripts/flash_t114_when_plugged.sh` waits for a Heltec T114 USB device at one of these paths:

```text
KOALABYTE_HELTEC_USB_PORT
KOALABYTE_PRIMARY_BLE_PORT
HELTEC_PORT
/dev/koalabyte-heltec
/dev/ttyACM0
/dev/ttyACM1
/dev/ttyUSB0
/dev/ttyUSB1
```

When the board appears, it runs the selected helper:

```text
combined-safe -> scripts/flash_t114_combined_safe.sh
color-mouth   -> scripts/flash_heltec_mouth.sh
hci-usb       -> scripts/flash_nrf52840_t114_hci_usb.sh
```

It writes status to:

```text
logs/t114_plug_flash_status.json
```

## Helper targets

The combined-safe helper uses:

```text
firmware/t114-combined-safe/CMakeLists.txt
firmware/t114-combined-safe/prj.conf
firmware/t114-combined-safe/src/main.c
scripts/build_t114_combined_safe.sh
scripts/flash_t114_combined_safe.sh
```

The legacy color-mouth helper uses:

```text
firmware/heltec-mouth/platformio.ini
firmware/heltec-mouth/src/main.cpp
```

The HCI USB helper uses:

```text
scripts/build_nrf52840_t114_hci_usb.sh
scripts/flash_nrf52840_t114_hci_usb.sh
```

## Commands

Flash the default combined-safe firmware when plugged in:

```bash
T114_PLUG_FLASH_PROFILE=combined-safe bash scripts/flash_t114_when_plugged.sh
```

Flash legacy color-mouth when plugged in:

```bash
T114_PLUG_FLASH_PROFILE=color-mouth bash scripts/flash_t114_when_plugged.sh
```

Flash HCI USB when plugged in:

```bash
T114_PLUG_FLASH_PROFILE=hci-usb bash scripts/flash_t114_when_plugged.sh
```

Check the flow without waiting or flashing:

```bash
bash scripts/flash_t114_when_plugged.sh --check-only
```

## Automated BLE action checks

After flashing, the Pi can drive the T114 primary BLE radio through the wrapper:

```bash
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py controller-check
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py status
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py scan --duration-seconds 30
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py tx-status
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py lab-advertise-start --confirm-send --duration-seconds 30 --tx-name "KoalaByte Lab"
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py lab-advertise-stop
```

In default combined-safe mode, these commands do not require the T114 to appear as a Linux HCI adapter. The Pi wraps the automation and talks to the T114 over USB CDC JSON.

## Guardrail

The combined-safe firmware intentionally keeps GNSS UART parsing and SX1262 LoRa radio driving behind status hooks until the exact Heltec T114 GNSS UART pins, LoRa SPI pins, DIO pins, reset pin, busy pin, RF switch behavior, and recovery procedure are validated on the physical board.

The BLE TX path is limited to bounded, non-connectable, explicitly confirmed owned-lab beacon/status use. It does not pair, connect, perform GATT writes, spoof another device, replay packets, jam, or disrupt.
