#pragma once

// killerkoala ESP32-S3 DualEye config RevA24
// Confirm exact DualEye audio/display/touch pins against your board revision before relying on hardware wake-word capture or direct touch-controller reads.

#define KOALABLUE_FW_VERSION "0.6.0-touch-menu"
#define COMPANION_NAME "killerkoala"
#define WAKE_WORD "killerkoala"
#define SERIAL_BAUD 115200

// Active firmware theme package.
#define KOALABLUE_ACTIVE_THEME "jungle_jumanji_eucalyptus"
#define KOALABLUE_THEMES_DIR "firmware/esp32-dualeye/themes"

// ESP32-S3 DualEye 2.4 GHz antenna configuration.
// This applies to the ESP32-S3 DualEye board only.
// Use the external-antenna board variant, or set the vendor-documented antenna selector resistor/jumper for IPEX/U.FL use.
#define ESP32S3_DUALEYE_EXTERNAL_2G4_ANTENNA 1
#define ESP32S3_DUALEYE_2G4_ANTENNA_MODE "external_connector"
#define ESP32S3_DUALEYE_2G4_ANTENNA_CONNECTOR "IPEX1/U.FL/MHF1 2.4 GHz connector"
#define ESP32S3_DUALEYE_2G4_WIRING_PATH "ESP32-S3 DualEye IPEX1/U.FL/MHF1 -> IPEX/U.FL pigtail -> SMA/RP-SMA bulkhead -> 2.4 GHz antenna"
#define ESP32S3_DUALEYE_VENDOR_SELECTOR_REQUIRED 1

// Voice front-end model plan.
// ESP32-S3 handles wake/short-command recognition; Raspberry Pi handles large-vocabulary companion responses.
#define ESP32S3_VOICE_FRONTEND_STACK "ESP-SR AFE/VAD + WakeNet9 + MultiNet7 Q8 English"
#define ESP32S3_WAKE_MODEL "WakeNet9 custom wake word: killerkoala"
#define ESP32S3_COMMAND_MODEL "MultiNet7 Q8 English command aliases"
#define ESP32S3_COMMAND_ALIAS_PACK "firmware/esp32-dualeye/voice_commands/killerkoala_multinet_aliases.csv"
#define KILLERKOALA_COMPANION_BRAIN "Raspberry Pi large-vocabulary Aussie cyberpunk companion engine"
#define KILLERKOALA_RESPONSE_POLICY "anti-repeat rotating vocabulary with XP/rank-aware Aussie terminology"

// Feature toggles.
// Mic wake is enabled by default for the killerkoala build. If audio pins are not configured,
// the firmware boots safely and reports that the hardware wake backend needs board-specific pin mapping.
#define ENABLE_LOCAL_BLE_SCAN 1
#define ENABLE_MIC_WAKE       1
#define ENABLE_WAKE_WORD_FILTER 1
#define ENABLE_DISPLAY_STUB   0
#define ENABLE_DISPLAY_BOOT_ANIMATION 1
#define ENABLE_AUDIO_SPEAKER  1
#define ENABLE_TOUCH_MENU     1

// Boot animation behavior.
#define BOOT_ANIMATION_TOTAL_MS 2500
#define BOOT_ANIMATION_FRAME_MS 50
#define DISPLAY_ROTATION 0

// ESP32-side touch menu bridge.
// Default backend is serial_calibrated because the DualEye touch controller/pins vary by board revision.
// When exact touch-controller wiring is confirmed, feed raw samples as raw_touch JSON or replace the backend reader.
#define TOUCH_MENU_BACKEND "serial_calibrated"
#define TOUCH_MENU_SCREEN_W 240
#define TOUCH_MENU_SCREEN_H 240
#define TOUCH_MENU_RAW_MIN_X 0
#define TOUCH_MENU_RAW_MAX_X 4095
#define TOUCH_MENU_RAW_MIN_Y 0
#define TOUCH_MENU_RAW_MAX_Y 4095
#define TOUCH_MENU_INVERT_X 0
#define TOUCH_MENU_INVERT_Y 0
#define TOUCH_MENU_SWAP_XY 0
#define TOUCH_MENU_ROW_HEIGHT 40
#define TOUCH_MENU_VISIBLE_ROWS 6
#define TOUCH_MENU_LONG_PRESS_MS 750

// Buttons. Use -1 to disable a button.
#define BTN_BACK_PIN    0
#define BTN_SELECT_PIN  1
#define BTN_NEXT_PIN    2
#define BTN_MENU_PIN    3
#define BUTTON_ACTIVE_LOW 1

// I2S microphone pins: set to the correct DualEye schematic/example values for real audio wake capture.
#define MIC_I2S_BCLK_PIN  -1
#define MIC_I2S_WS_PIN    -1
#define MIC_I2S_DIN_PIN   -1
#define MIC_WAKE_RMS_THRESHOLD 0.35f
#define MIC_WAKE_COOLDOWN_MS   2500

// Optional speaker path is hardware-revision-specific; use the vendor audio examples before enabling output.
#define SPEAKER_I2S_BCLK_PIN -1
#define SPEAKER_I2S_WS_PIN   -1
#define SPEAKER_I2S_DOUT_PIN -1

// BLE scan behavior.
#define BLE_SCAN_SECONDS 3
#define BLE_MAX_RESULTS_PER_CYCLE 16
