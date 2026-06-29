# KoalaByte Blue RevA25 USB Power-Pack Guide

KoalaByte Blue RevA25 uses a regulated **USB portable power pack / power bank** as the production power source.

It does **not** use loose cells, a 2S holder, a BMS, a fuse/switch/buck converter stack, a PD trigger board, or raw lithium wiring.

## Power topology

```text
USB portable power pack / power bank
  -> regulated USB-A or USB-C output
  -> short quality USB power cable
  -> Raspberry Pi 3B+ micro-USB power input

Raspberry Pi USB ports or optional powered USB hub
  -> Heltec Mesh Node T114 USB-C data/power
  -> ESP32-S3 DualEye USB data/power
  -> optional InnoMaker USB-to-CAN adapter

Raspberry Pi 40-pin GPIO header/extender
  -> 8-key button module VCC from Pi 3.3V only
  -> 8-key button module GND to Pi GND
  -> K1-K8 signal lines to assigned GPIO inputs
```

Use the power pack's normal regulated USB output. Do not open the pack or tap internal lithium cells.

## Required power parts

| Item | Qty | Requirement |
|---|---:|---|
| Regulated USB portable power pack / power bank | 1 | Use normal regulated USB output. Do not open or modify the pack. |
| Short USB-A or USB-C to micro-USB power cable | 1 | Powers the Raspberry Pi 3B+. Use a short low-resistance cable. |
| USB-C data cable for Heltec T114 | 1 | Data-capable cable from Pi or powered hub. |
| Short USB data cable for ESP32-S3 DualEye | 1 | Data-capable cable from Pi or powered hub. |
| 8 independent key button module | 1 | VCC to Pi 3.3V only, GND to Pi GND, K1-K8 to GPIO inputs. Do not connect to 5V or raw battery voltage. |
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
- six loose 4-pin tactile button wiring

## Device power wiring

| Device | Power/data connection |
|---|---|
| Raspberry Pi 3B+ | Power from power pack to Pi micro-USB input. |
| Heltec Mesh Node T114 | USB-C data/power from Pi or powered USB hub. |
| ESP32-S3 DualEye | USB data/power from Pi or powered USB hub. |
| Optional InnoMaker USB-CAN | USB data/power from Pi or powered USB hub. |
| 8-key front button module | VCC to Pi 3.3V only, GND to Pi GND, K1-K8 to GPIO. K7 is Power On/Off; K8 is Reset / Reboot. |

K7 can request a clean software shutdown while the Pi is already running. A GPIO button cannot power on a fully unpowered Raspberry Pi without a supported external power-control board or the USB power bank's own control.

## Bring-up checklist

1. Fully charge the USB power pack.
2. Connect the power pack to the Raspberry Pi 3B+ micro-USB power input using a short quality cable.
3. Boot the Pi and confirm there are no undervoltage warnings.
4. Connect the Heltec Mesh Node T114 by USB-C data cable and confirm it enumerates.
5. Connect ESP32-S3 DualEye by USB and confirm it enumerates.
6. Wire the 8-key button module using Pi 3.3V, Pi GND, and the assigned K1-K8 GPIO lines only.
7. Add the optional InnoMaker module only after the Pi, Heltec, ESP32, and button board remain stable.
8. If devices disconnect or the undervoltage icon appears, use a powered USB hub for accessories or a better power cable/output.
9. Add strain relief for all USB cables before closing the case.

## Safety boundary

- Do not open the power pack or tap its internal battery cells.
- Do not route raw lithium voltage inside the KoalaByte build.
- Do not connect power-pack outputs directly to Pi GPIO, ESP32 GPIO, button wiring, CAN wiring, or antenna hardware.
- Do not power the K1-K8 button module from 5V when its signal outputs connect to Raspberry Pi GPIO.
- Do not close the case until USB cable bend radius, strain relief, ventilation, button clearance, and undervoltage checks pass.
