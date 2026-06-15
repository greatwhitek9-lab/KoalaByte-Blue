# RevA15 Ear Tag TX Lab

## Purpose

Ear Tag TX Lab is the safe transmit-oriented lab mode for KoalaByte Blue. It uses the Nordic nRF52840 DK to advertise a clearly named, synthetic BLE service-data payload that can be observed by KoalaByte Blue passive scans, mobile BLE scanner apps, or protocol-analysis tools.

It is for owned-device signal-integrity observation and workflow validation. It does not replay captured packets, captured identifiers, preambles, access addresses, PDUs, or raw radio buffers.

## Firmware path

```text
firmware/nrf52840-dk-lab-peripheral/
```

Important files:

```text
firmware/nrf52840-dk-lab-peripheral/src/main.c
firmware/nrf52840-dk-lab-peripheral/prj.conf
firmware/nrf52840-dk-lab-peripheral/README.md
```

## Advertisement name

```text
EarTag-TX-Lab
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

```bash
bash scripts/flash_nrf52840_dk_lab.sh
```

Manual build:

```bash
west build -b nrf52840dk_nrf52840 firmware/nrf52840-dk-lab-peripheral -d build/nrf52840-dk-lab-peripheral
west flash -d build/nrf52840-dk-lab-peripheral
```

## Pi-side plan artifact

```bash
PYTHONPATH=pi-companion python3 scripts/run_ear_tag_tx_lab.py
```

Output:

```text
logs/ear_tag_tx_lab/ear_tag_tx_lab_plan_YYYYMMDD_HHMMSS.json
```

## Observe from KoalaByte Blue

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kapture.py --duration-seconds 30 --target-name EarTag-TX-Lab
```

Or use the normal passive scan/menu flow and look for `EarTag-TX-Lab`.

## Safety boundary

Ear Tag TX Lab is synthetic and clearly labeled. Koala Kry remains offline metadata replay only. Captured-signal over-the-air replay is intentionally not part of this repository.
