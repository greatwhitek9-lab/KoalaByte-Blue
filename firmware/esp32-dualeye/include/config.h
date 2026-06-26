#pragma once

// killerkoala ESP32-S3 DualEye config RevA25
// Confirm exact DualEye audio/display/touch pins against your board revision before relying on hardware wake-word capture or direct touch-controller reads.

#define KOALABLUE_FW_VERSION "0.6.1-dualeye-mic-bridge"
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
// ESP32-S3 handles built-in microphone wake/short-command front-end events.
// Raspberry Pi handles larger vocabulary routing, XP/rank state, optional TinyLlama/Ollama banter, and logs.
#define ESP32S3_DUALEYE_BUILTIN_MIC 1
#define ESP32S3_DUALEYE_MIC_ROLE "primary built-in microphone for KillerKoala wake and short voice-command events"
#define ESP32S3_VOICE_FRONTEND_STACK "ESP32-S3 DualEye built-in mic bridge + ESP-SR AFE/VAD/WakeNet plan + Pi voice-command router"
#define ESP32S3_WAKE_MODEL "killerkoala wake phrase over ESP32-S3 DualEye built-in mic event bridge"
#define ESP32S3_COMMAND_MODEL "short command phrases bridged over USB CDC serial to Raspberry Pi"
#define ESP32S3_COMMAND_ALIAS_PACK "firmware/esp32-dualeye/voice_commands/killerkoala_multinet_aliases.csv"
#define KILLERKOALA_COMPANION_BRAIN "Raspberry Pi large-vocabulary Aussie cyberpunk companion engine"
#define KILLERKOALA_RESPONSE_POLICY "anti-repeat rotating vocabulary with XP/rank-aware Aussie terminology"

// Feature toggles.
// Mic wake is enabled by default for the killerkoala build. If audio pins are not configured,
// the firmware boots safely and reports that the built-in mic is present but needs board-specific I2S pin mapping.
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

// Built-in I2S/PDM microphone bridge.
// These are intentionally overridable from PlatformIO build_flags or a board-specific header.
// When the exact DualEye mic pins are confirmed, set these three pins and the firmware will initialize I2S RX.
#ifndef MIC_I2S_BCLK_PIN
#define MIC_I2S_BCLK_PIN  -1
#endif
#ifndef MIC_I2S_WS_PIN
#define MIC_I2S_WS_PIN    -1
#endif
#ifndef MIC_I2S_DIN_PIN
#define MIC_I2S_DIN_PIN   -1
#endif
#define MIC_SAMPLE_RATE_HZ       16000
#define MIC_SAMPLE_BLOCK_SAMPLES 256
#define MIC_WAKE_RMS_THRESHOLD   0.35f
#define MIC_WAKE_COOLDOWN_MS     2500
#define MIC_STATUS_INTERVAL_MS   10000

// Optional speaker path is hardware-revision-specific; use the vendor audio examples before enabling output.
#define SPEAKER_I2S_BCLK_PIN -1
#define SPEAKER_I2S_WS_PIN   -1
#define SPEAKER_I2S_DOUT_PIN -1

// BLE scan behavior.
#define BLE_SCAN_SECONDS 3
#define BLE_MAX_RESULTS_PER_CYCLE 16
