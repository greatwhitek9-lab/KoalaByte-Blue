#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NEEDED=[
"README.md",
"firmware/esp32-dualeye/src/killerkoala_ai_face.h",
"firmware/esp32-dualeye/src/killerkoala_ai_face.cpp",
"firmware/heltec-mouth/README.md",
"firmware/heltec-mouth/boards/heltec_t114.json",
"firmware/heltec-mouth/variants/Heltec_T114_Board/variant.h",
"firmware/heltec-mouth/variants/Heltec_T114_Board/variant.cpp",
"firmware/heltec-mouth/platformio.ini",
"firmware/heltec-mouth/include/config.h",
"firmware/heltec-mouth/src/main.cpp",
"pi-companion/koalablue/killerkoala_face_bridge.py",
"pi-companion/koalablue/killerkoala_voice_face_control.py",
"scripts/run_killerkoala_face_demo.py",
"scripts/flash_heltec_mouth.sh",
]
TEXT={
"firmware/esp32-dualeye/src/killerkoala_ai_face.cpp":["drawEye","eyes only"],
"firmware/heltec-mouth/README.md":["USB-C data cable","Do not wire","L76K GNSS","gnss_nmea"],
"firmware/heltec-mouth/platformio.ini":["board = heltec_t114","board_build.variants_dir = variants","Adafruit ST7735 and ST7789"],
"firmware/heltec-mouth/boards/heltec_t114.json":["HT-n5262","Heltec Mesh Node T114 v2","Heltec_T114_Board"],
"firmware/heltec-mouth/variants/Heltec_T114_Board/variant.h":["PIN_TFT_CS","SX126X_DIO1","PIN_SERIAL1_RX"],
"firmware/heltec-mouth/include/config.h":["KOALA_GNSS_ENABLED","KOALA_GNSS_BAUD","KOALA_GNSS_REPORT_MS"],
"firmware/heltec-mouth/src/main.cpp":["Adafruit_ST7789","Serial.begin","Serial1.begin","gnss_nmea","drawSnout","drawSolidMouth"],
"pi-companion/koalablue/killerkoala_face_bridge.py":["KOALABYTE_HELTEC_USB_PORT","heltec_connection","usb-cdc"],
"scripts/run_menu_screen.py":["emit_selected_action_face"],
}
def main():
    missing=[p for p in NEEDED if not (ROOT/p).exists()]
    for p,words in TEXT.items():
        body=(ROOT/p).read_text(encoding="utf-8",errors="ignore") if (ROOT/p).exists() else ""
        missing += [p+":"+w for w in words if w not in body]
    if missing:
        print("KoalaByte readiness issues:")
        for m in missing: print("- "+m)
        return 1
    print("KoalaByte Blue repo readiness check passed.")
    return 0
if __name__=="__main__": raise SystemExit(main())
