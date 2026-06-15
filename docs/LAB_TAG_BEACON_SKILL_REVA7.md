# RevA15 Ear Tag / Ear Tag TX Lab Beacon Skill

## Purpose

The safe lab BLE beacon skill is named **Ear Tag**. It is designed for owned-device testing and advertises a clearly labeled lab BLE name that KoalaByte Blue can detect, log, and report during authorized lab work.

RevA15 adds **Ear Tag TX Lab**, a synthetic owned-device advertisement pattern for signal-integrity observation. It does not replay captured packets or captured identifiers.

This is useful for:

- Testing KoalaByte Blue BLE scanning and logging.
- Testing local mobile BLE scanner apps.
- Validating reports and lab workflows.
- Demonstrating how named BLE advertisements appear in the KoalaByte Blue UI.
- Observing synthetic sequence counters and RSSI trends in an owned lab setting.

## Behavior

The current dongle lab firmware advertises as:

```text
EarTag-TX-Lab
```

It includes a synthetic 128-bit service-data field containing:

```text
KBTX magic bytes
format version
static pattern bytes
sequence counter
simple XOR check byte
```

The sequence counter updates every 5 seconds. Use a name that clearly identifies the device as your own lab beacon.

## Safety boundary

This skill is limited to clearly labeled lab-device advertising, synthetic service data, and a read-only status characteristic.

## Configure the lab beacon name

Edit:

```text
firmware/nrf52840-dongle-ear-tag-tx-lab/prj.conf
```

Set:

```text
CONFIG_BT_DEVICE_NAME="EarTag-TX-Lab"
```

Or use the helper:

```bash
python3 scripts/set_lab_ble_name.py EarTag-TX-Lab
```

## Build and flash the dongle

Build the retained Nordic dongle firmware:

```bash
bash scripts/build_nrf52840_dongle_lab.sh
```

Create the DFU package and flash when the dongle is in bootloader mode:

```bash
bash scripts/flash_nrf52840_dongle_lab_dfu.sh
```

Or set the DFU port explicitly:

```bash
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_nrf52840_dongle_lab_dfu.sh
```

## Generate a Pi-side Ear Tag TX Lab plan

```bash
PYTHONPATH=pi-companion python3 scripts/run_ear_tag_tx_lab.py
```

## Test

Run KoalaByte Blue passive scan or a BLE scanner app. Confirm the advertisement name matches your lab name and that captures are stored under `/blecaptures/` when `eucalyptus` always-on capture is enabled.
