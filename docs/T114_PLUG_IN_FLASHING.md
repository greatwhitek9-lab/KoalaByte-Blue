# T114 Plug-In Flashing

The KoalaByte Blue V2 Heltec Edition installer now supports plug-in-triggered T114 firmware flashing.

## Default behavior

During `scripts/install_pi.sh`, after the repo readiness check and T114 protocol artifact generation, the installer runs:

```bash
bash scripts/flash_t114_when_plugged.sh
```

Because `scripts/flash_all_components.sh --install-firmware` and `scripts/flash_all_components.sh --all` both run `scripts/install_pi.sh`, those one-shot paths also use this plug-in flashing flow.

## Profile selection

Default profile:

```bash
T114_PLUG_FLASH_PROFILE=color-mouth
```

HCI USB profile:

```bash
T114_PLUG_FLASH_PROFILE=hci-usb
```

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
color-mouth -> scripts/flash_heltec_mouth.sh
hci-usb     -> scripts/flash_nrf52840_t114_hci_usb.sh
```

It writes status to:

```text
logs/t114_plug_flash_status.json
```

## Helper targets

The color-mouth helper uses:

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

Flash color-mouth when plugged in:

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
