#pragma once

// killerkoala ESP32-S3 DualEye config RevA28
// Board target: Waveshare ESP32-S3-DualEye-Touch-LCD-1.28.
// Waveshare notes: ESP32-S3R8, 16MB flash, 8MB PSRAM, two 240x240 1.28in LCDs,
// GC9A01 display controller path, CST816D/CST816x I2C touch, ES8311 audio codec,
// ES7210 microphone front-end, onboard ceramic antenna, optional IPEX1 antenna path.
// Compatibility marker for older readiness checks: waveshare_cst816x_i2c.

#define KOALABLUE_FW_VERSION "0.6.5-waveshare-dualeye-onboard-ant"
#define COMPANION_NAME "killerkoala"
#define WAKE_WORD "killerkoala"
#define SERIAL_BAUD 115200

// Active firmware theme package.
#define KOALABLUE_ACTIVE_THEME "jungle_jumanji_eucalyptus"
#define KOALABLUE_THEMES_DIR "firmware/esp32-dualeye/themes"

// ESP32-S3 DualEye 2.4 GHz antenna configuration.
// Default KoalaByte Blue path: leave the Waveshare onboard ceramic antenna path active.
#define ESP32S3_DUALEYE_EXTERNAL_2G4_ANTENNA 0
#define ESP32S3_DUALEYE_2G4_ANTENNA_MODE "onboard_ceramic_default"
#define ESP32S3_DUALEYE_2G4_ANTENNA_CONNECTOR "onboard ceramic 2.4 GHz antenna"
#define ESP32S3_DUALEYE_2G4_WIRING_PATH "factory onboard ceramic antenna path; no case pigtail or bulkhead required"
#define ESP32S3_DUALEYE_VENDOR_SELECTOR_REQUIRED 0

// Voice front-end model plan.
// ESP32-S3 handles built-in microphone wake/short-command front-end events.
// Raspberry Pi handles larger vocabulary routing, XP/rank state, optional TinyLlama/Ollama banter, and logs.
#define ESP32S3_DUALEYE_BUILTIN_MIC 1
#define ESP32S3_DUALEYE_MIC_ROLE "Waveshare ES7210 microphone path for KillerKoala wake and short voice-command events"
#define ESP32S3_VOICE_FRONTEND_STACK "ESP32-S3 DualEye built-in mic bridge + Pi voice-command router"
#define ESP32S3_WAKE_MODEL "killerkoala wake phrase over ESP32-S3 DualEye built-in mic event bridge"
#define ESP32S3_COMMAND_MODEL "short command phrases bridged over USB CDC serial to Raspberry Pi"
#define ESP32S3_COMMAND_ALIAS_PACK "firmware/esp32-dualeye/voice_commands/killerkoala_multinet_aliases.csv"
#define KILLERKOALA_COMPANION_BRAIN "Raspberry Pi large-vocabulary Aussie cyberpunk companion engine"
#define KILLERKOALA_RESPONSE_POLICY "anti-repeat rotating vocabulary with XP/rank-aware Aussie terminology"

// Feature toggles.
#define ENABLE_LOCAL_BLE_SCAN 1
#define ENABLE_KOALA_KOMBAT_WIFI_NODE 1
#define ENABLE_KOALA_KOMBAT_SERIAL_COMMANDS 1
#define ENABLE_MIC_WAKE       1
#define ENABLE_WAKE_WORD_FILTER 1
#define ENABLE_DISPLAY_STUB   0
#define ENABLE_DISPLAY_BOOT_ANIMATION 1
#define ENABLE_AUDIO_SPEAKER  1
#define ENABLE_TOUCH_MENU     1

// Koala Kombat Kruisin' ESP32-S3 survey node behavior.
// The ESP32-S3 acts as a secondary passive Wi-Fi/BLE node and emits JSON over USB CDC.
#define KOALA_KOMBAT_WIFI_SCAN_INTERVAL_MS 15000
#define KOALA_KOMBAT_WIFI_MAX_APS 16
#define KOALA_KOMBAT_WIFI_PASSIVE_SCAN 1

// Waveshare round LCD display path.
#define DISPLAY_DRIVER "GC9A01"
#define DISPLAY_WIDTH 240
#define DISPLAY_HEIGHT 240
#define DISPLAY_MIRROR_X 1
#define DISPLAY_MIRROR_Y 0
#define DISPLAY_SWAP_XY 0
#define DISPLAY_OFFSET_X 0
#define DISPLAY_OFFSET_Y 0
#define DISPLAY_ROTATION 0
#define DISPLAY_INVERT_COLOR 1
#define DISPLAY_SPI_SCLK_PIN 4
#define DISPLAY_SPI_MOSI_PIN 2
#define DISPLAY_SPI_CS_PIN 5
#define DISPLAY_SPI_DC_PIN 47
#define DISPLAY_SPI_RESET_PIN 38
#define DISPLAY_BACKLIGHT_PIN 42
#define DISPLAY_BACKLIGHT_OUTPUT_INVERT 1
#define DISPLAY_SPI_SCLK_HZ 40000000

