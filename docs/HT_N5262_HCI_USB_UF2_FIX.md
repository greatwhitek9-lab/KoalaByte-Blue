# Heltec T114 / HT-n5262 HCI USB UF2 Fix

This note records the working KoalaByte Blue Heltec T114 flashing flow learned from the standalone Platypus firmware test.

## What changed

The Heltec T114 / HT-n5262 board uses an nRF52840 MCU with a UF2 bootloader that expects a specific flash layout and UF2 family ID.

The reliable HCI USB build must use:

```text
Board target:       heltec_t114_v2/nrf52840/uf2
App offset:         0x1000
App size:           0xdf000
UF2 family:         0x239a0071
Bootloader volume:  HT-n5262
```

The previously generated Zephyr UF2 could copy to the board but fail to boot because the app started at the wrong offset and carried the generic nRF52840 UF2 family.

The known-good final UF2 should inspect like this:

```text
Address min: 0x00001000
Families: ['0x239a0071']
```

## Updated KoalaByte Blue files

The HCI USB path now uses the same fix as Platypus:

```text
scripts/build_nrf52840_t114_hci_usb.sh
scripts/flash_nrf52840_t114_hci_usb.sh
scripts/flash_t114_when_plugged.sh
scripts/inspect_uf2.py
scripts/patch_uf2_family.py
```

## Build only

Use this to build and patch the KoalaByte Blue T114 HCI USB UF2 without flashing the board:

```bash
bash scripts/build_nrf52840_t114_hci_usb.sh
```

Expected output:

```text
releases/koalabyte-blue-t114-hci-usb-HT-n5262-offset1000.uf2
```

## Flash only

Put the Heltec T114 into UF2 bootloader mode first:

1. Plug in the Heltec T114 with a USB-C data cable.
2. Double-tap `RST`.
3. Wait for the `HT-n5262` removable drive to appear.

Then run:

```bash
T114_HCI_BUILD_FIRST=0 \
T114_FLASH_METHOD=uf2 \
T114_PLUG_FLASH_PROFILE=hci-usb \
bash scripts/flash_nrf52840_t114_hci_usb.sh
```

## HCI USB one-shot path

For the Koala Konnect / BlueZ HCI USB profile, use UF2-first mode with the HCI profile selected:

```bash
FLASH_T114_ON_PLUG=1 \
T114_REQUIRE_UF2=1 \
T114_FLASH_METHOD=uf2 \
T114_PLUG_FLASH_PROFILE=hci-usb \
bash scripts/install_koalabyte_one_shot.sh
```

This avoids serial/west fallback and requires the `HT-n5262` UF2 bootloader volume.

## Why UF2-first matters

For this board, the safest path is not `west flash`. The proven path is:

1. Build Zephyr HCI USB firmware for the UF2 board target.
2. Force app load offset `0x1000`.
3. Force app load size `0xdf000`.
4. Patch UF2 family to `0x239a0071`.
5. Copy the patched UF2 to the `HT-n5262` bootloader volume.
6. Unplug, wait five seconds, and replug normally.

After normal replug, Linux should see:

```text
2fe3:000b NordicSemiconductor Zephyr USBD BT HCI
```

BlueZ should expose the board as an HCI controller such as `hci1` when the host already has internal Bluetooth.

## Verify after flashing

```bash
sudo modprobe btusb
sudo systemctl restart bluetooth
sudo rfkill unblock bluetooth

lsusb
ls /sys/class/bluetooth/
bluetoothctl list
```

Expected signs of success:

```text
NordicSemiconductor Zephyr USBD BT HCI
hci0 hci1
```

## Safety note

This fix only makes the Heltec T114 work as a USB Bluetooth HCI controller. Use it only with devices and labs you own or have explicit authorization to test.
