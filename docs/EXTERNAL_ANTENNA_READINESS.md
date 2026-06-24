# External Antenna Readiness

KoalaByte Blue V2 Heltec Edition uses separate antenna paths for LoRa, ESP32-S3 2.4 GHz, Heltec 2.4 GHz, and Raspberry Pi 2.4 GHz.

Run the full readiness check with:

```bash
bash scripts/configure_koalabyte_external_antennas.sh --check-only
```

This writes:

```text
logs/koalabyte_external_antenna_status.json
logs/t114_lora_external_antenna_status.json
logs/t114_2g4_antenna_status.json
logs/esp32s3_dualeye_2g4_antenna_status.json
logs/pi_2g4_external_antenna_status.json
```

## Heltec T114 LoRa antenna

Helper:

```bash
bash scripts/configure_t114_lora_external_antenna.sh --check-only
```

Default path:

```text
Heltec T114 LoRa/SX1262 antenna connector
-> u.FL/IPEX pigtail
-> SMA/RP-SMA case bulkhead
-> region-matched LoRa antenna
```

Default region hint:

```text
HELTEC_T114_LORA_REGION=US915
```

Rules:

- Use a LoRa antenna matched to the configured regional band.
- Do not attach a 2.4 GHz WiFi/Bluetooth antenna to the LoRa connector.
- Do not transmit LoRa without the matched LoRa antenna attached.

## Heltec T114 2.4 GHz antenna

Helper:

```bash
bash scripts/configure_t114_2g4_antenna.sh --check-only
```

Default path:

```text
Heltec T114 2.4 GHz antenna connector
-> u.FL/IPEX pigtail
-> SMA/RP-SMA case bulkhead
-> 2.4 GHz antenna
```

Rules:

- This is not the LoRa connector.
- Only use an RF-switch overlay when the exact Heltec board schematic or board DTS confirms the switch GPIO.
- The helper records connector-only physical mode when no validated switch overlay is available.

## ESP32-S3 DualEye 2.4 GHz antenna

Helper:

```bash
bash scripts/configure_esp32s3_dualeye_2g4_antenna.sh --check-only
```

Default path:

```text
ESP32-S3 DualEye IPEX1/U.FL/MHF1 2.4 GHz connector
-> IPEX/U.FL pigtail
-> SMA/RP-SMA case bulkhead
-> 2.4 GHz antenna
```

Rules:

- Use a proper 2.4 GHz antenna.
- Do not solder directly to the IPEX/U.FL connector.
- If the board revision uses an antenna selector resistor/jumper, set it according to the vendor board documentation.

## Raspberry Pi 3B+ 2.4 GHz antenna

Helper:

```bash
bash scripts/configure_pi_2g4_external_antenna.sh --check-only
```

Supported production path:

```text
Pi USB-A port
-> USB 2.4 GHz WiFi/BLE adapter with external antenna connector
-> 2.4 GHz antenna
```

Rules:

- The Pi 3B+ onboard WiFi/Bluetooth antenna is not treated as an external-antenna radio in this project.
- Do not solder an antenna directly to the Raspberry Pi PCB as the production/default path.
- Use a USB WiFi/BLE adapter with a proper SMA/RP-SMA/IPEX antenna connector if the Pi needs an external 2.4 GHz antenna.

## Installer integration

`scripts/install_pi.sh` runs the aggregate helper after protocol artifact generation, so `bash scripts/flash_all_components.sh --install-firmware` and `bash scripts/flash_all_components.sh --all` generate the antenna readiness artifacts automatically.
