# RevA22 Koala Kan Kommander

## Purpose

Koala Kan Kommander adds an optional physical CAN-bus plug-in path for KoalaByte Blue using a SocketCAN-compatible USB-to-CAN adapter.

It is designed for authorized bench, training, and owned-device CAN observation. The production plug-in is passive by default and does not implement raw CAN frame transmission.

## Physical device option

Recommended physical path:

```text
SocketCAN-compatible USB-to-CAN adapter
  -> short internal USB cable to Raspberry Pi 3B+
  -> case-mounted CAN connector
  -> CAN_H / CAN_L / GND / optional SHIELD
```

Do not wire CAN_H or CAN_L directly to Raspberry Pi GPIO. Use a proper USB-to-CAN adapter or a CAN controller plus transceiver module.

## Connector lines

```text
CAN_H
CAN_L
GND
optional SHIELD
optional adapter-side power only when the selected adapter requires it
```

For KoalaByte Blue, the cleanest enclosure option is a rear or side-panel connector connected to a USB-to-CAN adapter mounted inside the case.

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
| `manifest` | Writes the plug-in manifest. |
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
