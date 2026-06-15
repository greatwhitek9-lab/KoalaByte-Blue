# RevA15 Koala Kry

**Koala Kry** is the saved-metadata replay simulator for KoalaByte Blue.

It reads files produced by **Koala Kapture** and writes local replay events for the KoalaByte UI, reports, `eucalyptus`, Urban Poaching, and XP testing.

Koala Kry does **not** transmit BLE advertisements or RF traffic. Captured Bluetooth/RF over-the-air replay is intentionally blocked. RevA15 adds a safe transmit-request review path that writes a manifest explaining why RF replay was not performed and what safe owned-device lab options remain available.

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
PYTHONPATH=pi-companion python3 scripts/run_koala_kry.py
```

## Run a specific file

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kry.py --input /blecaptures/koala_kapture/koala_kapture_YYYYMMDD_HHMMSS.jsonl
```

## Set playback speed

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kry.py --speed 5.0
```

## Request RF transmit review manifest

This command does not send RF. It records that a transmit/replay request was made, blocks it, and writes a review manifest with safe next steps.

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kry.py --request-rf-transmit --lab-setting --owned-device
```

Optional review-only mode:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kry.py --write-transmit-review --lab-setting --owned-device
```

Review output:

```text
logs/koala_kry_replay/koala_kry_transmit_review_YYYYMMDD_HHMMSS.json
```

## Safe lab alternatives

Allowed next steps are documented in the review manifest:

```text
Use Koala Kry offline replay for UI/parser/report/XP testing.
Use Ear Tag or vendor SDK examples for owned-device synthetic BLE lab advertisements.
Create a fresh clearly named lab advertisement payload instead of replaying a captured signal.
```

## Supported files

```text
.jsonl
.json
.csv
```

Default reward: 5 XP for a successful saved-session replay.
