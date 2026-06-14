#pragma once

// killerkoala ESP32-S3 DualEye config RevA2
// Confirm exact DualEye audio/display pins against your board revision before relying on hardware wake-word capture.

#define KOALABLUE_FW_VERSION "0.3.0-killerkoala-alwayson"
#define COMPANION_NAME "killerkoala"
#define WAKE_WORD "killerkoala"
#define SERIAL_BAUD 115200

// Feature toggles.
// Mic wake is enabled by default for the killerkoala build. If audio pins are not configured,
// the firmware boots safely and reports that the hardware wake backend needs board-specific pin mapping.
#define ENABLE_LOCAL_BLE_SCAN 1
#define ENABLE_MIC_WAKE       1
#define ENABLE_WAKE_WORD_FILTER 1
#define ENABLE_DISPLAY_STUB   1
#define ENABLE_AUDIO_SPEAKER  1

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
