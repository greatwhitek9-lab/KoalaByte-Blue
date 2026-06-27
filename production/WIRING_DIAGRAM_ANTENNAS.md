# KoalaByte Blue Production Antenna Wiring

This main-branch production guide covers the Heltec Mesh Node T114 and ESP32-S3 DualEye antenna paths for the Heltec power-pack production build.

## Heltec T114 LoRa path

```text
Heltec Mesh Node T114 LoRa / SX1262 antenna connector
  -> short IPEX/U.FL/MHF coax pigtail if needed
  -> case-mounted SMA or RP-SMA bulkhead connector if used
  -> region-matched LoRa antenna
```

Use the LoRa antenna frequency that matches your T114 board and region. Common examples are 915 MHz in the US and 868 MHz where legal. Do not attach a 2.4 GHz Wi-Fi/BLE antenna to the LoRa port.

## Heltec T114 2.4 GHz path, if exposed

```text
Heltec Mesh Node T114 2.4 GHz / BLE antenna connector, if present on your board revision
  -> short IPEX/U.FL/MHF coax pigtail
  -> case-mounted SMA or RP-SMA bulkhead connector if used
  -> external 2.4 GHz Wi-Fi/Bluetooth/BLE antenna
```

Some T114 board revisions may use an onboard 2.4 GHz antenna or may not expose a separate 2.4 GHz connector. Follow the vendor-documented antenna selector path for the exact board revision.

## ESP32-S3 DualEye external 2.4 GHz path

```text
ESP32-S3 DualEye 2.4 GHz / IPEX1-U.FL-MHF1 connector
  -> short IPEX/U.FL/MHF1 coax pigtail
  -> case-mounted SMA or RP-SMA bulkhead connector if used
  -> external 2.4 GHz Wi-Fi/Bluetooth antenna
```

## Build notes

- Use the ESP32-S3 DualEye external-antenna board variant when possible.
- If the ESP32 board revision uses an antenna-selector resistor or jumper, configure it for the external IPEX/U.FL path according to the vendor documentation.
- Do not solder random wire to the ESP32 or Heltec antenna pads.
- Keep LoRa and 2.4 GHz antenna cables separated where practical.
- Keep antenna cables away from the speaker magnet, USB power-pack cable, and high-current USB power wiring.
- Keep Heltec LoRa, Heltec 2.4 GHz, and ESP32 2.4 GHz antenna paths clearly labeled inside the case.

## Production validation

Before closing the case:

- Confirm the Heltec T114 LoRa antenna is connected to the LoRa/SX1262 path and uses the correct regional frequency.
- Confirm the Heltec 2.4 GHz antenna path, if used, is connected only to the T114 2.4 GHz connector/selector path.
- Confirm the ESP32-S3 DualEye external 2.4 GHz antenna is connected to the ESP32-S3 DualEye IPEX/U.FL/MHF1 connector through the pigtail/bulkhead path.
- Confirm every coax pigtail is strain-relieved and not pinched by the case.
- Confirm antenna cables are not routed across the Raspberry Pi power cable, speaker magnet, optional CAN service bay, or button wiring.

## Firmware/status files

Antenna readiness is tracked through the production status helpers in:

```text
logs/koalabyte_external_antenna_status.json
logs/t114_lora_external_antenna_status.json
logs/t114_2g4_antenna_status.json
logs/esp32s3_dualeye_2g4_antenna_status.json
```
