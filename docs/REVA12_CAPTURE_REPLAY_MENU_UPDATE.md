# RevA12 Capture, Replay, and Menu Update

## Naming

```text
eucalyptus     = always-on passive BLE observation/logger
Koala Kapture  = passive BLE metadata capture and archive
Koala Kry      = offline replay of Koala Kapture metadata
Ear Tag        = named lab BLE beacon
Urban Poaching = BLE RSSI lab game
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

Koala Kry now replays saved metadata captured by Koala Kapture. It does not transmit RF and does not replay BLE advertisements over the air.

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
```

## Menu Selection Screen

The menu screen supports:

- Button 1: Main Menu
- Button 2: Left / Back
- Button 3: Select; hold for shutdown route
- Button 4: Right / Forward
- Button 5: Up
- Button 6: Down
- Touch drag to scroll
- Touch long press to select

Primary files:

```text
pi-companion/koalablue/menu_ui.py
pi-companion/koalablue/menu_screen.py
scripts/run_menu_screen.py
docs/MENU_SELECTION_REVA12.md
```

## Config

The shared defaults are in:

```text
pi-companion/config.default.json
```

## Safety

All RevA12 capture and replay work is local/passive/offline unless the device is running the existing named lab beacon firmware. No RF flooding, jamming, disruption, or over-the-air replay is included.
