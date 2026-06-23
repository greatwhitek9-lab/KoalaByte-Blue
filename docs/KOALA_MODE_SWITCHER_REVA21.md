# Koala Mode Switcher - Heltec T114 Edition

## Purpose

On `koalabyte_blue_v2_heltec_edition`, **Koala Mode Switcher is the Pi-side controller for the Heltec Mesh Node T114 v2 onboard nRF52840**, not for a separate Nordic nRF52840 USB Dongle.

The switcher tracks and launches the supported Heltec T114 firmware profiles:

| Mode | Default? | Hardware target | Purpose |
|---|---:|---|---|
| Heltec Mouth / BLE / GNSS | Yes | Heltec T114 onboard nRF52840 | Normal KoalaByte Blue Heltec mode with the T114 mouth display, local BLE observation status, and GNSS path |
| Koala Konnect T114 | No | Heltec T114 onboard nRF52840 | Optional USB Bluetooth HCI controller profile for local BlueZ-based checks |

Only one firmware profile can be active on the Heltec T114 at a time. Flashing Koala Konnect T114 replaces the normal mouth/BLE/GNSS firmware until `firmware/heltec-mouth/` is flashed back.

## Default production/lab mode

The default mode for this branch is:

```text
Heltec Mouth / BLE / GNSS
```

The normal firmware lives under:

```text
firmware/heltec-mouth/
```

The normal flash helper is:

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 bash scripts/flash_heltec_mouth.sh
```

Through the all-component helper:

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --heltec-t114
```

## Optional Koala Konnect T114 mode

Koala Konnect T114 is an alternate firmware profile for the **same onboard nRF52840 on the Heltec T114**. It is not a USB Dongle profile.

Use the Heltec T114 Zephyr board target:

```text
heltec_t114_v2/nrf52840
```

Build only:

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/build_koala_konnect_t114.sh
```

Build through the all-component helper:

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_all_components.sh --nrf-konnect --build-only
```

Flash Koala Konnect T114:

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_koala_konnect_t114.sh
```

Flash through the all-component helper:

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_all_components.sh --nrf-konnect
```

## Return to normal Heltec mode

After testing Koala Konnect T114, flash the normal Heltec firmware back:

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 bash scripts/flash_heltec_mouth.sh
```

## Check current helper readiness

T114 controller check:

```bash
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py controller-check
```

Safe local wrapper check:

```bash
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py all-safe
```

## Safety and scope

Koala Mode Switcher does not create a dual-boot system. It tracks and helps launch one selected Heltec T114 profile at a time.

Koala Konnect T114 should only be used with owned systems or systems where you have permission to attach and test a Bluetooth HCI controller. The BlueZ wrapper checks are bounded local readiness and inventory checks; they do not implement pairing bypasses, unauthorized access, or offensive workflows.
