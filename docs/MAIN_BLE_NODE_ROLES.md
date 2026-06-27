# KoalaByte Blue V2 Heltec Edition BLE node roles

The `koalabyte_blue_v2_heltec_edition` architecture uses the **Heltec Mesh Node T114 onboard Nordic nRF52840** as the primary KoalaByte Blue BLE radio endpoint.

## Role model

| Node | Role | Notes |
|---|---|---|
| Heltec Mesh Node T114 nRF52840 | Primary BLE transceiver | Canonical passive BLE advertisement observer and Pi-commanded bounded TX endpoint. The same board also carries the SX1262 LoRa radio for Heltec Edition radio work, but LoRa driving stays guarded until the T114 pin map is validated. |
| ESP32-S3 DualEye BLE | Secondary node | Face/UI/controller BLE node. Emits local BLE observations from the eye/display controller when enabled and drives the front-panel experience. |
| Raspberry Pi onboard BlueZ | Secondary / fallback node | Linux BLE node used for enrichment, host-side checks, and fallback observations when needed. The Pi still owns action processing and automation. |

The Pi companion merges events and resolves duplicate observations in favor of the Heltec T114 nRF52840 primary BLE source. ESP32-S3 DualEye and Raspberry Pi BlueZ are still real BLE nodes; they are just not the canonical source of truth.

## Heltec combined-safe service path

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

## Primary RX event shape

Expected primary BLE RX events from the Heltec T114 nRF52840 should use this shape:

```json
{"type":"ble_adv_seen","device":"heltec-t114-nrf52840","source":"heltec-t114-nrf52840","role":"primary","transport":"usb-cdc","addr":"AA:BB:CC:DD:EE:FF","addr_type":"random","rssi":-61,"active_scan":false}
```

## Primary TX command shape

The Pi can activate a bounded, non-connectable owned-lab BLE beacon on the T114. This keeps action processing on the Pi while the nRF52840 performs the radio transmit action.

```json
{"type":"ble_lab_advertise_start","name":"KoalaByte Lab","duration_ms":30000,"confirm":true}
```

Stop command:

```json
{"type":"ble_lab_advertise_stop"}
```

TX status command:

```json
{"type":"ble_tx_status"}
```

The firmware blocks beacon start unless `confirm` is `true`, clamps duration, and uses a non-connectable advertisement. This is not a spoofing, pairing, GATT-write, replay, or disruptive path.

## Automated wrapper actions

The `scripts/run_t114_bluez.py` entrypoint now represents the KoalaByte wrapped BLE automation layer, not necessarily Linux HCI mode. In the default combined-safe profile:

```bash
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py controller-check
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py status
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py scan --duration-seconds 30
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py tx-status
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py lab-advertise-start --confirm-send --duration-seconds 30 --tx-name "KoalaByte Lab"
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py lab-advertise-stop
```

The Pi processes the action request, writes artifacts, and talks to the T114 over USB CDC JSON. The T114 nRF52840 is the primary BLE receiver/transmitter. ESP32-S3 BLE and Pi BlueZ remain secondary nodes.

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

`T114_PLUG_FLASH_PROFILE=hci-usb` is still available when you intentionally want the T114 to appear as a Linux HCI adapter. That is not the default because the default combined-safe profile keeps the nRF52840 firmware in charge of BLE RX/TX and communicates with the Pi through JSON.

## Safety boundary

Keep radio work lawful, local, owned-device, licensed, or explicitly in-scope. The default RX path is passive advertisement observation. The TX path is bounded, non-connectable, and explicitly Pi-confirmed for owned-lab beacon/status use only.
