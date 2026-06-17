# that’s not a knife local guard service

`that’s not a knife` is the KoalaByte Blue always-on BLE defensive monitor suite. It runs as a small Pi-side loop, reviews recent KoalaByte/host Bluetooth logs, writes local guard state, and lets killerkoala react when a local defensive block succeeds.

## What it does

- Runs continuously through systemd.
- Reads recent local log files and KoalaByte Blue JSON artifacts.
- Monitors BLE DoS pressure, bluesnarfing / blue snarfing risk, bluebugging risk, and pairing/MITM-risk patterns.
- Lets each monitor be turned on or off individually.
- Writes monitor settings to `logs/thats_not_a_knife/monitor_settings.json`.
- Writes state to `logs/thats_not_a_knife/guard_state.json`.
- Writes the local workflow block artifact to `logs/thats_not_a_knife/ble_workflow_block.json`.
- Writes the local killerkoala alert text to `logs/thats_not_a_knife/killerkoala_alert.txt`.
- Awards killerkoala XP **only after a successful defensive block**. Monitoring, detection, and failed block attempts award `0 XP`.
- Uses a cooldown after successful blocks so XP is not farmed repeatedly from the same condition.

The local alert line is:

```text
Crikey’ mate. i blocked a SKID!
```

## Individual monitors

Default monitor IDs:

| Monitor ID | Default | Purpose |
|---|---:|---|
| `dos_pressure` | On | Repeated connection/controller pressure patterns. |
| `bluesnarfing` | On | Suspicious local object, phonebook, contact-card, or file-pull access patterns. |
| `bluebugging` | On | Suspicious local RFCOMM, AT-command, handsfree, call-control, or serial-control patterns. |
| `mitm_guard` | On | Suspicious pairing, authorization, key-change, weak-pairing, or authentication-failure patterns. |

Aliases accepted by the CLI include `dos`, `ble_dos`, `bluesnarf`, `blue_snarfing`, `blue-snarfing`, `bluesnarffing`, `mitm`, and `man-in-the-middle`.

## Turn monitors on or off

Show current settings:

```bash
PYTHONPATH=pi-companion python3 scripts/run_thats_not_a_knife.py status
```

Disable one monitor:

```bash
PYTHONPATH=pi-companion python3 scripts/run_thats_not_a_knife.py disable bluesnarfing
```

Enable one monitor:

```bash
PYTHONPATH=pi-companion python3 scripts/run_thats_not_a_knife.py enable bluesnarfing
```

Change one monitor threshold:

```bash
PYTHONPATH=pi-companion python3 scripts/run_thats_not_a_knife.py threshold mitm_guard 5
```

The always-on service reads the same `monitor_settings.json`, so changes take effect on the next service loop pass.

## XP rule

killerkoala earns XP only when all of these are true:

1. At least one enabled monitor reaches its configured threshold.
2. The local workflow block artifact is written successfully.
3. XP awards are enabled for that guard pass.
4. The XP cooldown has expired.

If the guard is only monitoring, or if a defensive condition is detected but the local block cannot be written, killerkoala earns no XP.

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
