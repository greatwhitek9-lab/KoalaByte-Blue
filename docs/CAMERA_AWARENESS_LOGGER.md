# Camera Awareness Logger

The Camera Awareness Logger is a KoalaByte Blue public-awareness utility for documenting cameras that the operator personally observes or learns about from public sources.

It is intentionally **manual/public-observation only**.

## What it does

The logger stores rich, non-network identity details so manually found cameras are easier to track over time:

- Local observation ID
- Local asset ID
- UTC timestamp
- Location text
- Optional latitude/longitude entered by the operator
- Public agency or public source URL
- Visible pole, mount, or asset markings
- Visible make/model, if known from the housing/signage/public source
- Camera type label such as `unknown camera`, `traffic camera`, or `ALPR-style camera`
- Mounting description and facing direction
- Local photo reference
- Notes
- Confidence level

## What it does not do

This tool does **not** detect, scan, probe, fingerprint, or track cameras electronically.

It does not collect:

- MAC addresses
- BSSID/SSID values
- IP addresses
- Bluetooth addresses
- RF fingerprints
- Probe responses
- Wardriving scan results
- Network scan output
- Avoidance/evasion routing data

The program rejects MAC-like values, IP addresses, and notes that mention network/RF/evasion identifiers.

## Commands

Show schema and safety scope:

```bash
PYTHONPATH=pi-companion python3 scripts/run_camera_awareness_logger.py schema
```

Add a manual observation:

```bash
PYTHONPATH=pi-companion python3 scripts/run_camera_awareness_logger.py add \
  --label "Main St pole camera" \
  --type "ALPR-style camera" \
  --location "Main St / 1st Ave" \
  --confidence medium \
  --public-agency "Example City public works" \
  --visible-markings "utility pole tag visible from sidewalk" \
  --pole-or-mount-id "pole tag shown publicly" \
  --visible-make-model "unknown" \
  --mounting-description "mast arm above roadway" \
  --facing-direction "northbound" \
  --photo-reference "local_photo_reference_only.jpg" \
  --notes "Observed from public sidewalk; no RF or network probing performed."
```

List observations:

```bash
PYTHONPATH=pi-companion python3 scripts/run_camera_awareness_logger.py list
```

Export reports:

```bash
PYTHONPATH=pi-companion python3 scripts/run_camera_awareness_logger.py export --format both
```

Default outputs:

```text
logs/camera_awareness/observations.jsonl
logs/camera_awareness/camera_awareness_report.json
logs/camera_awareness/camera_awareness_report.csv
```

## Safe identity fields

Use fields that come from lawful personal observation or public records:

| Field | Safe example |
|---|---|
| `label` | `Main St pole camera` |
| `location` | `Main St / 1st Ave` |
| `public-agency` | `Example City public works` |
| `public-source-url` | Public meeting agenda, public inventory, public notice |
| `visible-markings` | Visible pole tag or public sticker text |
| `pole-or-mount-id` | Publicly visible pole or mounting identifier |
| `public-asset-tag` | Public asset/permit tag visible from lawful vantage point |
| `visible-make-model` | Housing/signage/public-source make/model only |
| `photo-reference` | Local file reference without face/license-plate details |

Do not use this logger for covert camera discovery, real-time avoidance, network targeting, RF targeting, or device exploitation.
