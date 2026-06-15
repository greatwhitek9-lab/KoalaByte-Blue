# RevA23 Koala Kan Kommander - InnoMaker USB-to-CAN Update

## Purpose

Koala Kan Kommander adds an optional physical CAN observation path for KoalaByte Blue using the user-specified **InnoMaker USB to CAN Converter kit** as the USB-to-CAN adapter.

It is designed for authorized bench, training, and owned-device CAN observation. The production plug-in is passive by default and does not implement raw CAN frame transmission.

## Physical device option

Recommended physical path:

```text
Raspberry Pi 3B+ USB host
  -> short internal USB cable
  -> InnoMaker USB to CAN Converter kit
  -> adapter-side CAN_H / CAN_L / GND / optional SHIELD
  -> authorized bench harness or owned-device test network
```

Do not wire CAN_H or CAN_L directly to Raspberry Pi GPIO. Use the InnoMaker adapter as the CAN controller/transceiver path.

## Mechanical update

RevA23 removes the earlier circular CAN panel port. Mount the InnoMaker converter internally or in a side/rear rectangular service bay and provide cable strain relief. Keep it clear of antennas, batteries, speaker grille, and the Pi GPIO header.

## Connector lines

```text
CAN_H
CAN_L
GND
optional SHIELD
```

Use the adapter-side connection supplied by the selected InnoMaker kit/listing. Do not create a direct Pi GPIO CAN wiring path.

## Menu entry

The menu option is named:

```text
Koala Kan Kommander
```

The command key is:

```text
koala_kan_kommander
```

## Runner

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py status --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py listen --interface can0 --duration 10
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py report --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py transmit-placeholder
```

## Supported actions

| Action | Behavior |
|---|---|
| `manifest` | Writes the plug-in manifest with the InnoMaker adapter path. |
| `inventory` | Detects SocketCAN interfaces under `/sys/class/net`. |
| `status` | Saves `ip -details -statistics link show <interface>` output. |
| `listen` | Performs a bounded passive raw-socket CAN listen and saves JSON artifacts. |
| `report` | Writes a Markdown report with inventory/status artifact links. |
| `transmit-placeholder` | Writes a blocked-action artifact. No CAN frame is sent. |

## Optional Pi setup

Most USB-to-CAN adapters expose a SocketCAN interface such as `can0`. Useful host commands:

```bash
sudo apt install -y can-utils iproute2
ip link show
sudo ip link set can0 up type can bitrate 500000
ip -details -statistics link show can0
```

Use the bitrate required by your authorized bench harness or owned-device test network.

## Safety boundary

Koala Kan Kommander is for authorized CAN observation and bench validation only. The production plug-in does not transmit raw CAN frames. Vehicle networks, industrial controllers, batteries, and embedded control networks must be treated as high-risk systems; observe only unless you fully own the test harness and have documented scope.