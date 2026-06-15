# RevA9 Ear Tag Lab Beacon Skill

## Purpose

RevA9 renames the safe lab BLE beacon skill to **Ear Tag**. It is designed for owned-device testing and advertises a clearly labeled lab BLE name that KoalaByte Blue can detect, log, and report during authorized lab work.

This is useful for:

- Testing KoalaByte Blue BLE scanning and logging.
- Testing local mobile BLE scanner apps.
- Validating reports and lab workflows.
- Demonstrating how named BLE advertisements appear in the KoalaByte Blue UI.

## Behavior

The **Ear Tag** lab beacon advertises a configurable name such as:

```text
EarTag-Lab
```

The name can be changed at build time. Use a name that clearly identifies the device as your own lab beacon.

## Safety boundary

This skill is limited to clearly labeled lab-device advertising and a read-only status characteristic.

## Configure the lab beacon name

Edit:

```text
firmware/nrf52840-dk-lab-peripheral/prj.conf
```

Set:

```text
CONFIG_BT_DEVICE_NAME="EarTag-Lab"
```

Or use the helper:

```bash
python3 scripts/set_lab_ble_name.py EarTag-Lab
```

## Flash

```bash
bash scripts/flash_nrf52840_dk_lab.sh
```

## Test

Run KoalaByte Blue passive scan or a BLE scanner app. Confirm the advertisement name matches your lab name and that captures are stored under `/blecaptures/` when `eucalyptus` always-on capture is enabled.
