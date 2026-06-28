# Koala Kombat Kruisin’ Node Roles

The corrected Koala Kombat Kruisin’ radio layout is:

```text
Raspberry Pi 3B+       -> main Wi-Fi controller and main BLE node
ESP32-S3 DualEye       -> only secondary Wi-Fi node and second BLE node
Heltec T114 / nRF52840 -> BLE, GNSS, and LoRa node only; not a Wi-Fi node
```

The Heltec T114 does not have Wi-Fi, so it must not be treated as a Wi-Fi survey node.

The role profile lives in:

```text
pi-companion/koalablue/koala_kombat_node_roles.py
```

Smoke-check coverage lives in:

```text
scripts/check_koala_kombat_kruisin.py
```

Expected role policy:

```text
Wi-Fi nodes: raspberry-pi, esp32-s3-dualeye
BLE nodes: raspberry-pi, esp32-s3-dualeye, heltec-t114-nrf52840
GNSS node: heltec-t114-nrf52840
LoRa node: heltec-t114-nrf52840
```
