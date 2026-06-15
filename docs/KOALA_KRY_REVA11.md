# RevA12 Koala Kry

**Koala Kry** is now the saved-metadata session player for KoalaByte Blue.

It reads files produced by **Koala Kapture** and writes local test events for the KoalaByte UI, reports, `eucalyptus`, Urban Poaching, and XP testing.

Input folder:

```text
/blecaptures/koala_kapture/
```

Output folder:

```text
logs/koala_kry_replay/
```

Run latest saved session:

```bash
cd pi-companion
source .venv/bin/activate
PYTHONPATH=. python ../scripts/run_koala_kry.py
```

Run a specific file:

```bash
PYTHONPATH=. python ../scripts/run_koala_kry.py --input /blecaptures/koala_kapture/koala_kapture_YYYYMMDD_HHMMSS.jsonl
```

Set playback speed:

```bash
PYTHONPATH=. python ../scripts/run_koala_kry.py --speed 5.0
```

Default reward: 5 XP for a successful saved-session run.
