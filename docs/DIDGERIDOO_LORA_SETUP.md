# Didgeridoo LoRa Setup — Phase 1

Didgeridoo is the KoalaByte Blue setup layer for the optional Semtech SX1262 / DX-LR30 433 MHz SPI LoRa board.

This Phase 1 integration is deliberately limited to hardware setup, local checks, dependency installation, SPI enablement, menu visibility, and Meshtastic node information. It does not add raw radio sending features.

## Hardware target

- Board: DX-LR30 / Semtech SX1262 SPI LoRa module
- Band: 410–475 MHz / 433 MHz module variant
- Raspberry Pi: Raspberry Pi 3B+
- Connection: 40-pin GPIO breakout over SPI0
- Antenna: 433 MHz antenna attached to the SX1262 SMA connector before the board is powered for radio use

## GPIO map

The six KoalaByte Blue front buttons stay on their existing GPIO pins. Didgeridoo uses SPI0 and three control pins that do not overlap the button layout.

| DX-LR30 / SX1262 pin | Raspberry Pi signal | Physical pin |
|---|---|---:|
| SCK / SCLK | GPIO11 / SPI0 SCLK | 23 |
| MISO / SDO | GPIO9 / SPI0 MISO | 21 |
| MOSI / SDI | GPIO10 / SPI0 MOSI | 19 |
| NSS / CS / NSEL | GPIO8 / SPI0 CE0 | 24 |
| RESET / NRST | GPIO22 | 15 |
| BUSY | GPIO24 | 18 |
| DIO1 / IRQ | GPIO25 | 22 |
| GND | Ground | 20 or 25 |
| VCC | 3.3V if the board header is marked 3V3; VIN/5V only if the carrier board label explicitly supports it | 17 for 3.3V |

## Existing six button map

| Button | Function | GPIO | Physical pin |
|---:|---|---:|---:|
| 1 | Main Menu | GPIO5 | 29 |
| 2 | Move Left / Back | GPIO6 | 31 |
| 3 | Enter / Select | GPIO13 | 33 |
| 4 | Move Right / Forward | GPIO19 | 35 |
| 5 | Up | GPIO26 | 37 |
| 6 | Down | GPIO21 | 40 |

All button grounds share a ground bus, usually physical pin 39.

## Flash/install behavior

The normal KoalaByte Blue helper already runs system package setup and then the Pi companion installer. Phase 1 adds SPI/Meshtastic dependencies to that flow so a normal install can prepare the Pi for Didgeridoo.

```bash
bash scripts/flash_all_components.sh --all
```

The setup helper enables the Pi SPI interface when `raspi-config` is available. Reboot after first install if `/dev/spidev0.0` does not appear immediately.

## Local checks

```bash
PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py manifest
PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py status
PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py meshtastic-info --port /dev/ttyUSB0
```

The Meshtastic info command only queries a connected Meshtastic node. It does not send a mesh text message.

## Phase 1 boundaries

Included:

- Didgeridoo menu entry
- LoRa / Mesh Tools menu group
- SPI package dependency
- Meshtastic Python dependency
- Pi SPI enablement helper
- Local status and manifest artifacts
- Meshtastic node info checks

Not included yet:

- Raw SX1262 message sending
- Meshtastic message sending
- Automatic radio actions
- Background radio service

Those can be added later as a separately reviewed Phase 2 once the hardware is installed and validated.
