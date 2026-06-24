# KoalaByte Blue V2 Heltec Edition BLE node roles

The `koalabyte_blue_v2_heltec_edition` architecture uses the **Heltec Mesh Node T114 onboard Nordic nRF52840** as the primary KoalaByte Blue BLE board.

## Role model

| Node | Role | Notes |
|---|---|---|
| Heltec Mesh Node T114 nRF52840 | Primary BLE board | Canonical passive BLE advertisement observer and source of truth. The same board also carries the SX1262 LoRa radio for Heltec Edition radio work. |
| ESP32-S3 DualEye BLE | Secondary node | Face/UI/controller BLE node. Emits local BLE observations from the eye/display controller when enabled and drives the front-panel experience. |
| Raspberry Pi onboard BlueZ | Secondary / fallback node | Linux BLE node used for enrichment, host-side checks, and fallback observations when needed. |

The Pi companion merges events and resolves duplicate observations in favor of the Heltec T114 nRF52840 primary BLE source. ESP32-S3 DualEye and Raspberry Pi BlueZ are still real BLE nodes; they are just not the canonical source of truth.

## Heltec Edition service path

The normal Heltec Edition service flow discovers the Heltec T114 first, then starts the Pi-side node manager service:

```bash
python3 scripts/discover_koalabyte_ports.py --profile heltec
python3 scripts/preflight_all_hardware.py --profile heltec
bash scripts/install_ble_node_manager_service.sh
```

The service is named:

```text
koalabyte-ble-node-manager.service
```

It launches `scripts/run_ble_node_manager.py --duration 0`, reads the Heltec T114 nRF52840 serial JSON stream as the primary BLE node, folds in ESP32-S3 and Raspberry Pi BlueZ secondary-node observations, and writes logs under `logs/ble_nodes/`.

## Primary event shape

Expected primary BLE events from the Heltec T114 nRF52840 should use this shape:

```json
{"type":"ble_adv_seen","device":"heltec-t114-nrf52840","source":"heltec-t114-nrf52840","role":"primary","transport":"usb-cdc","addr":"AA:BB:CC:DD:EE:FF","addr_type":"random","rssi":-61,"active_scan":false}
```

## Manual runner

The service is installed by the normal flow. For bench testing only, the manager can also be run manually:

```bash
KOALABYTE_PRIMARY_BLE_PORT=/dev/koalabyte-heltec PYTHONPATH=pi-companion python3 scripts/run_ble_node_manager.py --duration 30
```

Use `--duration 0` to keep listening. Use `--esp32-port /dev/koalabyte-esp32-eyes` to include the ESP32-S3 DualEye serial node explicitly. Use `--no-pi-bluez` to disable the Raspberry Pi onboard BlueZ secondary node.

Logs are written to:

```text
logs/ble_nodes/ble_events.jsonl
logs/ble_nodes/ble_state.json
logs/ble_nodes/service.log
logs/ble_nodes/service.err
```

## Legacy compatibility

Older wrapper scripts and environment files may still use names such as `KOALABYTE_NRF_BLE_PORT`, `NRF_BLE_PORT`, or `--dongle-port`. In the Heltec Edition, those are compatibility aliases for the Heltec T114 onboard nRF52840 primary BLE board. They should not be interpreted as requiring a separate nRF52840 USB Dongle.

## Safety boundary

This feature is passive observation and local logging only. Keep radio work lawful, local, owned-device, licensed, or explicitly in-scope.