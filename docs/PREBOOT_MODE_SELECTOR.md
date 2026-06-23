# KoalaByte Blue Heltec T114 Mode Selection

## Purpose

On `koalabyte_blue_v2_heltec_edition`, mode selection is centered on the **Heltec Mesh Node T114 v2 onboard nRF52840**.

The supported Heltec profiles are:

```text
1) Heltec Mouth / BLE / GNSS
   Default branch profile. The T114 provides the KoalaByte mouth display, BLE status path, USB CDC bridge, and optional GNSS forwarding.

2) Koala Konnect T114
   Optional USB HCI controller profile for local BlueZ checks through the same T114 onboard nRF52840.
```

This selector concept does not change the Raspberry Pi bootloader. It is a Pi-side startup/menu decision for which Heltec T114 profile should be active.

## Default branch profile

The default profile is:

```text
Heltec Mouth / BLE / GNSS
```

Use the normal Heltec helper when you need to restore the default profile:

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 bash scripts/flash_heltec_mouth.sh
```

## Optional Koala Konnect T114 profile

Build only:

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/build_koala_konnect_t114.sh
```

Apply Koala Konnect T114 through the all-component helper:

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_all_components.sh --nrf-konnect
```

## Full boot wrapper

Use this wrapper as the normal Pi-side startup command:

```bash
bash scripts/koalabyte_blue_boot.sh
```

Boot wrapper order:

```text
1. KillerKoala mode-aware boot welcome
2. KoalaByte Blue boot splash
3. KoalaByte Blue grouped menu
```

## Checks

```bash
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py controller-check
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py all-safe
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
```

## Scope

Koala Konnect T114 is for local, owned-lab, BlueZ readiness checks only.
