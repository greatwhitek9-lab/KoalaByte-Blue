# KoalaByte Blue nRF52840 Dongle KoalaByte Lab Peripheral

Safe, authorized-lab firmware for the production compact BLE board:

```text
Nordic nRF52840 Dongle / PCA10059 / NRF52840-DONGLE
```

This project advertises as a clearly labeled KoalaByte lab peripheral named `KoalaByte Lab`, emits a synthetic service-data pattern for signal-integrity observation, and exposes a read-only GATT status characteristic for client/app testing.

It does not replay captured packets, captured identifiers, or raw NRF_RADIO packet bytes.

The internal firmware folder remains `firmware/nrf52840-dongle-ear-tag-tx-lab/` for compatibility with existing build scripts.

## Hardware

- Board: Nordic nRF52840 Dongle / PCA10059
- Zephyr/NCS board target: `nrf52840dongle_nrf52840`
- Hardware role: production compact BLE board
- Flash method: USB bootloader / DFU package flow

## Safety scope

This firmware is intentionally limited to:

- Clear lab-device advertising
- Synthetic owned-device service-data pattern
- Sequence counter for observation and packet-loss notes
- One read-only GATT status characteristic
- Console/log output where available
- No third-party device impersonation
- No disruptive radio behavior
- No unauthorized connection workflow

## Build with nRF Connect SDK

Install Nordic nRF Connect SDK and `west`, then run from the repo root:

```bash
bash scripts/build_nrf52840_dongle_lab.sh
```

Manual build:

```bash
west build -b nrf52840dongle_nrf52840 firmware/nrf52840-dongle-ear-tag-tx-lab -d build/nrf52840-dongle-lab
```

## DFU package / flashing

Create a DFU package:

```bash
bash scripts/flash_nrf52840_dongle_lab_dfu.sh
```

Flash after putting the Dongle into bootloader mode and identifying the DFU serial port:

```bash
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_nrf52840_dongle_lab_dfu.sh
```

See:

```text
docs/NRF52840_DONGLE_FLASHING.md
```

## Generate the Pi-side plan artifact

```bash
PYTHONPATH=pi-companion python3 scripts/run_ear_tag_tx_lab.py
```

## Test

Scan with a BLE scanner app or KoalaByte Blue passive scan. You should see:

```text
KoalaByte Lab
```

GATT exposes a read-only status characteristic containing:

```text
KoalaByte Blue KoalaByte Lab; synthetic owned-device BLE advertisement; no captured packet replay
```
