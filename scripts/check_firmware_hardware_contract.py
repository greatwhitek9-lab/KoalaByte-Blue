#!/usr/bin/env python3
"""Fail fast if proven ESP32 DualEye or Heltec T114 hardware contracts drift."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        raise AssertionError(f"missing firmware contract file: {relative}")
    return path.read_text(encoding="utf-8")


def require_lines(relative: str, expected: tuple[str, ...]) -> None:
    text = read(relative)
    missing = [line for line in expected if line not in text]
    if missing:
        raise AssertionError(f"{relative} lost required hardware contract lines: {missing}")


def forbid_lines(relative: str, forbidden: tuple[str, ...]) -> None:
    text = read(relative)
    present = [line for line in forbidden if line in text]
    if present:
        raise AssertionError(f"{relative} contains incompatible alternate hardware macros: {present}")


def require_order(relative: str, markers: tuple[str, ...]) -> None:
    text = read(relative)
    positions = []
    for marker in markers:
        position = text.find(marker)
        if position < 0:
            raise AssertionError(f"{relative} missing ordered build marker: {marker}")
        positions.append(position)
    if positions != sorted(positions):
        raise AssertionError(f"{relative} build stages are out of order: {markers}")


def main() -> int:
    esp32_config = "firmware/esp32-dualeye/include/config.h"
    require_lines(
        esp32_config,
        (
            '#define KOALABLUE_PROTOCOL "menu_sync_v1"',
            '#define KOALABLUE_REPO_PROTOCOL_VERSION "2026.06-menu-sync-v1"',
            '#define DISPLAY_DRIVER "GC9A01A_DUAL_SHARED_SPI"',
            '#define DISPLAY_SPI_MISO_PIN 40',
            '#define DISPLAY_SPI_MOSI_PIN 42',
            '#define DISPLAY_SPI_SCLK_PIN 41',
            '#define DISPLAY_SPI_DC_PIN 45',
            '#define DISPLAY_LCD1_CS_PIN 47',
            '#define DISPLAY_LCD1_RESET_PIN 48',
            '#define DISPLAY_LCD1_BACKLIGHT_PIN 46',
            '#define DISPLAY_LCD2_CS_PIN 38',
            '#define DISPLAY_LCD2_RESET_PIN 8',
            '#define DISPLAY_LCD2_BACKLIGHT_PIN 39',
            '#define DISPLAY_LCD1_ROTATION 1',
            '#define DISPLAY_LCD2_ROTATION 3',
            '#define DISPLAY_SPI_SCLK_HZ 40000000UL',
            '#define KOALA_LCD1_ENABLED 1',
            '#define KOALA_LCD2_ENABLED 1',
            '#define KOALA_HAS_TOUCH 0',
            '#define ENABLE_TOUCH_MENU 0',
            '#define AUDIO_I2S_MCLK_PIN 12',
            '#define AUDIO_I2S_BCLK_PIN 13',
            '#define AUDIO_I2S_WS_PIN 14',
            '#define AUDIO_I2S_DIN_PIN 15',
            '#define AUDIO_I2S_DOUT_PIN 16',
            '#define AUDIO_CODEC_PA_PIN 9',
            '#define AUDIO_CODEC_I2C_SDA_PIN 11',
            '#define AUDIO_CODEC_I2C_SCL_PIN 10',
            '#define AUDIO_CODEC_ES8311_ADDR 0x18',
            '#define AUDIO_CODEC_ES7210_ADDR 0x40',
            '#define MIC_WAKE_RMS_THRESHOLD 0.010f',
            '#define MIC_PCM_CHUNK_BYTES 640',
            '#define MIC_PRE_ROLL_BLOCKS 3',
            '#define SPEAKER_PCM_CHUNK_MAX_BYTES 2048',
            '#define BLE_NODE_SERVICE_UUID "7a6f616c-6162-7974-652d-6475616c6579"',
        ),
    )
    forbid_lines(
        esp32_config,
        (
            "#define LCD1_CS_PIN ",
            "#define LCD2_CS_PIN ",
            "#define LCD_DC_PIN ",
            "#define LCD_RST_PIN ",
            "#define AUDIO_I2C_SDA_PIN ",
            "#define AUDIO_I2S_LRCK_PIN ",
            "#define AUDIO_PA_CTRL_PIN ",
            "#define MIC_WAKE_RMS_THRESHOLD 540.0f",
            "#define SPEAKER_PCM_CHUNK_MAX_BYTES 768",
        ),
    )

    require_lines(
        "firmware/esp32-dualeye/platformio.ini",
        (
            "board = esp32-s3-devkitc-1",
            "board_upload.flash_size = 16MB",
            "board_build.flash_size = 16MB",
            "board_build.arduino.memory_type = qio_opi",
            "board_build.flash_mode = qio",
            "board_build.psram_type = opi",
            "pre:scripts/generate_wake_session_source.py",
            "pre:scripts/patch_complex_capture_preroll.py",
            "-<integrated_main.cpp>",
            "-<integrated_main_clean_voice.cpp>",
        ),
    )
    require_lines(
        "firmware/esp32-dualeye/src/integrated_main_clean_voice.cpp",
        ('#include "integrated_main.cpp"',),
    )

    require_lines(
        "scripts/build_t114_combined_safe.sh",
        ('BOARD="${T114_BOARD:-heltec_t114_v2/nrf52840/uf2}"',),
    )
    require_lines(
        "firmware/t114-combined-safe/prj.conf",
        (
            "CONFIG_BUILD_OUTPUT_UF2=y",
            "CONFIG_USB_CDC_ACM=y",
            "CONFIG_BT_OBSERVER=y",
            "CONFIG_BT_BROADCASTER=y",
            'CONFIG_BT_DEVICE_NAME="KoalaByte-T114"',
        ),
    )
    require_lines(
        "firmware/t114-combined-safe/src/main.c",
        (
            '#define KOALA_DEVICE "heltec-t114-nrf52840"',
            '#define KOALA_FW "0.10.0-t114-smooth-idle-and-speech-mouth"',
            '#define KOALA_BOOT_SPLASH_MS 6000',
        ),
    )
    require_order(
        "firmware/t114-combined-safe/CMakeLists.txt",
        (
            "generate_tone_aware_main.py",
            "patch_protocol_status.py",
            "patch_uf2_bootloader_entry.py",
        ),
    )
    require_lines(
        "firmware/t114-combined-safe/CMakeLists.txt",
        (
            "${KOALABYTE_FINAL_MAIN_SOURCE}",
            "src/original_texture_warp_renderer.c",
            "--expected-bytes 64800",
        ),
    )
    require_lines(
        "scripts/flash_t114_current_uf2.sh",
        (
            "--vector-address 0x26000",
            "--application-min 0x26000",
            "--application-max 0xec000",
            "--family 0x239a0071",
            'EXPECTED_FW="${T114_EXPECTED_FW:-}"',
            "sed -n 's/^#define KOALA_FW",
            'EXPECTED_FW="$(resolve_expected_fw || true)"',
            'payload.get("fw") == expected_fw',
        ),
    )

    payload = {
        "status": "FIRMWARE_HARDWARE_CONTRACT_READY",
        "esp32_target": "verified non-touch ESP32-S3 DualEye 1.28-inch",
        "esp32_pin_map_locked": True,
        "esp32_audio_map_locked": True,
        "t114_target": "heltec_t114_v2/nrf52840/uf2",
        "t114_application_offset": "0x26000",
        "t114_family": "0x239a0071",
        "t114_firmware_identity": "0.10.0-t114-smooth-idle-and-speech-mouth",
        "t114_identity_source": "firmware/t114-combined-safe/src/main.c",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
