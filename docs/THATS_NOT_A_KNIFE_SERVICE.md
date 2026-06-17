# that’s not a knife local guard service

`that’s not a knife` is the KoalaByte Blue always-on BLE pressure guard. It runs as a small Pi-side loop, reviews recent KoalaByte/host Bluetooth logs, writes a local guard state file, and lets killerkoala react when the guard activates.

## What it does

- Runs continuously through systemd.
- Reads recent local log files and KoalaByte Blue JSON artifacts.
- Scores defensive pressure signals such as repeated connection errors, controller resource pressure, and adapter reset patterns.
- Writes state to `logs/thats_not_a_knife/guard_state.json`.
- Writes the local killerkoala alert text to `logs/thats_not_a_knife/killerkoala_alert.txt`.
- Awards killerkoala XP when the guard activates, with a cooldown so XP is not farmed repeatedly from the same condition.

The local alert line is:

```text
Crikey’ mate. i blocked a SKID!
```

## Safety boundary

This service is local defensive monitoring only. It does not send a radio response, spoof devices, replay packets, or transmit offensive frames. The killerkoala response is local UI/log/TTS text for the operator.

## Install or refresh the service

The normal Pi installer now attempts to install and enable the service automatically:

```bash
bash scripts/install_pi.sh
```

Manual install or refresh:

```bash
bash scripts/install_thats_not_a_knife_service.sh
```

Check status:

```bash
systemctl status koalabyte-thats-not-a-knife.service
```

Watch logs:

```bash
journalctl -u koalabyte-thats-not-a-knife.service -f
```

## Tuning

Set these environment variables before running the installer:

```bash
THATS_NOT_A_KNIFE_INTERVAL_SECONDS=10 \
THATS_NOT_A_KNIFE_THRESHOLD=5 \
THATS_NOT_A_KNIFE_XP_COOLDOWN_SECONDS=300 \
bash scripts/install_thats_not_a_knife_service.sh
```

Run one smoke-test pass without installing systemd:

```bash
PYTHONPATH=pi-companion python3 scripts/run_thats_not_a_knife_loop.py --once
```
