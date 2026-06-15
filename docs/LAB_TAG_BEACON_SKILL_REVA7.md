# RevA7 KoalaTag Lab Beacon Skill

## Purpose

RevA7 adds a safe **KoalaTag Lab Beacon** skill for owned-device testing. It is designed to advertise a clearly labeled lab BLE name that KoalaByte Blue can detect, log, and report during authorized lab work.

This is useful for:

- Testing KoalaByte Blue BLE scanning and logging.
- Testing local mobile BLE scanner apps.
- Validating reports and lab workflows.
- Demonstrating how named BLE advertisements appear in the KoalaByte Blue UI.

## Behavior

The lab beacon advertises a configurable name such as:

```text
KoalaTag-Lab
```

The name can be changed at build time. Use a name that clearly identifies the device as your own lab beacon.

## Safety boundary

This skill is limited to clearly labeled lab-device advertising and a read-only status characteristic. It does not implement third-party tracker identity behavior, tracking-network behavior, hidden identity rotation, or location-tracking workflows.

## Configure the lab beacon name

Edit:

```text
firmware/nrf52840-dk-lab-peripheral/prj.conf
```

Set:

```text
CONFIG_BT_DEVICE_NAME="KoalaTag-Lab"
CONFIG_KOALABYTE_LAB_TAG_NAME="KoalaTag-Lab"
```

## Flash

```bash
bash scripts/flash_nrf52840_dk_lab.sh
```

## Test

Run KoalaByte Blue passive scan or a BLE scanner app. Confirm the advertisement name matches your lab name and that captures are stored under `/blecaptures/` when always-on capture is enabled.
