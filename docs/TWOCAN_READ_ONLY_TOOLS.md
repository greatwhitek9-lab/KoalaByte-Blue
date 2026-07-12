# TwoCan Read-Only Tools

TwoCan Read-Only Tools is an executable submenu under:

```text
Main Canopy -> CAN Bench Tools -> Koala Kan Kommander -> TwoCan Read-Only Tools
```

It is intended only for a vehicle you own or are explicitly authorized to diagnose. Use an ELM327-compatible OBD-II adapter for the live diagnostic actions. The optional InnoMaker USB-CAN adapter remains part of the isolated Koala Kan bench workflow and is not the default vehicle-diagnostics adapter.

## Control methods

Every enabled TwoCan row uses the shared KoalaByte menu action path and can be selected by:

- KillerKoala voice command
- Touchscreen selection
- K1-K8 front-panel button board
- USB or Bluetooth keyboard

Voice format:

```text
killerkoala run <menu label>
killerkoala open <menu label>
```

Examples:

```text
killerkoala run Stored DTC Report
killerkoala run Readiness Monitors
killerkoala run Live PID Snapshot
killerkoala run Offline CAN Capture Review
killerkoala run Repair Verification Checklist
```

Button and keyboard navigation use the same menu rows:

```text
K1 Main Menu
K2 Left / Back
K3 Enter / Select
K4 Right / Forward
K5 Up
K6 Down

Keyboard arrows or W/A/S/D move
Enter selects
Backspace or Left returns
```

## Executable submenu actions

| Menu item | Action |
|---|---|
| Run Full Read-Only Scan | Runs the supported read-only identity, DTC, freeze-frame, readiness, live snapshot, offline review, and checklist actions and writes a combined report. |
| Adapter Identity | Reads the ELM adapter version, detected voltage, serial port, connection state, and selected protocol. |
| Vehicle VIN and Calibration | Reads standard VIN, calibration ID, and calibration verification number data when supported. |
| Stored DTC Report | Reads confirmed emission-related diagnostic trouble codes. It does not clear them. |
| Pending DTC Report | Reads pending codes from the current or last completed drive cycle. |
| Permanent DTC Report | Sends the standard read-only service `0A` request for permanent emission-related codes. |
| Freeze-Frame Snapshot | Reads the DTC that triggered freeze-frame storage and supported Mode 02 PID values. |
| Readiness Monitors | Reads monitor status since the last clear and monitor status for the current drive cycle. |
| Live PID Snapshot | Reads one bounded snapshot of supported standard PIDs such as RPM, speed, temperatures, load, MAF, throttle, fuel level, and control-module voltage. |
| Live PID Log 30 Seconds | Logs supported standard live PIDs for a bounded interval. The duration can be adjusted through `KOALABYTE_TWOCAN_LIVE_SECONDS`, with a maximum of 300 seconds. |
| Offline CAN Capture Review | Summarizes a saved JSON, candump, log, or text capture. It never transmits or replays the capture. |
| Repair Verification Checklist | Writes a pre-repair and post-repair checklist artifact. |
| Clear Codes Safety Note | Writes the existing safety workflow note without sending a reset command. |

Artifacts are written under:

```text
logs/twocan_vehicle_diagnostics/
```

## CLI use

```bash
cd ~/KoalaByte-Blue

PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py adapter
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py identity
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py stored-dtcs
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py pending-dtcs
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py permanent-dtcs
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py freeze-frame
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py readiness
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py live-snapshot
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py live-log --duration 30 --interval 1
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py capture-review --capture /path/to/saved-capture.log
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py repair-checklist
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py full
```

Set a specific adapter path when auto-detection is not appropriate:

```bash
KOALABYTE_OBD_PORT=/dev/ttyUSB0 \
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py stored-dtcs
```

## Safety boundary

TwoCan Read-Only Tools does not include or automate:

- DTC clearing or reset service 04
- ECU coding, adaptation, or programming
- Actuator or output tests
- UDS security access
- Seed/key workflows
- OEM-specific raw-frame injection
- Captured traffic replay
- Synthetic ECU or UDS simulators

The live actions send only explicitly allowlisted read-only OBD-II requests. Offline capture review parses local saved artifacts and never opens a transmit or replay path.

## Readiness check

```bash
PYTHONPATH=pi-companion python3 scripts/check_twocan_read_only.py
bash scripts/check_deployability.sh
```
