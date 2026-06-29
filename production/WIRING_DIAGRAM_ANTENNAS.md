# KoalaByte Blue Production Antenna Wiring

This guide covers the default KoalaByte Blue antenna/RF routing for the Heltec Mesh Node T114 and Waveshare ESP32-S3 DualEye board.

## Default rule

For the first production build, keep the factory/default 2.4 GHz paths unchanged.

```text
ESP32-S3 DualEye 2.4 GHz -> factory onboard ceramic path
Heltec T114 2.4 GHz -> factory/default board path
Raspberry Pi 3B+ -> built-in Wi-Fi path
Heltec T114 LoRa -> region-matched LoRa antenna on the LoRa connector
```

## Heltec T114 LoRa path

```text
Heltec Mesh Node T114 LoRa / SX1262 antenna connector
  -> region-matched LoRa antenna
```

Use the LoRa antenna frequency that matches your T114 board and region. Common examples are 915 MHz in the US and 868 MHz where legal. Do not attach a 2.4 GHz Wi-Fi/BLE antenna to the LoRa port.

## 2.4 GHz paths

```text
ESP32-S3 DualEye -> onboard ceramic 2.4 GHz path
Heltec T114 -> factory/default 2.4 GHz path
Raspberry Pi -> built-in Wi-Fi path, optional USB Wi-Fi adapter only
```

No extra case-mounted 2.4 GHz pigtails or bulkhead paths are required for the default KoalaByte Blue build.

## Build notes

- Keep LoRa and 2.4 GHz antennas clearly separated.
- The LoRa antenna is the only required external antenna in the default build.
- Use extra 2.4 GHz antenna hardware only after validating the exact board revision and RF path.
- Keep antenna cables away from the speaker magnet, USB power-pack cable, and high-current USB power wiring.

## Production validation

Before closing the case:

- Confirm the Heltec T114 LoRa antenna is connected to the LoRa/SX1262 path and uses the correct regional frequency.
- Confirm the ESP32-S3 DualEye reports `onboard_ceramic_default` in its boot/status JSON.
- Confirm no case wire is pinched by the shell, shelves, buttons, or USB cables.

## Firmware/status files

Antenna readiness is tracked through:

```text
logs/koalabyte_external_antenna_status.json
logs/t114_lora_external_antenna_status.json
logs/t114_2g4_antenna_status.json
logs/esp32s3_dualeye_2g4_antenna_status.json
```
