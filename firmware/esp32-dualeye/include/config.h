#pragma once

// KillerKoala ESP32-S3 DualEye config RevA45 William/K1-K8/full-menu voice profile.
// Exact target: verified non-touch ESP32-S3 DualEye 1.28-inch variant.

#define KOALABLUE_FW_VERSION "0.9.6-dualeye-william-menu-voice"
#define COMPANION_NAME "killerkoala"
#define WAKE_WORD "killerkoala"
#define WAKE_WORD_ALTERNATE "hey killerkoala"
#define SERIAL_BAUD 115200
#define KOALABLUE_ACTIVE_THEME "killerkoala_realistic_cyber_fur"
#define KOALABLUE_THEMES_DIR "firmware/esp32-dualeye/themes"
#define KOALA_RECOVERY_PROFILE 0
#define KOALA_HAS_TOUCH 0

#define KOALA_EXPRESSION_SYNC_COORDINATOR "raspberry-pi"
#define KOALA_EXPRESSION_SYNC_MODE "pi_fanout"
#define KOALA_EXPRESSION_SYNC_REQUIRES_BLE 0
#define KOALA_BLE_ROLE "disabled_on_esp32; heltec_t114_is_ble_controller_and_raspberry_pi_is_its_ble_node"
#define KOALA_WIFI_ROLE "pi_command_telemetry_and_execution_node"
#define KOALA_EXECUTION_OWNER "raspberry-pi"

#define ESP32S3_DUALEYE_EXTERNAL_2G4_ANTENNA 0
#define ESP32S3_DUALEYE_2G4_ANTENNA_MODE "onboard_ceramic_default"
#define ESP32S3_DUALEYE_2G4_ANTENNA_CONNECTOR "onboard ceramic 2.4 GHz antenna"
#define ESP32S3_DUALEYE_2G4_WIRING_PATH "factory onboard ceramic antenna path"
#define ESP32S3_DUALEYE_VENDOR_SELECTOR_REQUIRED 0
#define ESP32S3_DUALEYE_BUILTIN_MIC 1
#define ESP32S3_DUALEYE_MIC_ROLE "ES7210 adaptive stereo channel probe; ESP-SR local phrases plus explicit complex PCM escalation"
#define ESP32S3_VOICE_FRONTEND_STACK "ESP32-S3 ES7210 + Arduino ESP_SR English MultiNet adaptive local-first router"
#define ESP32S3_WAKE_MODEL "always-on local MultiNet phrase detection for killer koala and hey killer koala"
#define ESP32S3_COMMAND_MODEL "K1-K8 plus every visible menu and submenu label are recognized locally; Pi executes leaf actions"
#define ESP32S3_COMMAND_ALIAS_PACK "generated from pi-companion/koalablue/menu_catalog.py at firmware build time"
#define KILLERKOALA_COMPANION_BRAIN "ESP32 William response bank plus Raspberry Pi execution and LLM escalation"
#define KILLERKOALA_RESPONSE_POLICY "ESP32 speaker handles local wake and basic William replies; Raspberry Pi handles execution and complex AI replies"
#define ESP32S3_SPEAKER_ROLE "local_wake_and_basic_ai_responses_only"
#define RASPBERRY_PI_SPEAKER_ROLE "menu_results_execution_feedback_and_complex_ai"
#define ENABLE_PI_RESPONSE_STREAM_TO_ESP32 0
#define KILLERKOALA_LOCAL_RESPONSE_COUNT 18
#define KILLERKOALA_LOCAL_VOICE "en-AU-WilliamNeural"

// Bluetooth is intentionally disabled on this ESP32-S3 hardware profile. Physical
// validation showed a LoadProhibited panic inside controller startup. Heltec T114
// remains the primary BLE controller and the Raspberry Pi is its BLE node/peer.
#define ENABLE_LOCAL_BLE_SCAN 0
#define ENABLE_KOALA_KOMBAT_WIFI_NODE 1
#define ENABLE_KOALA_KOMBAT_SERIAL_COMMANDS 1
#define ENABLE_MIC_WAKE 1
#define ENABLE_WAKE_WORD_FILTER 1
#define ENABLE_ESP_SR_LOCAL_COMMANDS 1
#define ENABLE_LOCAL_AI_RESPONSES 1
#define ENABLE_DISPLAY_STUB 0
#define ENABLE_DISPLAY_BOOT_ANIMATION 1
#define ENABLE_AUDIO_SPEAKER 1
#define ENABLE_TOUCH_MENU 0

// UINT32_MAX prevents the legacy unguarded staged BLE initializer from running.
// Wi-Fi, USB CDC, microphone, speaker and local ESP-SR staging remain active.
#define SUBSYSTEM_BLE_START_MS 0xFFFFFFFFUL
#define SUBSYSTEM_WIFI_START_MS 11000UL
#define SUBSYSTEM_AUDIO_START_MS 14500UL
#define SUBSYSTEM_READY_MIN_FREE_HEAP 90000UL
#define KOALA_KOMBAT_WIFI_SCAN_INTERVAL_MS 30000UL
#define KOALA_KOMBAT_WIFI_MAX_APS 16
#define KOALA_KOMBAT_WIFI_PASSIVE_SCAN 1
#define KOALA_WIFI_CONNECT_TIMEOUT_MS 15000UL
#define KOALA_WIFI_RETRY_INTERVAL_MS 20000UL
#define KOALA_PI_UDP_DEFAULT_PORT 42110
#define KOALA_ESP32_UDP_LISTEN_PORT 42111
#define KOALA_WIFI_NVS_NAMESPACE "koalapi"
#define KOALA_WIFI_DEVICE_NAME "KoalaBlue-DualEye"

