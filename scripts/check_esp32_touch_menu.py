#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pi-companion"))

from koalablue.esp32_touch_menu_bridge import Esp32TouchMenuBridge
from koalablue.menu_ui import MenuSelectionScreen

REQUIRED_MARKERS = {
    "firmware/esp32-dualeye/include/config.h": [
        "Waveshare ESP32-S3-DualEye-Touch-LCD-1.28",
        "DISPLAY_DRIVER \"GC9A01\"",
        "DISPLAY_SPI_SCLK_PIN 4",
        "DISPLAY_SPI_MOSI_PIN 2",
        "DISPLAY_SPI_CS_PIN 5",
        "DISPLAY_SPI_DC_PIN 47",
        "DISPLAY_SPI_RESET_PIN 38",
        "DISPLAY_BACKLIGHT_PIN 42",
        "TOUCH_MENU_BACKEND \"waveshare_cst816d_i2c\"",
        "TOUCH_MENU_CONTROLLER \"CST816D\"",
        "TOUCH_MENU_I2C_SDA_PIN 11",
        "TOUCH_MENU_I2C_SCL_PIN 7",
        "TOUCH_MENU_INT_PIN 12",
        "TOUCH_MENU_RST_PIN 6",
        "AUDIO_I2S_MCLK_PIN 16",
        "AUDIO_I2S_WS_PIN 45",
        "AUDIO_I2S_BCLK_PIN 9",
        "AUDIO_I2S_DIN_PIN 10",
        "AUDIO_I2S_DOUT_PIN 8",
    ],
    "firmware/esp32-dualeye/platformio.ini": [
        "board_upload.flash_size = 16MB",
        "board_build.flash_size = 16MB",
        "-DGC9A01_DRIVER",
        "-DTFT_MOSI=2",
        "-DTFT_SCLK=4",
        "-DTFT_CS=5",
        "-DTFT_DC=47",
        "-DTFT_RST=38",
        "-DTFT_BL=42",
    ],
    "docs/ESP32_TOUCH_MENU_CALIBRATION.md": [
        "Waveshare ESP32-S3-DualEye-Touch-LCD-1.28",
        "DISPLAY_DRIVER         GC9A01",
        "TOUCH_MENU_I2C_SDA_PIN GPIO11",
        "TOUCH_MENU_INT_PIN     GPIO12",
    ],
}


def check_markers() -> list[str]:
    failures: list[str] = []
    for relative, markers in REQUIRED_MARKERS.items():
        path = ROOT / relative
        if not path.exists():
            failures.append(f"missing file: {relative}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in markers:
            if marker not in text:
                failures.append(f"{relative} missing {marker}")
    return failures


def main() -> int:
    failures = check_markers()
    menu = MenuSelectionScreen(visible_rows=6)
    bridge = Esp32TouchMenuBridge(menu=menu)
    samples = [
        {"type": "menu_touch", "event": "down", "x": 100, "y": 80, "row": 2},
        {"type": "menu_touch", "event": "up", "x": 100, "y": 80, "row": 2},
        {"type": "menu_touch", "event": "long_press", "x": 100, "y": 120, "row": 3},
    ]
    events = []
    for payload in samples:
        event = bridge.handle_payload(payload)
        if event is not None:
            events.append({"type": event.event_type, "command": event.command, "label": event.selected_label, "index": event.selected_index})
    if not events:
        failures.append("Pi touch menu bridge produced no events")
    print(json.dumps({"status": "ESP32_TOUCH_MENU_READY" if not failures else "ESP32_TOUCH_MENU_INCOMPLETE", "touch_menu_bridge": "ok" if events else "empty", "events": events, "failures": failures}, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
