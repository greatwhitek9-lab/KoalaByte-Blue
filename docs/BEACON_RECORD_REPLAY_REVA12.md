# RevA12 Beacon Record & Replay Simulator

## What it is

**Beacon Record & Replay Simulator** is a local metadata replay action for KoalaByte Blue. It reads previously captured BLE observation records from `eucalyptus`, Koala Kry, or other local capture exports and replays them into a local test-feed file.

It is designed for:

- UI testing.
- Parser testing.
- Report generation tests.
- XP/leveling tests.
- Demonstrating how the companion reacts to known capture data.

## Safety boundary

This action does not transmit BLE packets and does not interact with BLE devices. It only reads existing metadata files and writes replayed metadata to local logs.

## Supported input formats

```text
.jsonl
.json
.csv
```

Common fields are normalized when present:

```text
timestamp, address, mac, name, local_name, rssi, signal
```

## Output

Default replay output directory:

```text
logs/beacon_replay/
```

Each run creates:

```text
beacon_replay_YYYYMMDD_HHMMSS.jsonl
beacon_replay_YYYYMMDD_HHMMSS_summary.json
```

## Run

From the repository root on the Raspberry Pi:

```bash
cd pi-companion
source .venv/bin/activate
PYTHONPATH=. python ../scripts/run_metadata_replay.py --input /blecaptures/example.jsonl
```

Replay faster than original timing:

```bash
PYTHONPATH=. python ../scripts/run_metadata_replay.py --input /blecaptures/example.jsonl --speed 20
```

Replay immediately without timing delays:

```bash
PYTHONPATH=. python ../scripts/run_metadata_replay.py --input /blecaptures/example.jsonl --no-timing
```

Limit replay size:

```bash
PYTHONPATH=. python ../scripts/run_metadata_replay.py --input /blecaptures/example.jsonl --max-records 100
```

## XP

Default reward is 5 XP for completing a valid replay run.
