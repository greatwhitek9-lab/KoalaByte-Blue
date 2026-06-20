# Didgeridoo LoRa / Meshtastic GNSS Node Setup — Phase 1

Didgeridoo is the KoalaByte Blue setup layer for the **Heltec Wireless Tracker V2** USB-C Meshtastic LoRa/GNSS node.

The preferred KoalaByte Blue wiring is:

```text
Raspberry Pi 3B+ USB-A port
   → short USB-A to USB-C data cable
   → Heltec Wireless Tracker V2 USB-C port
```

The six KoalaByte Blue front buttons stay on the 40-pin GPIO ribbon/breakout. The Heltec Wireless Tracker V2 does **not** need Raspberry Pi GPIO pins when it is used over USB serial, TCP, or BLE through the official Meshtastic CLI.

Phase 1 is deliberately limited to hardware setup, local checks, dependency installation, menu visibility, a Meshtastic connection profile, node information, and GNSS-readiness notes. It does not add raw radio sending features.

## Meshtastic compatibility

KoalaByte Blue treats Didgeridoo as a Meshtastic-node control/setup layer:

1. **Primary path — USB-C Meshtastic GNSS node**: plug the Heltec Wireless Tracker V2 into the Pi with a USB-A to USB-C data cable. The node should appear as `/dev/ttyUSB*` or `/dev/ttyACM*`.
2. **Secondary path — BLE Meshtastic node**: pair/configure the node from the Meshtastic phone app, then let KoalaByte Blue connect to the same node using the saved Didgeridoo BLE profile.
3. **Optional/legacy path — direct bare SX1262 SPI radio**: kept as documentation only for future lab experiments. It is not the preferred KoalaByte Blue build path anymore.

Meshtastic does not use a normal web-app username/password login for this local CLI workflow. Didgeridoo's `meshtastic-login` command saves a local connection profile so KoalaByte Blue knows which Meshtastic node to talk to.

No channel URL, PSK, password, private key, or QR-code secret is stored by this Phase 1 profile.

## Hardware target

- Board: Heltec Wireless Tracker V2 / USB-C Meshtastic LoRa GNSS node
- Host: Raspberry Pi 3B+
- Connection: USB-A to USB-C **data** cable
- Pi GPIO usage: none for LoRa/Meshtastic node mode
- Core radio: SX1262 LoRa transceiver on the Heltec board
- GNSS: UC6580 GNSS receiver on the Heltec board
- GNSS systems: GPS, GLONASS, BDS, Galileo, NAVIC, and QZSS support through the Heltec GNSS hardware
- LoRa antenna: board-matched LoRa antenna connected to the Heltec board's LoRa IPEX/U.FL antenna connector
- 2.4 GHz antenna: the Wireless Tracker has an onboard Wi-Fi/Bluetooth 2.4 GHz metal spring antenna; do not assume it needs a second external 2.4 GHz pigtail unless the exact board revision provides and documents one
- ESP32-S3 antenna: separate 2.4 GHz antenna connected to the ESP32-S3 DualEye IPEX1/U.FL path

Detailed antenna-hole placement and enclosure geometry are maintained in the production package, not in this Didgeridoo software/setup guide.

## Antenna and GNSS connection rules

Do **not** connect a 2.4 GHz antenna to the LoRa antenna connector.
Do **not** connect the LoRa antenna to any 2.4 GHz antenna connector.
Do **not** share one antenna between the Heltec board and the ESP32-S3 DualEye.
Do **not** power or use the LoRa node without its correct LoRa antenna attached.

For GNSS, the board may use its onboard GNSS antenna path by default. If the build uses an external GNSS antenna, follow the Heltec hardware documentation for switching to the GNSS IPEX/U.FL antenna path and keep that mechanical detail in the production package.

## USB wiring

```text
Raspberry Pi 3B+ USB-A
   → short USB-A to USB-C data cable
   → USB-C Heltec Wireless Tracker V2
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

SPI support remains optional for future direct-SX1262 lab work, but it is not required when using the Heltec Wireless Tracker V2 as a full USB-C Meshtastic node.

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

1. Flash/configure the Heltec Wireless Tracker V2 with the correct Meshtastic firmware for its hardware target and LoRa region.
2. Pair/configure the node with the phone app over Bluetooth.
3. Confirm the node's LoRa region/frequency, LoRa antenna, and GNSS location behavior are correct.
4. Move outdoors or near a window for first GNSS fix if needed.
5. Disconnect or close the phone app if the node supports only one active client connection.
6. Connect KoalaByte Blue to the node by USB serial, TCP, or BLE using Didgeridoo.

## GNSS note

The Heltec Wireless Tracker V2 is the preferred KoalaByte Blue Didgeridoo node when GPS/GNSS is required because it includes UC6580 GNSS hardware. GNSS fixes still require suitable sky view, correct firmware support, and correct antenna configuration.

## Phase 1 boundaries

Included:

- Didgeridoo menu entry
- LoRa / Mesh Tools menu group
- Meshtastic Python/CLI dependency
- Local status and manifest artifacts
- Local Meshtastic connection profile / login helper
- Meshtastic node info checks
- Heltec Wireless Tracker V2 USB-C wiring guidance
- GNSS-readiness guidance

Not included yet:

- Raw SX1262 message sending
- Meshtastic message sending
- Automatic radio actions
- Background radio service

Those can be added later as a separately reviewed Phase 2 once the hardware is installed and validated.
