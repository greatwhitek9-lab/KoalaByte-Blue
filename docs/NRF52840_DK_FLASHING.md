# Flash nRF52840 DK Ear Tag TX Lab Firmware

This guide covers the optional **Nordic nRF52840 DK / PCA10056** firmware used for Ear Tag TX Lab.

## What this firmware does

The DK firmware advertises as:

```text
EarTag-TX-Lab
```

It emits a synthetic 128-bit service-data pattern with a sequence counter that updates every 5 seconds. It also exposes one custom read-only GATT status characteristic. It is intended for owned-device lab testing, app testing, signal-integrity observation, and validation before moving compact workflows back to the nRF52840 Dongle.

It does not replay captured packets or captured identifiers.

## Requirements

- Nordic nRF52840 DK / PCA10056
- Nordic nRF Connect SDK installed
- `west` command available
- USB cable connected to the DK debug USB port

## Build

From the repository root:

```bash
west build -b nrf52840dk_nrf52840 firmware/nrf52840-dk-lab-peripheral -d build/nrf52840-dk-lab-peripheral
```

## Flash

```bash
west flash -d build/nrf52840-dk-lab-peripheral
```

## One-command helper

```bash
./scripts/flash_nrf52840_dk_lab.sh
```

## Generate Pi-side plan

```bash
PYTHONPATH=pi-companion python3 scripts/run_ear_tag_tx_lab.py
```

## Test

Use a BLE scanner or the KoalaByte Blue passive scan mode. Confirm the DK advertises as:

```text
EarTag-TX-Lab
```

Then connect with your own authorized BLE client and read the status characteristic. It should return:

```text
KoalaByte Blue Ear Tag TX Lab; synthetic owned-device BLE advertisement; no captured packet replay
```

## Production note

The DK is not intended to replace the Dongle in the final compact enclosure. Use the DK for development, debugging, and validation; use the nRF52840 Dongle / PCA10059 in the final stacked KoalaByte Blue build.
