# Main branch BLE node roles

The `main` branch uses the Nordic nRF52840 USB Dongle / PCA10059 as the primary KoalaByte Blue BLE node.

## Role model

| Node | Role | Notes |
|---|---|---|
| nRF52840 USB Dongle | Primary | Canonical passive BLE advertisement observer and source of truth. |
| ESP32-S3 DualEye BLE | Secondary | Emits local BLE observations from the eye/display controller when enabled. |
| Raspberry Pi onboard BlueZ | Secondary / fallback | Linux observer used for enrichment or fallback when the Dongle is unavailable. |

The Pi companion merges events and resolves duplicate observations in favor of the nRF52840 Dongle.

## One-shot install path

The normal main-branch one-shot command now builds/flashes the Dongle BLE-primary firmware and installs/starts the Pi-side node manager service automatically:

```bash
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --install-firmware
```

The service is named:

```text
koalabyte-ble-node-manager.service
```

It launches `scripts/run_ble_node_manager.py --duration 0`, reads the Dongle serial JSON stream, folds in ESP32-S3 and Raspberry Pi BlueZ secondary observations, and writes logs under `logs/ble_nodes/`.

## Dongle event shape

```json
{"type":"ble_adv_seen","device":"nrf52840-dongle","source":"nrf52840-dongle","role":"primary","transport":"usb-cdc","addr":"AA:BB:CC:DD:EE:FF","addr_type":"random","rssi":-61,"active_scan":false}
```

## Manual runner

The service is installed by the one-shot flow. For bench testing only, the manager can also be run manually:

```bash
KOALABYTE_NRF_BLE_PORT=/dev/ttyACM0 PYTHONPATH=pi-companion python3 scripts/run_ble_node_manager.py --duration 30
```

Use `--duration 0` to keep listening. Use `--no-pi-bluez` to disable the Raspberry Pi onboard secondary observer.

Logs are written to:

```text
logs/ble_nodes/ble_events.jsonl
logs/ble_nodes/ble_state.json
logs/ble_nodes/service.log
logs/ble_nodes/service.err
```

## Legacy modes

The existing KoalaByte Lab peripheral and Koala Konnect HCI profiles remain available, but only one profile can be active on the nRF52840 Dongle at a time.

## Safety boundary

This feature is passive observation and local logging. It does not pair, connect, write, disrupt, spoof, or replay BLE traffic.
