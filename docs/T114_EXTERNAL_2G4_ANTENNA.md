# Heltec T114 external 2.4 GHz antenna notes

The Heltec T114 has separate RF paths. Do not mix up the 2.4 GHz BLE antenna path and the LoRa antenna path.

## Default handling

The canonical helper assumes the safe physical connector path by default:

```bash
T114_2G4_ANTENNA=connector bash scripts/configure_t114_2g4_antenna.sh
```

This writes status to:

```text
logs/t114_2g4_antenna_status.json
```

## Important safety rule

Do not guess an RF-switch GPIO. Only use a GPIO overlay if you have the exact board schematic or board DTS confirming the RF switch line.

## Optional custom overlay

If the board revision has a confirmed RF switch overlay:

```bash
T114_ANTENNA_SWITCH_OVERLAY=/path/to/board_external_2g4.overlay \
  T114_2G4_ANTENNA=external \
  bash scripts/configure_t114_2g4_antenna.sh --print-export
```

## Optional generated overlay

Only use this if the GPIO controller and pin are confirmed:

```bash
T114_ANTENNA_SWITCH_GPIO_CONTROLLER=gpio0 \
T114_ANTENNA_SWITCH_GPIO_PIN=12 \
T114_ANTENNA_SWITCH_ACTIVE=high \
T114_2G4_ANTENNA=external \
bash scripts/configure_t114_2g4_antenna.sh --print-export
```

## Build integration

The T114 HCI USB build helper calls the antenna helper and passes an overlay to Zephyr only when a valid overlay path is produced.

```bash
T114_BOARD=heltec_t114_v2/nrf52840 T114_2G4_ANTENNA=connector \
  bash scripts/build_nrf52840_t114_hci_usb.sh
```

## Checklist

- 2.4 GHz BLE antenna goes to the 2.4 GHz antenna connector.
- LoRa antenna goes to the LoRa antenna connector.
- Do not solder random antenna wire to RF connectors.
- Do not transmit with a missing or wrong antenna on a radio path.
- Record any validated overlay and board revision in production notes.
