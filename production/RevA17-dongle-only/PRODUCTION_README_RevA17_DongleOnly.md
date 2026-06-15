# KoalaByte Blue RevA17 Dongle-Only Production Package

## Purpose

This production package removes the nRF52840 DK/PCA10056 from the retained build and firmware path. The only Nordic BLE board used by KoalaByte Blue is now:

```text
Nordic nRF52840 Dongle / PCA10059 / NRF52840-DONGLE
```

Everything else remains aligned with the existing KoalaByte Blue stacked Pi 3B+ architecture:

```text
Raspberry Pi 3B+ companion
ESP32-S3 DualEye LCD 1.28 front-end
nRF52840 Dongle BLE board
six-button front-panel controls
Koala BlueZ tools
killerkoala companion vocabulary
Koala Kapture / Koala Kry safe workflows
Ear Tag TX Lab synthetic BLE advertisement firmware
```

## Production BOM

Use:

```text
production/RevA17-dongle-only/BOM_RevA17_DongleOnly.csv
```

The older RevA1 BOM was also updated to keep the production package consistent, but this RevA17 BOM is the current source of truth for the dongle-only build.

## Firmware paths

Retained firmware paths:

```text
firmware/esp32-dualeye/
firmware/nrf52840-dongle-ear-tag-tx-lab/
pi-companion/
```

Removed DK firmware/build paths:

```text
firmware/nrf52840-dk-lab-peripheral/
scripts/build_nrf52840_dk_lab.sh
scripts/flash_nrf52840_dk_lab.sh
docs/NRF52840_DK_FLASHING.md
```

## Flashing flow

Validate first:

```bash
python3 scripts/check_repo_readiness.py
```

ESP32:

```bash
bash scripts/flash_esp32.sh
```

Pi companion:

```bash
bash scripts/install_pi.sh
```

nRF52840 Dongle build:

```bash
bash scripts/build_nrf52840_dongle_lab.sh
```

nRF52840 Dongle DFU package/flash:

```bash
bash scripts/flash_nrf52840_dongle_lab_dfu.sh
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_nrf52840_dongle_lab_dfu.sh
```

Adjust the DFU serial port for your OS.

## Expected BLE output

After the dongle firmware is flashed, scan for:

```text
EarTag-TX-Lab
```

The advertisement is synthetic, clearly labeled, and intended for owned-device signal-integrity observation only. It does not replay captured packets or captured identifiers.

## Readiness rule

The repo readiness check intentionally fails if DK build/flash files or DK board-target text are reintroduced outside the readiness script itself.
