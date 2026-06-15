# RevA12 Koala Kapture

## What it is

**Koala Kapture** is the passive metadata recorder for KoalaByte Blue. It records BLE observation metadata from owned or written-scope lab devices and saves the data for later local analysis by Koala Kry.

## Output files

Koala Kapture writes:

```text
/blecaptures/koala_kapture/*.jsonl
/blecaptures/koala_kapture/*.csv
/blecaptures/koala_kapture/*_manifest.json
```

## Run

```bash
cd pi-companion
source .venv/bin/activate
PYTHONPATH=. python ../scripts/run_koala_kapture.py --duration-seconds 30
```

To record only the Ear Tag lab beacon:

```bash
PYTHONPATH=. python ../scripts/run_koala_kapture.py --target-name EarTag-Lab --duration-seconds 30
```

## Safety scope

Koala Kapture only saves metadata from passive observations. It does not connect, pair, write, disrupt, or transmit.
