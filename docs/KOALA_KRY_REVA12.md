# RevA12 Koala Kry

**Koala Kry** is the saved-metadata replay simulator for KoalaByte Blue.

It reads files produced by **Koala Kapture** and writes local replay events for the KoalaByte UI, reports, `eucalyptus`, Urban Poaching, and XP testing.

Koala Kry does not transmit BLE advertisements or RF traffic. It is offline metadata replay only.

## Input folder

```text
/blecaptures/koala_kapture/
```

## Output folder

```text
logs/koala_kry_replay/
```

## Run latest saved session

```bash
cd pi-companion
source .venv/bin/activate
PYTHONPATH=. python ../scripts/run_koala_kry.py
```

## Run a specific file

```bash
PYTHONPATH=. python ../scripts/run_koala_kry.py --input /blecaptures/koala_kapture/koala_kapture_YYYYMMDD_HHMMSS.jsonl
```

## Set playback speed

```bash
PYTHONPATH=. python ../scripts/run_koala_kry.py --speed 5.0
```

## Supported files

```text
.jsonl
.json
.csv
```

Default reward: 5 XP for a successful saved-session replay.
