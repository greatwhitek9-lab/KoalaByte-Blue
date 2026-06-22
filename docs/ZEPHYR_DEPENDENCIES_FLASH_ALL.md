# Zephyr dependencies for optional T114 Koala Konnect

The normal KoalaByte Blue Heltec Edition runtime uses PlatformIO for the ESP32-S3 DualEye and Heltec mouth/GNSS/BLE-primary firmware.

The optional Koala Konnect USB HCI profile uses Zephyr and therefore needs additional tooling.

## Normal runtime build path

```bash
BUILD_ONLY=1 bash scripts/flash_all_components.sh --all
```

This checks the repo, system packages, PlatformIO, ESP32 firmware, Heltec mouth/GNSS/BLE-primary firmware, BLE node manager integration, and CAN checks.

## Optional Koala Konnect build path

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_all_components.sh --nrf-konnect --build-only
```

This checks/prepares:

- `west`
- nRF tooling
- nRF Connect SDK / Zephyr workspace
- Zephyr `samples/bluetooth/hci_usb`
- Heltec T114 board target resolver
- optional T114 2.4 GHz antenna overlay helper

## Full optional flash path

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_all_components.sh --nrf-konnect
```

## Direct helpers

Build only:

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/build_nrf52840_t114_hci_usb.sh
```

Flash:

```bash
T114_FLASH_METHOD=west bash scripts/flash_nrf52840_t114_hci_usb.sh
```

Convenience wrappers:

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/build_koala_konnect_t114.sh
T114_FLASH_METHOD=west bash scripts/flash_koala_konnect_t114.sh
```

## Environment knobs

```text
NCS_WORKSPACE=$HOME/ncs
NCS_REVISION=v2.9.0
ZEPHYR_SDK_VERSION=0.17.0
STRICT_NRF_TOOLS=1
STRICT_NCS_TOOLCHAIN=1
T114_BOARD=heltec_t114_v2/nrf52840
T114_FLASH_METHOD=west
```

## When not to use this

Do not run the optional Koala Konnect flash if you want the T114 to remain in normal KoalaByte mouth/GNSS/BLE-primary mode.

To return to normal mode:

```bash
bash scripts/flash_heltec_mouth.sh
```
