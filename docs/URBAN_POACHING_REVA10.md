# RevA10 Urban Poaching

## What it is

**Urban Poaching** is KoalaByte Blue's authorized BLE RSSI training game. It is designed for a controlled lab where the player uses KoalaByte Blue to find the project's own **Ear Tag** lab beacon.

Default lab target name:

```text
EarTag-Lab
```

## Why RSSI

BLE advertisements include received signal strength information at the scanner. RSSI is useful as a rough proximity signal, but it is noisy and affected by walls, antenna orientation, body blocking, reflections, and radio environment. Urban Poaching therefore uses RSSI only as a game hint, not as a precision locator.

## Safety scope

Use Urban Poaching only with:

- KoalaByte Blue's own Ear Tag lab beacon.
- Owned BLE development boards.
- Written-scope lab training devices.

The game does not connect, pair, write to, or modify any BLE device. It only observes advertisements from the configured lab target.

## Default game config

See `pi-companion/config.default.json`:

```json
{
  "action_names": {
    "ble_fox_hunt_game": "Urban Poaching"
  },
  "urban_poaching": {
    "default_target_name": "EarTag-Lab",
    "scan_seconds": 4.0,
    "rounds": 12,
    "capture_radius_rssi": -48,
    "close_rssi": -60,
    "warm_rssi": -72,
    "xp_reward_found": 25
  }
}
```

## Run

From the repo root on the Raspberry Pi:

```bash
cd pi-companion
source .venv/bin/activate
PYTHONPATH=. python ../scripts/run_urban_poaching.py --target-name EarTag-Lab
```

Or run the module directly:

```bash
cd pi-companion
source .venv/bin/activate
PYTHONPATH=. python -m koalablue.urban_poaching --target-name EarTag-Lab
```

## Game hints

Urban Poaching emits hints such as:

```text
cold - weak signal
warm - keep sweeping
hot - close range
capture range - target is close
getting warmer - keep moving this way
getting colder - backtrack or rotate
steady signal - fan left/right and compare RSSI
```

## Logs

Game results are stored under:

```text
pi-companion/logs/urban_poaching/
```

Results include target name, per-round RSSI observations, score, found status, and XP reward.

## XP

Default scoring:

- Found target: 25 XP
- Not found: 1 XP per completed round

The companion app can use the returned `xp_reward` field to feed the killerkoala leveling system.
