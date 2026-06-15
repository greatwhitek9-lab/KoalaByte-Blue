# RevA20 Koala Konnect

## Purpose

**Koala Konnect** is the optional external Bluetooth adapter mode for KoalaByte Blue.

In this mode, the Nordic nRF52840 USB Dongle is flashed as a USB HCI Bluetooth controller so a phone or computer can use it as an external Bluetooth adapter when the host operating system supports USB Bluetooth HCI devices.

This is an alternate dongle firmware profile. It does not replace the default KoalaByte Blue Ear Tag TX Lab firmware.

## Hardware target

```text
Nordic nRF52840 USB Dongle / PCA10059 / NRF52840-DONGLE
Board: nrf52840dongle_nrf52840
```

## Modes

| Mode | Firmware path/source | Purpose |
|---|---|---|
| Ear Tag TX Lab | `firmware/nrf52840-dongle-ear-tag-tx-lab/` | Synthetic owned-device BLE advertisement for KoalaByte Blue lab testing |
| Koala Konnect | Zephyr `samples/bluetooth/hci_usb` | USB HCI Bluetooth adapter mode for a phone or computer host |

Only one firmware mode can be flashed to the dongle at a time. Reflash the dongle to switch modes.

## Build Koala Konnect

From the repo root, with nRF Connect SDK / Zephyr available:

```bash
bash scripts/build_nrf52840_dongle_hci_usb_adapter.sh
```

Default build output:

```text
build/nrf52840-dongle-koala-konnect/zephyr/zephyr.hex
```

## Create DFU package

```bash
bash scripts/flash_nrf52840_dongle_koala_konnect_dfu.sh
```

The script creates:

```text
build/nrf52840-dongle-koala-konnect/koala-konnect-nrf52840-dongle-dfu.zip
```

## Flash Koala Konnect

Put the nRF52840 Dongle into bootloader mode, identify the DFU serial port, then run:

```bash
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_nrf52840_dongle_koala_konnect_dfu.sh
```

Adjust the port for your OS.

## Use with Linux / Raspberry Pi / desktop computer

After flashing Koala Konnect:

1. Unplug and replug the dongle.
2. Confirm the USB device appears.
3. Confirm the host Bluetooth stack sees an HCI adapter.

Useful checks on Linux:

```bash
lsusb
bluetoothctl list
bluetoothctl show
hciconfig -a 2>/dev/null || true
```

On BlueZ-based Linux systems, the host computer provides the Bluetooth stack. Koala Konnect provides the USB HCI controller interface.

## Use with a phone

Phone support depends on the phone hardware, USB OTG support, power budget, kernel, and operating system Bluetooth stack.

General requirements:

- USB-C or micro-USB OTG adapter.
- The phone must support USB host mode.
- The operating system must support external USB Bluetooth HCI adapters.
- The dongle may need external power if the phone cannot supply enough current.

Android compatibility varies by device and ROM. Stock phones may ignore external Bluetooth HCI adapters even when USB OTG works. Rooted or specialist builds are more likely to expose the adapter to the Bluetooth stack.

## Return to Ear Tag TX Lab mode

To return the dongle to the default KoalaByte Blue lab beacon mode:

```bash
bash scripts/build_nrf52840_dongle_lab.sh
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_nrf52840_dongle_lab_dfu.sh
```

Expected default advertisement after returning to Ear Tag TX Lab:

```text
EarTag-TX-Lab
```

## Safety and scope

Koala Konnect is only an external Bluetooth adapter mode. It does not add pairing bypass, spoofing, packet replay, or unauthorized access features. All Bluetooth activity is controlled by the host phone or computer and must remain limited to lawful, owned-device, or written-scope work.