// Boot animation behavior.
#define BOOT_ANIMATION_TOTAL_MS 2500
#define BOOT_ANIMATION_FRAME_MS 50

// ESP32-side touch menu bridge for Waveshare ESP32-S3-DualEye-Touch-LCD-1.28.
// Waveshare reference pinout: TP_SDA=GPIO11, TP_SCL=GPIO7, TP_RST=GPIO6, TP_INT=GPIO12.
#define TOUCH_MENU_BACKEND "waveshare_cst816d_i2c"
#define TOUCH_MENU_CONTROLLER "CST816D"
#define TOUCH_MENU_I2C_ADDR 0x15
#define TOUCH_MENU_I2C_SDA_PIN 11
#define TOUCH_MENU_I2C_SCL_PIN 7
#define TOUCH_MENU_INT_PIN 12
#define TOUCH_MENU_RST_PIN 6
#define TOUCH_MENU_I2C_CLOCK_HZ 400000
#define TOUCH_MENU_POLL_MS 10
#define TOUCH_MENU_SCREEN_W 240
#define TOUCH_MENU_SCREEN_H 240
#define TOUCH_MENU_RAW_MIN_X 0
#define TOUCH_MENU_RAW_MAX_X 239
#define TOUCH_MENU_RAW_MIN_Y 0
#define TOUCH_MENU_RAW_MAX_Y 239
#define TOUCH_MENU_INVERT_X 0
#define TOUCH_MENU_INVERT_Y 0
#define TOUCH_MENU_SWAP_XY 0
#define TOUCH_MENU_ROW_HEIGHT 40
#define TOUCH_MENU_VISIBLE_ROWS 6
#define TOUCH_MENU_LONG_PRESS_MS 500

// Local fallback buttons. Use -1 to disable a button.
// BOOT is GPIO0 on the Waveshare board; external front-panel buttons are handled by the Pi GPIO extender.
#define BTN_BACK_PIN    -1
#define BTN_SELECT_PIN  0
#define BTN_NEXT_PIN    -1
#define BTN_MENU_PIN    -1
#define BUTTON_ACTIVE_LOW 1

// Waveshare audio pins from vendor board definition.
#define AUDIO_INPUT_SAMPLE_RATE 24000
#define AUDIO_OUTPUT_SAMPLE_RATE 24000
#define AUDIO_I2S_MCLK_PIN 16
#define AUDIO_I2S_WS_PIN 45
#define AUDIO_I2S_BCLK_PIN 9
#define AUDIO_I2S_DIN_PIN 10
#define AUDIO_I2S_DOUT_PIN 8
#define AUDIO_CODEC_PA_PIN 46
#define AUDIO_CODEC_I2C_SDA_PIN 15
#define AUDIO_CODEC_I2C_SCL_PIN 14
#define AUDIO_CODEC_ES8311_ADDR 0x18

#ifndef MIC_I2S_BCLK_PIN
#define MIC_I2S_BCLK_PIN  AUDIO_I2S_BCLK_PIN
#endif
#ifndef MIC_I2S_WS_PIN
#define MIC_I2S_WS_PIN    AUDIO_I2S_WS_PIN
#endif
#ifndef MIC_I2S_DIN_PIN
#define MIC_I2S_DIN_PIN   AUDIO_I2S_DIN_PIN
#endif
#define MIC_SAMPLE_RATE_HZ       24000
#define MIC_SAMPLE_BLOCK_SAMPLES 256
#define MIC_WAKE_RMS_THRESHOLD   0.35f
#define MIC_WAKE_COOLDOWN_MS     2500
#define MIC_STATUS_INTERVAL_MS   10000

#ifndef SPEAKER_I2S_BCLK_PIN
#define SPEAKER_I2S_BCLK_PIN AUDIO_I2S_BCLK_PIN
#endif
#ifndef SPEAKER_I2S_WS_PIN
#define SPEAKER_I2S_WS_PIN   AUDIO_I2S_WS_PIN
#endif
#ifndef SPEAKER_I2S_DOUT_PIN
#define SPEAKER_I2S_DOUT_PIN AUDIO_I2S_DOUT_PIN
#endif

// Battery/power pins from vendor board definition. KoalaByte still uses the Pi power bank as primary power.
#define BATTERY_ADC_PIN 1
#define BATTERY_CHARGING_PIN 41

// BLE scan behavior.
#define BLE_SCAN_SECONDS 3
#define BLE_MAX_RESULTS_PER_CYCLE 16
