# RevA11 Koala Kry

## What it is

**Koala Kry** is a local synthetic BLE log generator for KoalaByte Blue. It creates realistic-looking test records so the companion UI, parsers, report generation, XP hooks, and `eucalyptus` import workflow can be stress-tested without transmitting radio traffic.

## What it does

Koala Kry writes local test files:

```text
logs/koala_kry/*.jsonl
logs/koala_kry/*.csv
logs/koala_kry/*_summary.json
```

The records include fields similar to passive BLE observations:

```text
timestamp, address, name, rssi, connectable, source, note
```

## Safety boundary

Koala Kry does **not** transmit BLE advertisements and does **not** create RF interference. It is local synthetic test data only.

## Run

From the repository root on the Raspberry Pi:

```bash
cd pi-companion
source .venv/bin/activate
PYTHONPATH=. python ../scripts/run_koala_kry.py --samples 250 --device-count 40
```

For repeatable test data:

```bash
PYTHONPATH=. python ../scripts/run_koala_kry.py --samples 250 --device-count 40 --seed 1337
```

## Recommended use

Use Koala Kry before live lab testing to verify:

- BLE table rendering.
- Log parsing.
- CSV export.
- Report generation.
- XP reward hooks.
- `eucalyptus` style capture workflow handling.

## XP

Default reward is 5 XP for generating a valid synthetic dataset.
