#pragma once

#define KOALA_TFT_FW_VERSION "0.3.0-heltec-t114-usb-gnss-mouth"
#define KOALA_TFT_SERIAL_BAUD 115200
#define KOALA_FACE_DEFAULT_DURATION_MS 4500
#define KOALA_FACE_NAME "killerkoala"

// Heltec Mesh Node T114 v2 / HT-n5262 color LCD.
// The panel is a 1.14 in ST7789-class TFT with a 240 x 135 landscape window.
#define KOALA_TFT_W 240
#define KOALA_TFT_H 135
#define KOALA_TFT_NATIVE_W 135
#define KOALA_TFT_NATIVE_H 240
#define KOALA_TFT_ROTATION 3
#define KOALA_TFT_SPI_HZ 40000000

// Raw nRF52840 GPIO numbers used by the local Heltec_T114_Board variant.
// These are internal T114 board connections, not Raspberry Pi GPIO wiring.
#define KOALA_TFT_RST 2
#define KOALA_TFT_VDD_CTL 3
#define KOALA_TFT_CS 11
#define KOALA_TFT_DC 12
#define KOALA_TFT_BL 15

// T114 panel power/backlight gates are active-low.
#define KOALA_TFT_POWER_ON_LEVEL LOW
#define KOALA_TFT_BACKLIGHT_ON_LEVEL LOW

// Optional Heltec L76K GNSS add-on on the T114 8-pin 1.25 mm GNSS connector.
// The Pi still connects to the T114 over USB CDC only; GNSS data is forwarded over USB.
#define KOALA_GNSS_ENABLED 1
#define KOALA_GNSS_BAUD 9600
#define KOALA_GNSS_REPORT_MS 1000

// RGB565 color palette.
#define KOALA_COLOR_BG 0x0000
#define KOALA_COLOR_TEXT 0xEFFF
#define KOALA_COLOR_CYAN 0x07FF
#define KOALA_COLOR_GREEN 0x07E0
#define KOALA_COLOR_UV 0xA81F
#define KOALA_COLOR_GREY 0x8410
#define KOALA_COLOR_FUZZ 0xBDF7
#define KOALA_COLOR_NOSE 0x0000
#define KOALA_COLOR_MOUTH 0xFA60
#define KOALA_COLOR_MOUTH_DARK 0x4004
#define KOALA_COLOR_WARNING 0xFD20
#define KOALA_COLOR_ERROR 0xF800
