# Boomerang Camera Awareness Logger

**Boomerang** is the KoalaByte Blue camera-awareness action. A boomerang is an Aussie throwing tool that comes back to you; this action does the same with field notes by bringing manually recorded camera details back as organized local IDs, reports, and exports.

Boomerang is a public-awareness utility for documenting cameras that the operator personally observes or learns about from public sources.

It is intentionally **manual/public-observation only**.

When selected from the KoalaByte menu, Boomerang stays open until the operator chooses `quit`, `q`, `back`, or `menu`.

## KillerKoala verbal alerts

Boomerang fires three separate KillerKoala alerts:

| Event | Alert purpose |
|---|---|
| `boomerang_start` | Plays when Boomerang starts. |
| `camera_found` | Plays after a manually observed camera record is successfully saved. |
| `xp_gain` | Plays separately after killerkoala XP is awarded. |

The default lines are:

```text
boomerang_start: BOOMerang!
camera_found: Camera found and logged, mate. Boomerang tagged it clean.
xp_gain: killerkoala gained XP. Another notch in the gumtree.
```

Alerts always print and log to:

```text
logs/killerkoala/boomerang_alerts.jsonl
```

Spoken audio is **on by default** at KoalaByte startup and when running Boomerang directly. The startup wrapper and menu runner set `KOALABYTE_TTS=1` unless you override it.

Mute spoken alerts with:

```bash
KOALABYTE_TTS=0 bash scripts/koalabyte_blue_boot.sh
```

Boomerang will try `espeak-ng`, `espeak`, or `say` if available. Without a TTS engine, the alerts still appear on screen and in the alert log.

## XP reward

killerkoala earns **+10 XP** for every camera record successfully logged through Boomerang.

XP is awarded only after the record passes the manual/public-observation safety checks and is written to the local log. Rejected records do not earn XP.

Boomerang writes XP to:

```text
logs/killerkoala/xp_state.json
```

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
- Camera type label such as `unknown camera`, `traffic camera`, or `roadside camera`
- Mounting description and facing direction
- Local photo reference
- Notes
- Confidence level

## What it does not do

This tool does **not** electronically detect, scan, probe, fingerprint, or track cameras.

It does not collect:

- MAC addresses
- BSSID/SSID values
- IP addresses
- Bluetooth addresses
- RF fingerprints
- Probe responses
- Wardriving scan results
- Network scan output
- Route-planning data

The program rejects MAC-like values, IP addresses, and notes that mention network or RF identifiers.

## Menu appearance

Boomerang is a normal KoalaByte Blue menu item. It uses the same grouped menu system as the other actions, so it appears with the same eucalyptus border, jungle/Jumanji-style rounded system font choices, selected-item glow, green/yellow jungle colors, and touch/button navigation.

## Commands

Run Boomerang directly:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boomerang.py
```

Show schema and safety scope:

```bash
PYTHONPATH=pi-companion python3 scripts/run_camera_awareness_logger.py schema
```

Add a manual observation:

```bash
PYTHONPATH=pi-companion python3 scripts/run_camera_awareness_logger.py add \
  --label "Main St pole camera" \
  --type "roadside camera" \
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

Keep this logger limited to lawful public-awareness documentation and local record keeping.
