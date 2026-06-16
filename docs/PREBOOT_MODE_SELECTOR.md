# KoalaByte Blue Pre-Boot Dongle Mode Selector

## Purpose

The pre-boot mode selector lets the operator choose the nRF52840 Dongle profile before the normal KoalaByte Blue boot splash and main menu run.

Available choices:

```text
1) KoalaByte Blue Lab Mode
   Default production/lab mode. The dongle advertises as KoalaByte Lab for owned-device BLE scan testing.

2) Koala Konnect Mode
   External USB HCI adapter mode. Replug the dongle into the phone or computer host USB port after switching.
```

The selector is a Pi-side startup step. It does not change the Raspberry Pi bootloader. It runs before the KoalaByte Blue boot splash/menu flow and calls Koala Mode Switcher when a DFU port is available.

## Offline firmware cache on the Pi

The Raspberry Pi can store both nRF52840 Dongle DFU packages locally so a second computer is not needed for normal mode switching.

Prepare both cached firmwares:

```bash
bash scripts/prepare_dongle_firmware_cache.sh
```

Equivalent Python command:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py prepare-cache
```

Check cache status without rebuilding:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py cache-status
```

Cache status file:

```text
logs/dongle_firmware_cache.json
```

Cached DFU ZIPs:

```text
build/nrf52840-dongle-lab/koalabyte-blue-nrf52840-dongle-dfu.zip
build/nrf52840-dongle-koala-konnect/koala-konnect-nrf52840-dongle-dfu.zip
```

When those ZIPs exist, the pre-boot selector shows each mode as `READY`. When one is missing, it shows `MISSING` and tells you to run the cache preparation command.

## Runner

Interactive pre-boot selector:

```bash
PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py
```

Choose Lab directly:

```bash
PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --mode koalabyte_lab
```

Choose Koala Konnect directly:

```bash
PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --mode koala_konnect
```

Choose and flash when the nRF52840 Dongle is in DFU bootloader mode:

```bash
NRF_DFU_PORT=/dev/ttyACM0 PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --mode koalabyte_lab
NRF_DFU_PORT=/dev/ttyACM0 PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --mode koala_konnect
```

If a cached DFU ZIP is available, the selector flashes that saved package directly from the Pi. If the selected cache is missing, the switcher falls back to the packaging script when possible and tells you what failed if required build/package tools are unavailable.

## Full boot wrapper

Use this wrapper as the normal Pi-side startup command:

```bash
bash scripts/koalabyte_blue_boot.sh
```

Boot wrapper order:

```text
1. Pre-boot dongle mode selector
2. KoalaByte Blue boot splash
3. KoalaByte Blue grouped menu
```

Useful environment variables:

```bash
# Skip selector and continue to boot splash/menu
PREBOOT_SELECTOR=0 bash scripts/koalabyte_blue_boot.sh

# Pick KoalaByte Blue Lab Mode without prompting
PREBOOT_MODE=koalabyte_lab bash scripts/koalabyte_blue_boot.sh

# Pick Koala Konnect Mode without prompting
PREBOOT_MODE=koala_konnect bash scripts/koalabyte_blue_boot.sh

# Record selected mode but do not flash the dongle
PREBOOT_NO_APPLY=1 PREBOOT_MODE=koala_konnect bash scripts/koalabyte_blue_boot.sh

# Flash selected mode through DFU when the dongle is in bootloader mode
NRF_DFU_PORT=/dev/ttyACM0 PREBOOT_MODE=koala_konnect bash scripts/koalabyte_blue_boot.sh
```

## Important behavior

The nRF52840 Dongle can hold only one active firmware profile at a time. Switching between KoalaByte Blue Lab Mode and Koala Konnect Mode requires DFU flashing the dongle.

If no DFU port is available, the selector records the requested mode in:

```text
logs/preboot_mode_selection.json
```

but it does not claim the physical dongle was switched.

Koala Mode Switcher state and cache files live at:

```text
logs/dongle_mode_state.json
logs/dongle_mode_events.jsonl
logs/dongle_firmware_cache.json
```

## Safety and scope

KoalaByte Blue Lab Mode remains the default production/lab mode. Koala Konnect is an alternate USB HCI adapter profile. Use only owned or written-scope lab devices and keep testing within authorized environments.
