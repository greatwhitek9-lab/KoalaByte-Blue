# RevA17 KoalaByte Lab

## Purpose

KoalaByte Lab is the safe transmit-oriented lab mode for KoalaByte Blue. It uses the Nordic nRF52840 Dongle / PCA10059 to advertise a clearly named, synthetic BLE service-data payload that can be observed by KoalaByte Blue passive scans, mobile BLE scanner apps, or protocol-analysis tools.

It is for owned-device signal-integrity observation and workflow validation. It does not replay captured packets, captured identifiers, preambles, access addresses, PDUs, or raw radio buffers.

## Firmware path

```text
firmware/nrf52840-dongle-ear-tag-tx-lab/
```

Important files:

```text
firmware/nrf52840-dongle-ear-tag-tx-lab/src/main.c
firmware/nrf52840-dongle-ear-tag-tx-lab/prj.conf
firmware/nrf52840-dongle-ear-tag-tx-lab/README.md
```

The internal firmware path is retained for compatibility, but the user-facing mode and advertised BLE name are now KoalaByte Lab.

## Advertisement name

```text
KoalaByte Lab
```

## Synthetic payload

The advertisement includes a 128-bit service-data block with:

```text
KBTX magic bytes
format version
static synthetic pattern bytes
sequence counter
simple XOR check byte
```

The sequence counter updates every 5 seconds. This gives passive observers a harmless sequence field for packet-loss notes and RSSI trend analysis.

## Build and flash

Build:

```bash
bash scripts/build_nrf52840_dongle_lab.sh
```

Create DFU package:

```bash
bash scripts/flash_nrf52840_dongle_lab_dfu.sh
```

Flash after putting the Dongle into bootloader mode and identifying the DFU port:

```bash
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_nrf52840_dongle_lab_dfu.sh
```

Manual build:

```bash
west build -b nrf52840dongle_nrf52840 firmware/nrf52840-dongle-ear-tag-tx-lab -d build/nrf52840-dongle-lab
```

## Pi-side plan artifact

```bash
PYTHONPATH=pi-companion python3 scripts/run_ear_tag_tx_lab.py
```

Output:

```text
logs/koalabyte_lab/koalabyte_lab_plan_YYYYMMDD_HHMMSS.json
```

## Observe from KoalaByte Blue

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kapture.py --duration-seconds 30 --target-name "KoalaByte Lab"
```

Or use the normal passive scan/menu flow and look for `KoalaByte Lab`.

## Safety boundary

KoalaByte Lab is synthetic and clearly labeled. Koala Kry remains offline metadata replay only. Captured-signal over-the-air replay is intentionally not part of this repository.
