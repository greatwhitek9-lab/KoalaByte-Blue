# Legacy KoalaByte Blue External nRF52840 Dongle BLE Observer

This firmware target is retained for the Nordic nRF52840 USB Dongle / PCA10059 / NRF52840-DONGLE as an explicit legacy compatibility target.

It is **not** the default BLE board for `koalabyte_blue_v2_heltec_edition`. The Heltec Edition uses the **Heltec Mesh Node T114 onboard nRF52840** as the primary BLE board. ESP32-S3 DualEye and Raspberry Pi BlueZ are additional BLE nodes.

## Safety scope

This firmware is intentionally limited to passive BLE advertisement observation and local serial reporting.

## Build

```bash
BUILD_LEGACY_NRF_DONGLE=1 bash scripts/build_firmware_all.sh
# or
bash scripts/build_nrf52840_dongle_ble_primary.sh
```

Manual build:

```bash
west build -b nrf52840dongle_nrf52840 firmware/nrf52840-dongle-ble-primary -d build/nrf52840-dongle-ble-primary
```

## DFU package / flashing

```bash
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_nrf52840_dongle_ble_primary_dfu.sh
```

The Heltec Edition one-shot install does **not** run this target by default. Use the explicit legacy target only when you intentionally want to build or flash an external dongle:

```bash
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --nrf-ble-primary
```

## Runtime event shape

Legacy external dongle event shape:

```json
{"type":"ble_adv_seen","device":"nrf52840-dongle","source":"nrf52840-dongle","role":"primary","transport":"usb-cdc","addr":"AA:BB:CC:DD:EE:FF","addr_type":"random","rssi":-61,"active_scan":false}
```

For the current Heltec Edition service, the preferred primary event source is:

```json
{"type":"ble_adv_seen","device":"heltec-t114-nrf52840","source":"heltec-t114-nrf52840","role":"primary","transport":"usb-cdc","addr":"AA:BB:CC:DD:EE:FF","addr_type":"random","rssi":-61,"active_scan":false}
```

The Pi service logs merged events under:

```text
logs/ble_nodes/ble_events.jsonl
logs/ble_nodes/ble_state.json
```