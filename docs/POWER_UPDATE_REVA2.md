# RevA2 Power Update — Superseded

This file is retained only for historical reference. The current main-branch production build no longer uses the old USB-C PD trigger, buck converter, fused 5 V rail, or loose-cell battery wiring path.

Use the current USB power-bank guide instead:

```text
production/RevA17-dongle-only/BATTERY_POWER_2S_18650.md
```

That compatibility-named file now documents the current **PIFFA-style 50000 mAh USB portable power bank 22.5 W class** power path.

## Current power path

```text
PIFFA-style USB portable power bank
  -> regulated USB-A or USB-C output
  -> short quality USB power cable
  -> Raspberry Pi 3B+ micro-USB power input

Raspberry Pi USB ports or optional powered USB hub
  -> Nordic nRF52840 USB Dongle
  -> ESP32-S3 DualEye
  -> optional Heltec USB-C LoRa/GNSS board
  -> optional InnoMaker USB-to-CAN adapter
```

## Do not use for new builds

The following older parts are not part of the current main production power plan:

- USB-C PD/QC trigger board
- 5 V buck regulator
- loose 18650 cells
- 2S holder
- 2S BMS wiring
- inline battery fuse
- DC battery switch
- raw battery distribution rails

## Current validation

1. Fully charge the USB power bank.
2. Power the Raspberry Pi 3B+ through its micro-USB input using a short quality cable.
3. Confirm no undervoltage warnings.
4. Add USB devices one at a time.
5. Use a powered USB hub if accessories disconnect or the Pi reports undervoltage.
6. Add strain relief for every USB cable before closing the case.
