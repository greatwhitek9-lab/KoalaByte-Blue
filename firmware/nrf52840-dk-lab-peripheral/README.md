# KoalaByte Blue nRF52840 DK Ear Tag TX Lab Peripheral

Safe, authorized-lab firmware for the optional **Nordic nRF52840 DK / PCA10056**.

This project is intended for development and validation. It advertises as a clearly labeled KoalaByte lab peripheral named `EarTag-TX-Lab`, emits a synthetic service-data pattern for signal-integrity observation, and exposes a read-only GATT status characteristic for client/app testing.

It does not replay captured packets, captured identifiers, or raw NRF_RADIO packet bytes.

## Hardware

- Board: Nordic nRF52840 DK
- Nordic board ID: `nrf52840dk_nrf52840`
- Hardware role: optional development/debug board
- Final KoalaByte Blue compact build still uses: nRF52840 Dongle / PCA10059

## Safety scope

This firmware is intentionally limited to:

- Clear lab-device advertising
- Synthetic owned-device service-data pattern
- Sequence counter for observation and packet-loss notes
- One read-only GATT status characteristic
- Console logging over USB/J-Link serial
- No third-party device impersonation
- No disruptive radio behavior
- No unauthorized connection workflow

## Synthetic advertisement payload

The advertisement carries a 128-bit service-data block with:

```text
KBTX magic bytes
format version
static synthetic pattern bytes
sequence counter
simple XOR check byte
```

The sequence counter updates every 5 seconds by restarting advertising with fresh service data. This gives the Pi companion, BLE scanner apps, or protocol tools a harmless sequence field to observe.

## Build with nRF Connect SDK

Install Nordic nRF Connect SDK and `west`, then run from the repo root:

```bash
west build -b nrf52840dk_nrf52840 firmware/nrf52840-dk-lab-peripheral -d build/nrf52840-dk-lab-peripheral
```

## Flash

With the DK plugged in over USB:

```bash
west flash -d build/nrf52840-dk-lab-peripheral
```

Or use the helper:

```bash
./scripts/flash_nrf52840_dk_lab.sh
```

## Generate the Pi-side plan artifact

```bash
PYTHONPATH=pi-companion python3 scripts/run_ear_tag_tx_lab.py
```

## Test

Scan with a BLE scanner app or KoalaByte Blue passive scan. You should see:

```text
EarTag-TX-Lab
```

GATT exposes a read-only status characteristic containing:

```text
KoalaByte Blue Ear Tag TX Lab; synthetic owned-device BLE advertisement; no captured packet replay
```
