# Heltec BLE node roles

The `heltec` branch uses the Heltec Mesh Node T114 v2 / HT-n5262 nRF52840 as the primary KoalaByte BLE node.

## Role model

| Node | Role | Notes |
|---|---|---|
| Heltec T114 nRF52840 | Primary | Canonical passive BLE advertisement scanner and source of truth. |
| ESP32-S3 DualEye BLE | Secondary | Optional assistant node. Should not override Heltec observations. |
| Raspberry Pi BlueZ | Secondary / fallback | Optional Linux observer or fallback when the Heltec is unavailable. |

The Pi companion merges events and resolves duplicate observations in favor of the Heltec T114.

## Heltec USB JSON commands

Start passive primary scanning:

```json
{"type":"ble_start","role":"primary","active_scan":false}
```

Stop scanning:

```json
{"type":"ble_stop"}
```

Request status:

```json
{"type":"ble_status"}
```

Set a non-primary node to secondary:

```json
{"type":"ble_set_role","role":"secondary"}
```

## Event shape

```json
{"type":"ble_adv_seen","device":"heltec-t114","source":"heltec-t114","role":"primary","transport":"usb-cdc","addr":"AA:BB:CC:DD:EE:FF","addr_type":"random","rssi":-61,"active_scan":false}
```

## Pi runner

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 PYTHONPATH=pi-companion python3 scripts/run_ble_node_manager.py --duration 30
```

Use `--duration 0` to keep listening. Use `--active-scan` only for owned-device lab work where scan-response collection is allowed.

Logs are written to:

```text
logs/ble_nodes/ble_events.jsonl
logs/ble_nodes/ble_state.json
```

## Safety boundary

This feature is passive observation and local logging. It does not pair, connect, write, disrupt, spoof, or replay BLE traffic.
