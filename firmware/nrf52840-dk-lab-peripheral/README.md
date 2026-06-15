# KoalaByte Blue nRF52840 DK Lab Peripheral

Safe, authorized-lab firmware for the optional **Nordic nRF52840 DK / PCA10056**.

This project is intended for development and validation. It lets the DK advertise as a clearly labeled KoalaByte lab peripheral and exposes a read-only GATT status characteristic for client/app testing.

## Hardware

- Board: Nordic nRF52840 DK
- Nordic board ID: `nrf52840dk_nrf52840`
- Hardware role: optional development/debug board
- Final KoalaByte Blue compact build still uses: nRF52840 Dongle / PCA10059

## Safety scope

This firmware is intentionally limited to:

- Clear lab-device advertising
- One read-only GATT status characteristic
- Console logging over USB/J-Link serial
- No third-party device impersonation
- No disruptive radio behavior
- No unauthorized connection workflow

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

## Test

Scan with a BLE scanner app or KoalaByte Blue passive scan. You should see:

```text
KoalaBlue-Lab
```

GATT exposes a read-only status characteristic containing:

```text
KoalaByte Blue authorized lab peripheral; read-only demo
```
