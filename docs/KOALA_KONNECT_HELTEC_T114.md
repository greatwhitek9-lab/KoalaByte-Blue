# Koala Konnect on Heltec T114

Koala Konnect is the optional Heltec T114 USB Bluetooth HCI profile for the canonical Heltec Edition branch.

Use it when you want the Heltec T114 nRF52840 to act as a USB Bluetooth HCI controller for a supported lab host. It is not the default KoalaByte runtime profile.

## Important behavior

Flashing Koala Konnect replaces the normal Heltec mouth/GNSS/BLE-primary firmware until the normal Heltec profile is flashed back.

Normal KoalaByte runtime profile:

```bash
bash scripts/flash_heltec_mouth.sh
```

Optional Koala Konnect profile:

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/build_koala_konnect_t114.sh
T114_FLASH_METHOD=west bash scripts/flash_koala_konnect_t114.sh
```

Equivalent one-shot optional action:

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_all_components.sh --nrf-konnect
```

Build-only validation:

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_all_components.sh --nrf-konnect --build-only
```

## Dependencies

Koala Konnect uses Zephyr's `samples/bluetooth/hci_usb` application. The branch prepares/checks:

- `west`
- nRF tools
- nRF Connect SDK / Zephyr workspace
- confirmed T114 board target
- optional external 2.4 GHz antenna overlay handling

The build helper writes `logs/t114_hci_usb_mode.json`.
The flash helper writes `logs/t114_active_ble_mode.json`.

## Verify on a Linux host

After flashing, unplug and replug the T114 USB-C cable, then check:

```bash
bluetoothctl list
bluetoothctl show
python3 scripts/run_t114_bluez.py controller-check
```

## Safe use notes

- Use only on hardware you own or are authorized to test.
- Do not confuse the 2.4 GHz antenna connector with the LoRa antenna connector.
- Do not use this profile during normal KoalaByte mouth/GNSS/BLE-primary operation.
- Flash the normal Heltec mouth profile back when returning to normal KoalaByte Blue mode.
