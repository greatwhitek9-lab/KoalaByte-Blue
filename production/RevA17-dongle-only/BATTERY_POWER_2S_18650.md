# KoalaByte Blue USB Power Bank Guide

> Compatibility note: this file keeps the old filename for existing links, but the current main-branch production build no longer uses the 2x18650/BMS/fuse/buck power stack.

KoalaByte Blue now uses a **PIFFA-style 50000 mAh USB portable power bank 22.5 W class** as the primary production power source.

## Power topology

```text
PIFFA-style 50000 mAh USB portable power bank
  -> regulated USB-A or USB-C output
  -> short quality USB power cable
  -> Raspberry Pi 3B+ micro-USB power input

Raspberry Pi USB ports or optional powered USB hub
  -> Nordic nRF52840 USB Dongle
  -> ESP32-S3 DualEye USB data/power
  -> optional Heltec Wireless Tracker V2 / T114 USB data/power
  -> optional InnoMaker USB-to-CAN adapter
```

Use the power bank's normal regulated USB output. Do not open the pack or tap internal lithium cells.

## Required power parts

| Item | Qty | Requirement |
|---|---:|---|
| PIFFA-style 50000 mAh USB portable power bank 22.5 W class | 1 | Use normal regulated USB output. Do not open or modify the pack. |
| Short USB-A or USB-C to micro-USB power cable | 1 | Powers the Raspberry Pi 3B+. Use a short low-resistance cable. |
| Short USB data cable for ESP32-S3 DualEye | 1 | Data-capable cable. |
| Optional USB-A to USB-C data cable for Heltec board | 0-1 | Data-capable cable for optional Didgeridoo/T114 hardware. |
| Optional powered USB hub | 0-1 | Recommended if the Pi shows undervoltage or USB devices disconnect. |
| Cable strain relief | 1 set | Use adhesive cable anchors or printed clips so USB plugs are not stressed. |

## Removed older power parts

The following items are not required for the main production build:

- loose 18650 cells
- 2x18650 series holder
- 2S Li-ion BMS/protection board
- inline blade fuse holder
- 5 A blade fuse
- DC main battery switch
- 5 V buck converter
- USB-C PD/QC trigger board
- raw battery distribution rails

## Device power wiring

| Device | Power/data connection |
|---|---|
| Raspberry Pi 3B+ | Power from power bank to Pi micro-USB input. |
| Nordic nRF52840 USB Dongle | Plugs into Raspberry Pi USB. |
| ESP32-S3 DualEye | USB data/power from Pi or powered USB hub. |
| Optional Heltec Wireless Tracker V2 / T114 | USB data/power from Pi or powered USB hub. |
| Optional InnoMaker USB-CAN | USB data/power from Pi or powered USB hub. |
| Six front buttons | Signal-only wiring to GPIO and GND. Do not connect buttons to power-bank positive or any 5 V line. |

## Bring-up checklist

1. Fully charge the USB power bank.
2. Connect the power bank to the Raspberry Pi 3B+ micro-USB power input using a short quality cable.
3. Boot the Pi and confirm there are no undervoltage warnings.
4. Insert the Nordic nRF52840 USB Dongle and confirm it enumerates.
5. Connect ESP32-S3 DualEye by USB and confirm it enumerates.
6. Add optional Heltec or InnoMaker modules only after the Pi, dongle, and ESP32 remain stable.
7. If devices disconnect or the undervoltage icon appears, use a powered USB hub for accessories or a better power cable/output.
8. Add strain relief for all USB cables before closing the case.

## Safety boundary

- Do not open the power bank or tap its internal battery cells.
- Do not route raw lithium voltage inside the KoalaByte build.
- Do not connect power-bank outputs directly to Pi GPIO, ESP32 GPIO, button wiring, CAN wiring, or antenna hardware.
- Do not swap LoRa, GNSS, and 2.4 GHz antenna systems.
- Do not close the case until USB cable bend radius, strain relief, ventilation, and undervoltage checks pass.
