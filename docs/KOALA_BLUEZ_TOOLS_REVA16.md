# RevA16 Koala BlueZ Tools

## Purpose

Koala BlueZ Tools gives KoalaByte Blue safe, KoalaByte-named wrappers around common local BlueZ command-line tools on Raspberry Pi OS.

The wrappers focus on:

- Local adapter inventory
- Local adapter status
- Timed discovery
- Timed HCI monitor logging
- Owned-device diagnostics that require explicit target and `--owned-device`

They do not perform pairing bypass, spoofing, disruptive actions, or captured-packet replay.

## Main runner

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py status
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py scan --duration 15
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py monitor --duration 20
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py all-safe --duration 15
```

## Convenience scripts

```bash
bash scripts/run_koala_bluez_inventory.sh
bash scripts/run_koala_bluez_status.sh
bash scripts/run_koala_bluez_scan.sh --duration 15
bash scripts/run_koala_bluez_monitor.sh --duration 20
```

## KoalaByte names

| KoalaByte name | BlueZ/backend command | Purpose |
|---|---|---|
| Koala Blue Controller | bluetoothctl | Adapter power, discovery, controller status |
| Koala Blue Manager | btmgmt | Controller management/status |
| Koala Blue Monitor | btmon | Local HCI monitor logging |
| Koala Blue Radio List | hciconfig | Local adapter identity/status when installed |
| Koala Blue Classic List | hcitool | Legacy scan/inquiry support when installed |
| Koala Blue Blocker Status | rfkill | Bluetooth soft/hard block status |
| Koala Blue RFCOMM Status | rfcomm | Local RFCOMM binding/status |
| Koala Blue Service Notes | sdptool | Owned-device service browsing only |
| Koala Blue Link Echo | l2ping | Owned-device link echo only |
| Koala Blue GATT Notes | gatttool | Legacy owned-device GATT notes when installed |

## Menu entries

The main menu now lists:

```text
Koala BlueZ Inventory
Koala BlueZ Status
Koala BlueZ Scan
Koala BlueZ Monitor
```

## Output

Output is written to:

```text
logs/koala_bluez/
```

Typical files:

```text
koala_bluez_inventory.json
koala_bluez_status_<timestamp>.json
koala_bluez_scan_<timestamp>.json
koala_bluez_monitor_<timestamp>.json
koala_bluez_btmon_<timestamp>.log
```

## Target-specific diagnostics

Target-specific actions require both an explicit target and `--owned-device`:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py info --target AA:BB:CC:DD:EE:FF --owned-device
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py services --target AA:BB:CC:DD:EE:FF --owned-device
```

## Install notes

Install core packages on Raspberry Pi OS:

```bash
sudo apt update
sudo apt install -y bluetooth bluez rfkill
```

Some older BlueZ utilities are deprecated and may not exist on every OS image. The inventory action records which commands are actually present.