#define DISPLAY_DRIVER "GC9A01A_DUAL_SHARED_SPI"
#define DISPLAY_WIDTH 240
#define DISPLAY_HEIGHT 240
#define DISPLAY_SPI_MISO_PIN 40
#define DISPLAY_SPI_MOSI_PIN 42
#define DISPLAY_SPI_SCLK_PIN 41
#define DISPLAY_SPI_DC_PIN 45
#define DISPLAY_LCD1_CS_PIN 47
#define DISPLAY_LCD1_RESET_PIN 48
#define DISPLAY_LCD1_BACKLIGHT_PIN 46
#define DISPLAY_LCD2_CS_PIN 38
#define DISPLAY_LCD2_RESET_PIN 8
#define DISPLAY_LCD2_BACKLIGHT_PIN 39
#define DISPLAY_LCD1_ROTATION 1
#define DISPLAY_LCD2_ROTATION 3
#define DISPLAY_INVERT_COLOR 1
#define DISPLAY_SPI_SCLK_HZ 40000000UL
#define KOALA_LCD1_ENABLED 1
#define KOALA_LCD2_ENABLED 1
#define KOALA_PRIMARY_DISPLAY 2
#define KOALA_PRIMARY_DISPLAY_POSITION "front_right_back_left"
#define KOALA_CRITICAL_UI_PRIMARY_ONLY 0
#define KOALA_TEXT_INPUT_PRIMARY_ONLY 0
#define KOALA_MIRROR_ACTION_ANIMATIONS 1
#define KOALA_ALLOW_MISSING_LCD1 1
#define KOALA_ACTIVE_TOUCH_DISPLAY 0
#define KOALA_EYE_RENDER_FPS 30
#define KOALA_EYE_CANVAS_SIZE 200
#define BOOT_ANIMATION_TOTAL_MS 6000
#define BOOT_ANIMATION_FRAME_MS 33

// Legacy readiness token: waveshare_cst816x_i2c is intentionally disabled.
// This verified board has no touch controller or touch panel.
#define TOUCH_MENU_BACKEND "disabled_non_touch_hardware"
#define TOUCH_MENU_CONTROLLER "none"
#define TOUCH_MENU_I2C_ADDR 0x00
#define TOUCH_MENU_I2C_SDA_PIN -1
#define TOUCH_MENU_I2C_SCL_PIN -1
#define TOUCH_MENU_INT_PIN -1
#define TOUCH_MENU_RST_PIN -1
#define TOUCH_MENU_I2C_CLOCK_HZ 100000
#define TOUCH_MENU_POLL_MS 1000
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

#define BTN_BACK_PIN -1
#define BTN_SELECT_PIN 0
#define BTN_NEXT_PIN -1
#define BTN_MENU_PIN -1
#define BUTTON_ACTIVE_LOW 1

#define AUDIO_INPUT_SAMPLE_RATE 16000
#define AUDIO_OUTPUT_SAMPLE_RATE 16000
#define AUDIO_I2S_MCLK_PIN 12
#define AUDIO_I2S_BCLK_PIN 13
#define AUDIO_I2S_WS_PIN 14
#define AUDIO_I2S_DIN_PIN 15
#define AUDIO_I2S_DOUT_PIN 16
#define AUDIO_CODEC_PA_PIN 9
#define AUDIO_CODEC_I2C_SDA_PIN 11
#define AUDIO_CODEC_I2C_SCL_PIN 10
#define AUDIO_CODEC_ES8311_ADDR 0x18
#define AUDIO_CODEC_ES7210_ADDR 0x40
#define AUDIO_MCLK_MULTIPLE 256
#define AUDIO_OUTPUT_VOLUME 68
#define MIC_I2S_BCLK_PIN AUDIO_I2S_BCLK_PIN
#define MIC_I2S_WS_PIN AUDIO_I2S_WS_PIN
#define MIC_I2S_DIN_PIN AUDIO_I2S_DIN_PIN
#define MIC_SAMPLE_RATE_HZ AUDIO_INPUT_SAMPLE_RATE
#define MIC_SAMPLE_BLOCK_SAMPLES 320
#define MIC_WAKE_RMS_THRESHOLD 0.015f
#define MIC_WAKE_COOLDOWN_MS 1800UL
#define MIC_STATUS_INTERVAL_MS 10000UL
#define MIC_UTTERANCE_SILENCE_MS 900UL
#define MIC_UTTERANCE_MAX_MS 6500UL
#define MIC_PRE_ROLL_BLOCKS 3
#define MIC_PCM_CHUNK_BYTES 640
#define SPEAKER_I2S_BCLK_PIN AUDIO_I2S_BCLK_PIN
#define SPEAKER_I2S_WS_PIN AUDIO_I2S_WS_PIN
#define SPEAKER_I2S_DOUT_PIN AUDIO_I2S_DOUT_PIN
#define SPEAKER_PCM_CHUNK_MAX_BYTES 2048

#define BATTERY_ADC_PIN 1
#define BATTERY_CHARGING_PIN -1
#define BLE_SCAN_SECONDS 3
#define BLE_MAX_RESULTS_PER_CYCLE 16
#define BLE_SCAN_INTERVAL_MS 15000UL
#define BLE_DEVICE_NAME "KoalaBlue-DualEye"
#define BLE_NODE_SERVICE_UUID "7a6f616c-6162-7974-652d-6475616c6579"
