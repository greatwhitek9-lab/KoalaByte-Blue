# Didgeridoo LoRa / Meshtastic Node Setup — Phase 1

Didgeridoo is the KoalaByte Blue setup layer for a **USB-C Meshtastic LoRa node board**, with the current target being a Heltec-style Meshtastic board that has both a LoRa antenna connection and a separate 2.4 GHz antenna connection.

The preferred KoalaByte Blue wiring is:

```text
Raspberry Pi 3B+ USB-A port
   → short USB-A to USB-C data cable
   → Heltec / Meshtastic LoRa node board USB-C port
```

The six KoalaByte Blue front buttons stay on the 40-pin GPIO ribbon/breakout. The Meshtastic LoRa board does **not** need Raspberry Pi GPIO pins when it is used over USB serial, TCP, or BLE through the official Meshtastic CLI.

Phase 1 is deliberately limited to hardware setup, local checks, dependency installation, menu visibility, a Meshtastic connection profile, and Meshtastic node information. It does not add raw radio sending features.

## Meshtastic compatibility

KoalaByte Blue treats Didgeridoo as a Meshtastic-node control/setup layer:

1. **Primary path — USB-C Meshtastic node board**: plug the board into the Pi with a USB-A to USB-C data cable. The node should appear as `/dev/ttyUSB*` or `/dev/ttyACM*`.
2. **Secondary path — BLE Meshtastic node**: pair/configure the node from the Meshtastic phone app, then let KoalaByte Blue connect to the same node using the saved Didgeridoo BLE profile.
3. **Optional/legacy path — direct bare SX1262 SPI radio**: kept as documentation only for future lab experiments. It is not the preferred KoalaByte Blue build path anymore.

Meshtastic does not use a normal web-app username/password login for this local CLI workflow. Didgeridoo's `meshtastic-login` command saves a local connection profile so KoalaByte Blue knows which Meshtastic node to talk to.

No channel URL, PSK, password, private key, or QR-code secret is stored by this Phase 1 profile.

## Hardware target

- Board: USB-C Heltec / Meshtastic LoRa node board
- Host: Raspberry Pi 3B+
- Connection: USB-A to USB-C **data** cable
- Pi GPIO usage: none for LoRa/Meshtastic node mode
- Heltec LoRa antenna: board-matched LoRa antenna connected to the Heltec node's LoRa antenna connector
- Heltec 2.4 GHz antenna: 2.4 GHz Wi-Fi/Bluetooth antenna connected to the Heltec board's 2.4 GHz antenna connector, if fitted
- ESP32-S3 antenna: separate 2.4 GHz antenna connected to the ESP32-S3 DualEye IPEX1/U.FL path

Detailed antenna-hole placement and enclosure geometry are maintained in the production package, not in this Didgeridoo software/setup guide.

## Antenna connection rules

Do **not** connect a 2.4 GHz antenna to the LoRa antenna connector.
Do **not** connect the LoRa antenna to either 2.4 GHz antenna connector.
Do **not** share one antenna between the Heltec 2.4 GHz connector and the ESP32-S3 DualEye.
Do **not** power or use the LoRa node without its correct LoRa antenna attached.

## USB wiring

```text
Raspberry Pi 3B+ USB-A
   → short USB-A to USB-C data cable
   → USB-C Heltec / Meshtastic LoRa node
```

After plugging it in, check:

```bash
lsusb
ls /dev/ttyUSB*
ls /dev/ttyACM*
```

Common serial ports:

```text
/dev/ttyUSB0
/dev/ttyACM0
```

## Existing six button map

The six buttons remain on the 40-pin GPIO cable and do not conflict with the USB Meshtastic node.

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

The normal KoalaByte Blue helper already runs system package setup and then the Pi companion installer. Phase 1 adds the Meshtastic CLI dependency to that flow so a normal install can prepare the Pi for Didgeridoo.

```bash
bash scripts/flash_all_components.sh --all
```

SPI support remains optional for future direct-SX1262 lab work, but it is not required when using a full USB-C Meshtastic node board.

## Local Didgeridoo checks

```bash
PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py manifest
PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py status
```

## Meshtastic login profiles

USB serial node:

```bash
PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py meshtastic-login --connection serial --port /dev/ttyUSB0 --verify
```

Alternative USB CDC serial node:

```bash
PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py meshtastic-login --connection serial --port /dev/ttyACM0 --verify
```

TCP/network node:

```bash
PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py meshtastic-login --connection tcp --host meshtastic.local --verify
```

BLE node:

```bash
PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py meshtastic-login --connection ble --ble "device_name_or_address" --verify
```

Show the saved profile:

```bash
PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py meshtastic-profile
```

Clear the saved profile:

```bash
PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py meshtastic-logout
```

Query the logged-in node:

```bash
PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py meshtastic-info
```

The Meshtastic info command only queries a connected Meshtastic node. It does not send a mesh text message.

## Phone app workflow

The Meshtastic phone app and KoalaByte Blue both talk to the Meshtastic node. The phone is not the LoRa radio for KoalaByte Blue.

Typical workflow:

1. Pair/configure the Meshtastic node with the phone app over Bluetooth.
2. Confirm the node's region/frequency and all antennas are correct.
3. Disconnect or close the phone app if the node supports only one active client connection.
4. Connect KoalaByte Blue to the node by USB serial, TCP, or BLE using Didgeridoo.

## GPS note

The USB-C Meshtastic node may support GPS only if that specific board includes a GNSS/GPS receiver or accepts an external GPS module. The LoRa radio chip itself is not GPS.

Look for board/listing terms such as:

- GPS
- GNSS
- L76K
- LC76G
- NEO-6M
- NEO-M8N
- ATGM336H
- PPS

If the node has no GPS, it can still use phone-provided location, fixed position settings, or an external GPS module depending on the board and Meshtastic configuration.

## Phase 1 boundaries

Included:

- Didgeridoo menu entry
- LoRa / Mesh Tools menu group
- Meshtastic Python/CLI dependency
- Local status and manifest artifacts
- Local Meshtastic connection profile / login helper
- Meshtastic node info checks
- USB-C Meshtastic node wiring guidance

Not included yet:

- Raw SX1262 message sending
- Meshtastic message sending
- Automatic radio actions
- Background radio service

Those can be added later as a separately reviewed Phase 2 once the hardware is installed and validated.
