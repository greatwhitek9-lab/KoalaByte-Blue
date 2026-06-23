# Koala Konnect - Heltec T114 Edition

## Purpose

On `koalabyte_blue_v2_heltec_edition`, **Koala Konnect** is the optional USB HCI controller profile for the **Heltec Mesh Node T114 v2 onboard nRF52840**.

It is not a separate USB accessory profile for this branch.

## Hardware target

```text
Heltec Mesh Node T114 v2 onboard nRF52840
Board target: heltec_t114_v2/nrf52840
```

## Modes

| Mode | Hardware target | Purpose |
|---|---|---|
| Heltec Mouth / BLE / GNSS | Heltec T114 onboard nRF52840 | Normal KoalaByte Blue Heltec mode with mouth display, BLE status, and GNSS path |
| Koala Konnect T114 | Heltec T114 onboard nRF52840 | Optional USB Bluetooth HCI controller mode for local BlueZ checks |

Only one T114 profile can be active at a time. Using Koala Konnect T114 replaces the normal Heltec mouth/BLE/GNSS firmware until the normal Heltec firmware is restored.

## Build Koala Konnect T114

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/build_koala_konnect_t114.sh
```

Build through the all-component helper:

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_all_components.sh --nrf-konnect --build-only
```

## Apply Koala Konnect T114 to the Heltec board

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_koala_konnect_t114.sh
```

Or through the all-component helper:

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_all_components.sh --nrf-konnect
```

## Return to normal Heltec mode

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 bash scripts/flash_heltec_mouth.sh
```

## Readiness checks

Controller check:

```bash
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py controller-check
```

Safe local check bundle:

```bash
PYTHONPATH=pi-companion python3 scripts/run_t114_bluez.py all-safe
```

## Safety and scope

Koala Konnect T114 provides a local USB HCI controller profile for owned-lab checks. It does not add pairing bypass, spoofing, packet replay, or unauthorized access features. All Bluetooth activity must remain limited to lawful, owned-device, or written-scope work.
