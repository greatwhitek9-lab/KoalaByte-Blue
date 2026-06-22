# Heltec Mesh Node T114 v2 color mouth display

This firmware target is for the Heltec Mesh Node T114 v2 / HT-n5262 board with nRF52840, SX1262, USB-C, and the 1.14 inch color TFT display.

## Pi connection

Connect the Heltec T114 to the Raspberry Pi with a USB-C data cable. Do not wire the Heltec serial pins to the Pi GPIO header for the KillerKoala face channel.

The Pi sends newline-delimited JSON face commands over the Heltec USB CDC serial device. The Pi-side bridge checks these environment variables first:

- `KOALABYTE_HELTEC_USB_PORT`
- `KOALABYTE_HELTEC_FACE_PORT`
- `HELTEC_PORT`

When none are set, the bridge searches common USB serial paths such as `/dev/serial/by-id/*`, `/dev/ttyACM*`, and `/dev/ttyUSB*`.

## Build and flash

```bash
BUILD_ONLY=1 scripts/flash_heltec_mouth.sh
HELTEC_PORT=/dev/ttyACM0 scripts/flash_heltec_mouth.sh
```

The PlatformIO environment is `heltec_t114_mouth` and uses the local `heltec_t114` board definition plus the `Heltec_T114_Board` Arduino variant.

## Display behavior

The T114 color TFT renders only the lower koala face channel: fuzzy grey cheeks, black nose, and a solid orange animated mouth. The ESP32-S3 DualEye board renders only the eyes. Both devices receive the same face state from the Pi so the eye and mouth motion stay synchronized.
