#pragma once

// KillerKoala ESP32-S3 DualEye config RevA46 sensitive two-stage voice profile.
// Exact target: verified non-touch ESP32-S3 DualEye 1.28-inch variant.

#define KOALABLUE_FW_VERSION "0.9.7-dualeye-sensitive-killerkoala-menu"
#define KOALABLUE_PROTOCOL "menu_sync_v1"
#define KOALABLUE_REPO_PROTOCOL_VERSION "2026.06-menu-sync-v1"
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
#define KOALA_BLE_ROLE "standby_by_default; raspberry_pi_bluez_is_preferred_heltec_node; esp32_is_guarded_fallback"
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
#define KILLERKOALA_COMPANION_BRAIN "KillerKoala local response bank plus Raspberry Pi execution and LLM escalation"
#define KILLERKOALA_RESPONSE_POLICY "ESP32 speaker handles local wake and basic KillerKoala replies; Raspberry Pi handles execution and complex AI replies"
#define ESP32S3_SPEAKER_ROLE "local_wake_and_basic_ai_responses_only"
#define RASPBERRY_PI_SPEAKER_ROLE "menu_results_execution_feedback_and_complex_ai"
#define ENABLE_PI_RESPONSE_STREAM_TO_ESP32 0
#define KILLERKOALA_LOCAL_RESPONSE_COUNT 18
#define KILLERKOALA_LOCAL_VOICE "en-AU-WilliamNeural"

// BLE remains off during normal boot because this hardware previously panicked
// during unrequested controller startup. The Pi BlueZ adapter is the preferred
// Heltec companion node. The Pi may explicitly command a guarded ESP32 fallback
// only when BlueZ is unavailable. A persistent NVS pending marker quarantines BLE
// after a controller-start reset so the eyes cannot enter a reboot loop.
#define ENABLE_LOCAL_BLE_SCAN 1
#define ENABLE_ESP32_BLE_FAILOVER 1
#define KOALA_BLE_NVS_NAMESPACE "koalable"
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

// UINT32_MAX prevents unrequested staged BLE startup. BLE can start only through
// an explicit Pi ble_role=heltec_fallback_ble_node command.
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
#define DISPLAY_SPI_MOSI_PIN 45
#define DISPLAY_SPI_SCLK_PIN 41
#define DISPLAY_SPI_FREQUENCY_HZ 40000000
#define LCD1_CS_PIN 21
#define LCD2_CS_PIN 38
#define LCD_DC_PIN 39
#define LCD_RST_PIN 42
#define LCD_BL_PIN 5
#define LCD_BL_ACTIVE_HIGH 1
#define LCD_BL_LEDC_CHANNEL 7

#define AUDIO_CODEC "ES8311"
#define AUDIO_ADC "ES7210"
#define AUDIO_INPUT_SAMPLE_RATE 16000
#define AUDIO_OUTPUT_SAMPLE_RATE 16000
#define AUDIO_INPUT_BITS 16
#define AUDIO_OUTPUT_BITS 16
#define AUDIO_I2C_SDA_PIN 47
#define AUDIO_I2C_SCL_PIN 48
#define AUDIO_I2S_MCLK_PIN 2
#define AUDIO_I2S_BCLK_PIN 15
#define AUDIO_I2S_LRCK_PIN 16
#define AUDIO_I2S_DOUT_PIN 17
#define AUDIO_I2S_DIN_PIN 18
#define AUDIO_PA_CTRL_PIN 46
#define AUDIO_PA_ACTIVE_HIGH 1
#define ES7210_MIC_GAIN 30
#define MIC_WAKE_RMS_THRESHOLD 540.0f
#define MIC_UTTERANCE_SILENCE_MS 900
#define MIC_UTTERANCE_MAX_MS 8000
#define MIC_PCM_CHUNK_BYTES 640
#define MIC_PRE_ROLL_BLOCKS 3
#define SPEAKER_PCM_CHUNK_MAX_BYTES 768

#define BLE_DEVICE_NAME "KoalaBlue-DualEye"
#define BLE_NODE_SERVICE_UUID "7a1e0001-6d4f-4f61-9f5e-6b6f616c6162"
#define BLE_SCAN_SECONDS 5
