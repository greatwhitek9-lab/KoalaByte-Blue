# RevA15 Capture, Replay, and Menu Update

## Naming

```text
eucalyptus            = always-on passive BLE observation/logger
Koala Kapture         = passive BLE metadata capture and archive
Koala Kry             = offline replay of Koala Kapture metadata
Koala Kry RF Review   = safe review manifest path; no radio output
Ear Tag               = named lab BLE beacon
Urban Poaching        = BLE RSSI lab game
```

## Koala Kapture

Koala Kapture records passive BLE advertisement metadata from owned or written-scope lab devices.

Primary files:

```text
pi-companion/koalablue/koala_kapture.py
scripts/run_koala_kapture.py
docs/KOALA_KAPTURE_REVA12.md
```

Output:

```text
/blecaptures/koala_kapture/*.jsonl
/blecaptures/koala_kapture/*.csv
/blecaptures/koala_kapture/*_manifest.json
```

## Koala Kry

Koala Kry replays saved metadata captured by Koala Kapture into local files only.

RevA15 adds a review-manifest path. The review command records the request, keeps radio output disabled, and writes a JSON file with safe next steps.

Primary files:

```text
pi-companion/koalablue/koala_kry.py
scripts/run_koala_kry.py
docs/KOALA_KRY_REVA12.md
```

Output:

```text
logs/koala_kry_replay/*.jsonl
logs/koala_kry_replay/*_summary.json
logs/koala_kry_replay/koala_kry_transmit_review_*.json
```

Review command:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kry.py --request-rf-transmit --lab-setting --owned-device
```

## Menu Selection Screen

The menu screen supports the six front-panel buttons, touch drag scrolling, touch long-press selection, and the Koala Kry RF Review entry.

Primary files:

```text
pi-companion/koalablue/menu_ui.py
pi-companion/koalablue/menu_screen.py
pi-companion/koalablue/menu_catalog.py
scripts/run_menu_screen.py
docs/MENU_SELECTION_REVA12.md
```

## Config

The shared defaults are in:

```text
pi-companion/config.default.json
```

## Safety

Capture and replay work is local/passive/offline unless the device is running the existing named lab beacon firmware. Use synthetic, clearly named owned-device lab beacon payloads for radio-oriented learning.
