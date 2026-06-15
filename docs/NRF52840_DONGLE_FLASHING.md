# Flash nRF52840 Dongle / PCA10059 Ear Tag TX Lab Firmware

This guide covers the only retained Nordic BLE board in KoalaByte Blue:

```text
Nordic nRF52840 Dongle / PCA10059 / NRF52840-DONGLE
```

Legacy external Nordic development-board targets have been removed from the retained production and firmware build path. The current build is USB Dongle only.

## What the firmware does

The Dongle advertises as:

```text
EarTag-TX-Lab
```

It emits a synthetic 128-bit service-data pattern with KBTX magic bytes, static pattern bytes, a sequence counter, and a simple check byte. It does not replay captured packets or captured identifiers.

## Build with nRF Connect SDK / Zephyr

From the repository root:

```bash
bash scripts/build_nrf52840_dongle_lab.sh
```

Manual build:

```bash
west build -b nrf52840dongle_nrf52840 firmware/nrf52840-dongle-ear-tag-tx-lab -d build/nrf52840-dongle-lab
```

If your installed Zephyr/NCS version uses a newer board target naming style, override the board from the shell:

```bash
BOARD=<your_dongle_board_target> bash scripts/build_nrf52840_dongle_lab.sh
```

## Artifacts

Build outputs normally appear under:

```text
build/nrf52840-dongle-lab/zephyr/
```

Common useful artifacts:

```text
zephyr.hex
zephyr.bin
zephyr.elf
```

## Flashing / DFU note

The nRF52840 Dongle normally flashes through its USB bootloader/DFU flow.

Build the firmware first:

```bash
bash scripts/build_nrf52840_dongle_lab.sh
```

Create a DFU package:

```bash
bash scripts/flash_nrf52840_dongle_lab_dfu.sh
```

That command creates:

```text
build/nrf52840-dongle-lab/koalabyte-blue-nrf52840-dongle-dfu.zip
```

To flash after putting the Dongle in bootloader mode and identifying its serial DFU port:

```bash
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_nrf52840_dongle_lab_dfu.sh
```

Adjust the port for your OS, for example `/dev/ttyACM1`, `/dev/cu.usbmodem*`, or the relevant Windows COM port.

## Test

After flashing, scan with KoalaByte Blue passive scan or a BLE scanner app. Confirm:

```text
EarTag-TX-Lab
```

## Dongle summary

```text
Dongle board target:  nrf52840dongle_nrf52840
Dongle firmware path: firmware/nrf52840-dongle-ear-tag-tx-lab
Dongle build dir:     build/nrf52840-dongle-lab
Dongle flashing:      USB bootloader/DFU package flow
```
