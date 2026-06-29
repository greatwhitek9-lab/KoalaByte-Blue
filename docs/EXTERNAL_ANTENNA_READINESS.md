# Antenna Readiness

KoalaByte Blue default policy:

- Use the factory/default 2.4 GHz RF paths on the ESP32-S3 DualEye and Heltec T114.
- The Waveshare ESP32-S3 DualEye uses its onboard ceramic 2.4 GHz RF path by default.
- The Heltec T114 2.4 GHz path is treated as factory/default unless a specific board revision says otherwise.
- The Heltec T114 LoRa connector still needs a region-matched LoRa antenna.
- The Raspberry Pi 3B+ uses built-in Wi-Fi by default; a USB Wi-Fi adapter is optional only.

Readiness check:

```bash
bash scripts/configure_koalabyte_external_antennas.sh --check-only
```

Generated status files:

```text
logs/koalabyte_external_antenna_status.json
logs/t114_lora_external_antenna_status.json
logs/t114_2g4_antenna_status.json
logs/esp32s3_dualeye_2g4_antenna_status.json
logs/pi_2g4_external_antenna_status.json
```

Default routing:

```text
Heltec T114 LoRa connector -> region-matched LoRa antenna
Heltec T114 2.4 GHz -> factory/default path
ESP32-S3 DualEye 2.4 GHz -> onboard ceramic path
Raspberry Pi 3B+ -> built-in Wi-Fi path
```
