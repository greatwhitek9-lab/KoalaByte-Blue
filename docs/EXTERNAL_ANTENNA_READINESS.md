# External Antenna Readiness

Corrected KoalaByte Blue V2 Heltec Edition antenna policy:

- The additional case-mounted 2.4 GHz antenna routes to the Heltec T114 2.4 GHz connector.
- The Heltec T114 LoRa connector uses a region-matched LoRa antenna.
- The ESP32-S3 DualEye uses its own IPEX1/U.FL/MHF1 2.4 GHz connector path.
- The Raspberry Pi does not require an external 2.4 GHz antenna in the default build.
- A Raspberry Pi USB wireless adapter with an antenna connector is optional only.
- Missing Raspberry Pi USB wireless hardware must not fail firmware, installer, CI, or readiness.
- Do not solder an antenna directly to the Raspberry Pi PCB as the production/default path.

Run the full readiness check with:

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

Default production routing:

```text
Heltec T114 LoRa connector -> region-matched LoRa antenna
Heltec T114 2.4 GHz connector -> additional case-mounted 2.4 GHz antenna
ESP32-S3 DualEye 2.4 GHz connector -> ESP32-S3 2.4 GHz antenna
Raspberry Pi 3B+ -> no required external antenna; optional USB wireless adapter only
```

`scripts/install_pi.sh` runs the aggregate helper after protocol artifact generation, so `bash scripts/flash_all_components.sh --install-firmware` and `bash scripts/flash_all_components.sh --all` generate readiness artifacts without requiring a Raspberry Pi USB wireless adapter.
