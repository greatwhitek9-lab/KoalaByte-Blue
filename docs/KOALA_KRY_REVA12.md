# RevA16 Koala Kry

**Koala Kry** is the saved-metadata replay simulator for KoalaByte Blue.

It reads files produced by **Koala Kapture** and writes local replay events for the KoalaByte UI, reports, `eucalyptus`, Urban Poaching, and XP testing.

Koala Kry does **not** transmit BLE advertisements or RF traffic. Captured Bluetooth/RF over-the-air replay remains intentionally blocked. RevA16 changes the old transmit-request review into an **RF bench review** path that writes isolation, authorization, equipment, monitoring, and stop-condition notes for a separate compliant lab setup.

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

## Write RF bench review manifest

This command does not send RF. It records that an RF bench review was requested and writes a manifest with scope, isolation controls, equipment notes, monitoring expectations, and safe next steps.

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kry.py --request-rf-transmit --lab-setting --owned-device
```

Optional review-only mode:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kry.py --write-transmit-review --lab-setting --owned-device
```

Review output:

```text
logs/koala_kry_replay/koala_kry_rf_bench_review_YYYYMMDD_HHMMSS.json
```

## RF bench review fields

The review manifest includes:

```text
action
status
rf_transmission=false
policy
lab_setting_ack
owned_device_ack
allowed_next_steps
blocked_actions
required_lab_controls
review_notes
```

## Safe lab alternatives

Allowed next steps are documented in the review manifest:

```text
Use Koala Kry offline replay for UI/parser/report/XP testing.
Document shielding, attenuation, dummy-load use, monitoring, and stop conditions.
Use certified RF test equipment or vendor SDK examples only within a compliant isolated test setup.
Create fresh synthetic lab payloads instead of replaying captured signals.
```

## Supported files

```text
.jsonl
.json
.csv
```

Default reward: 5 XP for a successful saved-session replay.
