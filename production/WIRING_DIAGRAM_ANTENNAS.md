# KoalaByte Blue Production ESP32 Antenna Wiring

This main-branch production guide covers the ESP32-S3 DualEye external 2.4 GHz antenna path for the Nordic USB Dongle build.

## ESP32-S3 DualEye external 2.4 GHz path

```text
ESP32-S3 DualEye 2.4 GHz / IPEX1-U.FL-MHF1 connector
  -> short IPEX/U.FL/MHF1 coax pigtail
  -> case-mounted SMA or RP-SMA bulkhead connector
  -> external 2.4 GHz WiFi/Bluetooth antenna
```

## Build notes

- Use the ESP32-S3 DualEye external-antenna board variant when possible.
- If the board revision uses an antenna-selector resistor or jumper, configure it for the external IPEX/U.FL path according to the vendor documentation.
- Do not solder random wire to the ESP32 antenna pad.
- Keep the ESP32 antenna cable away from the speaker magnet, USB power wiring, and high-current power-bank cable.
- Keep this ESP32 antenna path separate from the Nordic USB Dongle production path.

## Production validation

Before closing the case:

- Confirm the ESP32-S3 DualEye external 2.4 GHz antenna is connected to the ESP32-S3 DualEye IPEX/U.FL/MHF1 connector through the pigtail/bulkhead path.
- Confirm the coax pigtail is strain-relieved and not pinched by the case.
- Confirm the ESP32 antenna cable is not routed across the Raspberry Pi power cable, speaker magnet, or optional CAN service bay.

## Firmware/flash status file

The ESP32-S3 DualEye flash helper records the antenna configuration in:

```text
logs/esp32s3_dualeye_2g4_antenna_status.json
```
