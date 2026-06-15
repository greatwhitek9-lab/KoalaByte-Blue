# RevA21 Koala Mode Switcher

## Purpose

Koala Mode Switcher is the Pi-side controller for switching the nRF52840 USB Dongle between the two supported KoalaByte Blue dongle firmware profiles:

| Mode | Default? | Purpose |
|---|---:|---|
| KoalaByte Lab | Yes | Synthetic owned-device BLE lab advertisement mode |
| Koala Konnect | No | USB HCI external Bluetooth adapter mode for a compatible phone or computer |

Only one firmware can be installed on the dongle at a time. The switcher stores and manages both build/package profiles, then reflashes the selected mode through the dongle DFU flow.

## Default production/lab mode

KoalaByte Lab remains the default production/lab mode.

The default state file is:

```text
logs/dongle_mode_state.json
```

If no state file exists yet, the switcher treats the active mode as:

```text
KoalaByte Lab
```

## Build both firmwares and create both DFU ZIPs

From the repo root:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py prepare-all
```

This runs the build and DFU-package flow for both:

```text
KoalaByte Lab
Koala Konnect
```

Expected DFU package paths:

```text
build/nrf52840-dongle-lab/koalabyte-blue-nrf52840-dongle-dfu.zip
build/nrf52840-dongle-koala-konnect/koala-konnect-nrf52840-dongle-dfu.zip
```

## Show current mode and artifact status

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py status
```

This writes or refreshes:

```text
logs/dongle_mode_state.json
logs/dongle_mode_events.jsonl
```

## Switch to KoalaByte Lab

Put the dongle into bootloader mode, identify the DFU serial port, then run:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py switch koalabyte_lab --dfu-port /dev/ttyACM0
```

You can also use the environment variable form:

```bash
NRF_DFU_PORT=/dev/ttyACM0 PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py switch koalabyte_lab
```

After a successful switch, the state file records:

```text
active_mode: koalabyte_lab
active_title: KoalaByte Lab
killerkoala_line: KoalaByte Lab loaded. Clean beacon, clean scope, and the lab signal is ours.
```

## Switch to Koala Konnect

Put the dongle into bootloader mode, identify the DFU serial port, then run:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py switch koala_konnect --dfu-port /dev/ttyACM0
```

After a successful switch, the state file records:

```text
active_mode: koala_konnect
active_title: Koala Konnect
killerkoala_line: Koala Konnect loaded. Plug me into the host and let the machine drive the stack.
```

## Build or package one mode only

Build one mode:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py build koalabyte_lab
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py build koala_konnect
```

Package one mode without flashing:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py package koalabyte_lab
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py package koala_konnect
```

Build and package one mode:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py prepare koalabyte_lab
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py prepare koala_konnect
```

## Safety and scope

Koala Mode Switcher does not create a dual-boot dongle. It manages two firmware profiles and flashes one selected profile at a time.

Flashing requires an explicit DFU port. Without `--dfu-port` or `NRF_DFU_PORT`, switch/apply actions are blocked and only metadata is written.

KoalaByte Lab remains the safe default production/lab mode. Koala Konnect should only be used with owned phones/computers or systems where you have permission to attach an external Bluetooth adapter.
