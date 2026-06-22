# KoalaByte Blue nRF52840 Dongle BLE Primary Node

This firmware target is for the Nordic nRF52840 USB Dongle / PCA10059 / NRF52840-DONGLE on the main KoalaByte Blue branch.

It turns the Dongle into the **primary passive BLE observer** for KoalaByte Blue. The Raspberry Pi consumes newline-delimited JSON events over the Dongle USB CDC serial interface and treats the Dongle as the canonical BLE source. ESP32-S3 DualEye BLE and Raspberry Pi BlueZ can act as secondary/fallback nodes.

## Safety scope

This firmware is intentionally limited to passive BLE advertisement observation and local serial reporting.

It does not pair, connect, write, spoof, disrupt, or replay BLE traffic.

## Build

```bash
bash scripts/build_nrf52840_dongle_ble_primary.sh
```

Manual build:

```bash
west build -b nrf52840dongle_nrf52840 firmware/nrf52840-dongle-ble-primary -d build/nrf52840-dongle-ble-primary
```

## DFU package / flashing

```bash
bash scripts/flash_nrf52840_dongle_ble_primary_dfu.sh
```

Flash after putting the Dongle into bootloader mode and identifying the DFU serial port:

```bash
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_nrf52840_dongle_ble_primary_dfu.sh
```

The main one-shot flow runs this as the default Dongle BLE role:

```bash
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --install-firmware
```

## Runtime event shape

```json
{"type":"ble_adv_seen","device":"nrf52840-dongle","source":"nrf52840-dongle","role":"primary","transport":"usb-cdc","addr":"AA:BB:CC:DD:EE:FF","addr_type":"random","rssi":-61,"active_scan":false}
```

The Pi service logs merged events under:

```text
logs/ble_nodes/ble_events.jsonl
logs/ble_nodes/ble_state.json
```
