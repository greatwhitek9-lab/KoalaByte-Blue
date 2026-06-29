# KoalaByte Blue Production Folder

## Current production package

Use the Heltec power-pack package:

```text
production/RevA25-heltec-powerbank/
```

Current production target:

```text
Raspberry Pi 3B+
Heltec Mesh Node T114 / nRF52840 + SX1262 LoRa board
ESP32-S3 DualEye
8-key front panel using one independent K1-K8 button module
regulated USB portable power pack / power bank
optional InnoMaker USB-to-CAN kit
```

The front panel replaces the older six loose 4-pin tactile buttons with one K1-K8 module. K1-K6 remain the menu/navigation controls. The two far-right buttons are K7 Power On/Off and K8 Reset / Reboot.

This production folder no longer uses the Nordic nRF52840 USB Dongle as the production BLE board and no longer uses loose 18650 cells or raw battery wiring.

## Current files

```text
production/RevA25-heltec-powerbank/PRODUCTION_README_RevA25_HeltecPowerBank.md
production/RevA25-heltec-powerbank/BOM_RevA25_HeltecPowerBank.csv
production/RevA25-heltec-powerbank/USB_POWER_PACK.md
production/WIRING_DIAGRAM_ANTENNAS.md
```

## Bring-up command

Run a dry check first:

```bash
bash scripts/install_koalabyte_one_shot.sh --check-only
```

Then run the full one-shot install:

```bash
bash scripts/install_koalabyte_one_shot.sh
```
