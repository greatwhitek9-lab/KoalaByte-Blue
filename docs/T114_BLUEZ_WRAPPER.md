# T114 BlueZ wrapper

The canonical Heltec Edition branch includes a Pi-side BlueZ wrapper for the optional Heltec T114 USB HCI profile.

## Purpose

When the T114 is flashed with the optional Koala Konnect USB HCI firmware, Linux should expose it as a Bluetooth controller. The wrapper checks that controller and then runs bounded, safe BlueZ actions.

## Main commands

Controller check:

```bash
python3 scripts/run_t114_bluez.py controller-check
```

Status:

```bash
python3 scripts/run_t114_bluez.py status
```

Bounded scan:

```bash
python3 scripts/run_t114_bluez.py scan --duration-seconds 15
```

All safe local checks:

```bash
python3 scripts/run_t114_bluez.py all-safe --duration-seconds 15
```

## Output

Artifacts are written under:

```text
logs/t114_bluez/
logs/hardware_validation/
```

The wrapper records whether the HCI controller is present, which adapter was selected, command return codes, and the safe action output.

## Safety boundaries

The wrapper is for authorized lab use and local device validation only. It does not implement pairing bypass, spoofing, packet replay, or disruptive radio behavior.

## Returning to normal KoalaByte runtime

If the T114 is currently in USB HCI mode and you want normal KoalaByte Blue mouth/GNSS/BLE-primary mode again, flash:

```bash
bash scripts/flash_heltec_mouth.sh
```
