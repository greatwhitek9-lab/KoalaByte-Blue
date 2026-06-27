#include <Arduino.h>
#include <ArduinoJson.h>
#include <NimBLEDevice.h>
#include <driver/i2s.h>
#include <math.h>
#include "boot_animation.h"
#include "config.h"
#include "koalagotchi_mode_screens.h"

struct ButtonDef {
  const char *name;
  int pin;
  bool last;
  uint32_t lastChange;
};

ButtonDef buttons[] = {
  {"back", BTN_BACK_PIN, true, 0},
  {"select", BTN_SELECT_PIN, true, 0},
  {"next", BTN_NEXT_PIN, true, 0},
  {"menu", BTN_MENU_PIN, true, 0},
};

static uint32_t lastBleScan = 0;
static uint32_t lastHeartbeat = 0;
static uint32_t lastVoiceWake = 0;
static uint32_t lastVoiceStatus = 0;
static bool micBackendReady = false;
static const char *micBackendStatus = "not_initialized";
static const char *micBackendReason = "setupMic has not run";

void sendJson(JsonDocument &doc) {
  serializeJson(doc, Serial);
  Serial.println();
}

void emitStatus(const char *message) {
  StaticJsonDocument<256> doc;
  doc["type"] = "status";
  doc["device"] = "esp32-dualeye";
  doc["message"] = message;
  sendJson(doc);
}

bool micPinsConfigured() {
  return MIC_I2S_BCLK_PIN >= 0 && MIC_I2S_WS_PIN >= 0 && MIC_I2S_DIN_PIN >= 0;
}

void emitMicStatus(const char *statusType = "voice_backend") {
  StaticJsonDocument<768> doc;
  doc["type"] = statusType;
  doc["device"] = "esp32-dualeye";
  doc["mic"] = "esp32_s3_dualeye_builtin_mic";
  doc["builtin_mic_present"] = ESP32S3_DUALEYE_BUILTIN_MIC;
  doc["role"] = ESP32S3_DUALEYE_MIC_ROLE;
  doc["status"] = micBackendStatus;
  doc["ready"] = micBackendReady;
  doc["wake_word"] = WAKE_WORD;
  doc["front_end"] = ESP32S3_VOICE_FRONTEND_STACK;
  doc["command_model"] = ESP32S3_COMMAND_MODEL;
  doc["sample_rate_hz"] = MIC_SAMPLE_RATE_HZ;
  doc["pins_configured"] = micPinsConfigured();
  doc["bclk_pin"] = MIC_I2S_BCLK_PIN;
  doc["ws_pin"] = MIC_I2S_WS_PIN;
  doc["din_pin"] = MIC_I2S_DIN_PIN;
  doc["reason"] = micBackendReason;
  doc["pi_bridge"] = "koalablue.esp32_dualeye_voice_bridge";
  sendJson(doc);
}

void emitAntennaStatus() {
  StaticJsonDocument<512> doc;
  doc["type"] = "antenna_status";
  doc["device"] = "esp32-dualeye";
  doc["radio"] = "2.4GHz WiFi/Bluetooth";
  doc["external_antenna"] = ESP32S3_DUALEYE_EXTERNAL_2G4_ANTENNA;
  doc["mode"] = ESP32S3_DUALEYE_2G4_ANTENNA_MODE;
  doc["connector"] = ESP32S3_DUALEYE_2G4_ANTENNA_CONNECTOR;
  doc["wiring_path"] = ESP32S3_DUALEYE_2G4_WIRING_PATH;
  doc["selector_required"] = ESP32S3_DUALEYE_VENDOR_SELECTOR_REQUIRED;
  sendJson(doc);
}

void emitVoiceStackStatus() {
  StaticJsonDocument<1024> doc;
  doc["type"] = "voice_stack";
  doc["device"] = "esp32-dualeye";
  doc["wake_word"] = WAKE_WORD;
  doc["front_end"] = ESP32S3_VOICE_FRONTEND_STACK;
  doc["wake_model"] = ESP32S3_WAKE_MODEL;
  doc["command_model"] = ESP32S3_COMMAND_MODEL;
  doc["alias_pack"] = ESP32S3_COMMAND_ALIAS_PACK;
  doc["companion_brain"] = KILLERKOALA_COMPANION_BRAIN;
  doc["response_policy"] = KILLERKOALA_RESPONSE_POLICY;
  doc["builtin_mic_present"] = ESP32S3_DUALEYE_BUILTIN_MIC;
  doc["mic_ready"] = micBackendReady;
  doc["mic_status"] = micBackendStatus;
  sendJson(doc);
}

void emitEyeStyleStatus(const char *statusType = "eye_style") {
  StaticJsonDocument<384> doc;
  doc["type"] = statusType;
  doc["device"] = "esp32-dualeye";
  doc["look"] = getKoalagotchiEyeLook();
  doc["animation"] = getKoalagotchiEyeAnimation();
  doc["left_color"] = getKoalagotchiLeftEyeHex();
  doc["right_color"] = getKoalagotchiRightEyeHex();
  doc["brightness"] = getKoalagotchiEyeBrightness();
  doc["accepted_looks"] = "round,cyber,slit,sleepy,angry,star,heart,x";
  doc["accepted_animations"] = "static,idle,pulse,blink,scan,glitch,sleepy";
  sendJson(doc);
}

void emitBoot() {
  StaticJsonDocument<1024> doc;
  doc["type"] = "boot";
  doc["device"] = "esp32-dualeye";
  doc["fw"] = KOALABLUE_FW_VERSION;
  doc["companion"] = COMPANION_NAME;
  doc["wake_word"] = WAKE_WORD;
  doc["ble_scan"] = ENABLE_LOCAL_BLE_SCAN;
  doc["mic_wake"] = ENABLE_MIC_WAKE;
  doc["builtin_mic_present"] = ESP32S3_DUALEYE_BUILTIN_MIC;
  doc["mic_ready"] = micBackendReady;
  doc["mic_status"] = micBackendStatus;
  doc["display_stub"] = ENABLE_DISPLAY_STUB;
  doc["boot_animation"] = ENABLE_DISPLAY_BOOT_ANIMATION;
  doc["custom_animated_eyes"] = 1;
  doc["voice_front_end"] = ESP32S3_VOICE_FRONTEND_STACK;
  doc["command_model"] = ESP32S3_COMMAND_MODEL;
  doc["companion_brain"] = KILLERKOALA_COMPANION_BRAIN;
  doc["esp32_2g4_antenna"] = ESP32S3_DUALEYE_2G4_ANTENNA_MODE;
  doc["esp32_external_antenna"] = ESP32S3_DUALEYE_EXTERNAL_2G4_ANTENNA;
  sendJson(doc);
  emitAntennaStatus();
  emitVoiceStackStatus();
  emitMicStatus();
  emitEyeStyleStatus();
}

void setupButtons() {
  for (auto &b : buttons) {
    if (b.pin >= 0) {
      pinMode(b.pin, BUTTON_ACTIVE_LOW ? INPUT_PULLUP : INPUT_PULLDOWN);
      b.last = digitalRead(b.pin);
      b.lastChange = millis();
    }
  }
}

void pollButtons() {
  const uint32_t now = millis();
  for (auto &b : buttons) {
    if (b.pin < 0) continue;
    bool v = digitalRead(b.pin);
    if (v != b.last && (now - b.lastChange) > 35) {
      b.last = v;
      b.lastChange = now;
      bool pressed = BUTTON_ACTIVE_LOW ? (v == LOW) : (v == HIGH);
      StaticJsonDocument<160> doc;
      doc["type"] = "button";
      doc["button"] = b.name;
      doc["state"] = pressed ? "pressed" : "released";
      sendJson(doc);
    }
  }
}

#if ENABLE_LOCAL_BLE_SCAN
class KoalaAdvertisedDeviceCallbacks : public NimBLEAdvertisedDeviceCallbacks {
  void onResult(NimBLEAdvertisedDevice *d) override {
    StaticJsonDocument<384> doc;
    doc["type"] = "ble_seen";
    doc["name"] = d->haveName() ? d->getName().c_str() : "";
    doc["addr"] = d->getAddress().toString().c_str();
    doc["rssi"] = d->getRSSI();
    doc["connectable"] = d->isConnectable();
    doc["source"] = "esp32_local_scan";
    sendJson(doc);
  }
};

void setupBle() {
  NimBLEDevice::init("KoalaBlue-DualEye");
  NimBLEScan *scan = NimBLEDevice::getScan();
  scan->setAdvertisedDeviceCallbacks(new KoalaAdvertisedDeviceCallbacks(), true);
  scan->setActiveScan(false);
  scan->setInterval(120);
  scan->setWindow(80);
}

void runBleScanCycle() {
  if (millis() - lastBleScan < 7000) return;
  lastBleScan = millis();
  NimBLEScan *scan = NimBLEDevice::getScan();
  emitStatus("ble_scan_start");
  scan->start(BLE_SCAN_SECONDS, false);
  scan->clearResults();
  emitStatus("ble_scan_done");
}
#endif

void setupMic() {
#if ENABLE_MIC_WAKE
  if (!ESP32S3_DUALEYE_BUILTIN_MIC) {
    micBackendReady = false;
    micBackendStatus = "disabled_no_builtin_mic";
    micBackendReason = "ESP32S3_DUALEYE_BUILTIN_MIC is disabled";
    emitMicStatus();
    return;
  }
  if (!micPinsConfigured()) {
    micBackendReady = false;
    micBackendStatus = "builtin_mic_pin_mapping_required";
    micBackendReason = "Built-in mic bridge is enabled; set MIC_I2S_BCLK_PIN, MIC_I2S_WS_PIN, and MIC_I2S_DIN_PIN for this DualEye board revision.";
    emitMicStatus();
    return;
  }

  i2s_config_t i2s_config = {};
  i2s_config.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
  i2s_config.sample_rate = MIC_SAMPLE_RATE_HZ;
  i2s_config.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;
  i2s_config.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;
#if defined(I2S_COMM_FORMAT_STAND_I2S)
  i2s_config.communication_format = I2S_COMM_FORMAT_STAND_I2S;
#else
  i2s_config.communication_format = I2S_COMM_FORMAT_I2S;
#endif
  i2s_config.intr_alloc_flags = 0;
  i2s_config.dma_buf_count = 4;
  i2s_config.dma_buf_len = MIC_SAMPLE_BLOCK_SAMPLES;
  i2s_config.use_apll = false;
  i2s_config.tx_desc_auto_clear = false;
  i2s_config.fixed_mclk = 0;

  i2s_pin_config_t pin_config = {};
  pin_config.bck_io_num = MIC_I2S_BCLK_PIN;
  pin_config.ws_io_num = MIC_I2S_WS_PIN;
  pin_config.data_out_num = I2S_PIN_NO_CHANGE;
  pin_config.data_in_num = MIC_I2S_DIN_PIN;

  esp_err_t err = i2s_driver_install(I2S_NUM_0, &i2s_config, 0, nullptr);
  if (err != ESP_OK) {
    micBackendReady = false;
    micBackendStatus = "i2s_driver_install_failed";
    micBackendReason = "ESP32 I2S driver install failed";
    emitMicStatus();
    return;
  }

  err = i2s_set_pin(I2S_NUM_0, &pin_config);
  if (err != ESP_OK) {
    i2s_driver_uninstall(I2S_NUM_0);
    micBackendReady = false;
    micBackendStatus = "i2s_pin_config_failed";
    micBackendReason = "ESP32 I2S pin config failed";
    emitMicStatus();
    return;
  }

  i2s_zero_dma_buffer(I2S_NUM_0);
  micBackendReady = true;
  micBackendStatus = "builtin_mic_i2s_ready";
  micBackendReason = "ESP32-S3 DualEye built-in mic I2S RX initialized";
  emitMicStatus();
#else
  micBackendReady = false;
  micBackendStatus = "disabled";
  micBackendReason = "ENABLE_MIC_WAKE is disabled";
#endif
}

float sampleMicRms() {
#if ENABLE_MIC_WAKE
  if (!micBackendReady) return 0.0f;
  int32_t samples[MIC_SAMPLE_BLOCK_SAMPLES];
  size_t bytesRead = 0;
  esp_err_t err = i2s_read(I2S_NUM_0, samples, sizeof(samples), &bytesRead, 0);
  if (err != ESP_OK || bytesRead == 0) return 0.0f;

  const size_t count = bytesRead / sizeof(int32_t);
  if (count == 0) return 0.0f;
  double sumSquares = 0.0;
  for (size_t i = 0; i < count; ++i) {
    const float normalized = (float)(samples[i] >> 14) / 131072.0f;
    sumSquares += (double)normalized * (double)normalized;
  }
  return sqrt(sumSquares / (double)count);
#else
  return 0.0f;
#endif
}

void emitVoiceWakeEvent(float rms, const char *source) {
  StaticJsonDocument<256> doc;
  doc["type"] = "voice_wake";
  doc["name"] = COMPANION_NAME;
  doc["wake_word"] = WAKE_WORD;
  doc["phrase"] = WAKE_WORD;
  doc["rms"] = rms;
  doc["source"] = source;
  doc["mic"] = "esp32_s3_dualeye_builtin_mic";
  sendJson(doc);
}

void emitVoiceCommandEvent(const char *phrase, const char *source) {
  StaticJsonDocument<384> doc;
  doc["type"] = "voice_command";
  doc["name"] = COMPANION_NAME;
  doc["wake_word"] = WAKE_WORD;
  doc["phrase"] = phrase;
  doc["source"] = source;
  doc["mic"] = "esp32_s3_dualeye_builtin_mic";
  doc["route_to_pi"] = true;
  sendJson(doc);
}

void pollVoiceWake() {
#if ENABLE_MIC_WAKE
  if (millis() - lastVoiceStatus > MIC_STATUS_INTERVAL_MS) {
    lastVoiceStatus = millis();
    emitMicStatus("voice_backend_heartbeat");
  }
  float rms = sampleMicRms();
  if (rms >= MIC_WAKE_RMS_THRESHOLD && millis() - lastVoiceWake > MIC_WAKE_COOLDOWN_MS) {
    lastVoiceWake = millis();
    emitVoiceWakeEvent(rms, "esp32_s3_dualeye_builtin_mic_i2s");
  }
#endif
}

void handleKillerKoalaFace(JsonDocument &doc) {
  const char *state = doc["state"] | "listening";
  const char *left = doc["left_eye"] | "#A54BFF";
  const char *right = doc["right_eye"] | "#32FF71";
  int brightness = doc["brightness"] | getKoalagotchiEyeBrightness();
  const bool enabled = doc["enabled"] | true;
  const char *look = "round";
  const char *animation = "idle";

  if (!enabled || !strcmp(state, "hidden")) {
    animation = "sleepy";
  } else if (!strcmp(state, "wake")) {
    animation = "pulse";
  } else if (!strcmp(state, "thinking")) {
    animation = "scan";
  } else if (!strcmp(state, "speaking")) {
    animation = "blink";
  } else if (!strcmp(state, "action")) {
    animation = "glitch";
  } else if (!strcmp(state, "success")) {
    look = "star";
    animation = "pulse";
  } else if (!strcmp(state, "error")) {
    look = "angry";
    animation = "glitch";
  }

  setKoalagotchiEyeStyle(look, left, right, animation, brightness);
  drawKoalagotchiModeScreen("killerkoala", state, 85, 92);

  StaticJsonDocument<288> ack;
  ack["type"] = "killerkoala_eye_ack";
  ack["device"] = "esp32-dualeye";
  ack["state"] = state;
  ack["left_eye"] = left;
  ack["right_eye"] = right;
  ack["animation"] = animation;
  ack["mouth_sync"] = "killerkoala_face";
  sendJson(ack);
}

void handleMenuSync(JsonDocument &doc) {
  const char *label = doc["selected_label"] | "menu";
  const char *command = doc["selected_command"] | "";
  const char *eventType = doc["event_type"] | "highlight";
  const int position = doc["selected_position"] | 1;
  const int total = doc["total_items"] | 1;
  char mood[96];
  snprintf(mood, sizeof(mood), "%02d/%02d %s", position, total, label);

  const char *animation = (!strcmp(eventType, "select") || !strcmp(eventType, "touch_long_press_select")) ? "pulse" : "scan";
  setKoalagotchiEyeStyle("cyber", "#A54BFF", "#32FF71", animation, getKoalagotchiEyeBrightness());
  drawKoalagotchiModeScreen("menu", mood, 82, 90);

  StaticJsonDocument<384> ack;
  ack["type"] = "menu_sync_ack";
  ack["device"] = "esp32-dualeye";
  ack["selected_label"] = label;
  ack["selected_command"] = command;
  ack["event_type"] = eventType;
  ack["position"] = position;
  ack["total"] = total;
  ack["execute"] = "B3/select or touchscreen long-press";
  sendJson(ack);
}

void handlePiCommand(const String &line) {
  StaticJsonDocument<1536> doc;
  DeserializationError err = deserializeJson(doc, line);
  if (err) return;

  const char *type = doc["type"] | "";
  if (!strcmp(type, "killerkoala_face") || !strcmp(type, "ai_face")) {
    handleKillerKoalaFace(doc);
  } else if (!strcmp(type, "menu_sync")) {
    handleMenuSync(doc);
  } else if (!strcmp(type, "koala_says")) {
    const char *msg = doc["message"] | "";
    StaticJsonDocument<192> ack;
    ack["type"] = "display_ack";
    ack["message"] = msg;
    sendJson(ack);
  } else if (!strcmp(type, "screen")) {
    if (doc["eye_look"].is<const char*>() || doc["left_eye"].is<const char*>() || doc["right_eye"].is<const char*>()) {
      setKoalagotchiEyeStyle(
        doc["eye_look"] | getKoalagotchiEyeLook(),
        doc["left_eye"] | getKoalagotchiLeftEyeHex(),
        doc["right_eye"] | getKoalagotchiRightEyeHex(),
        doc["eye_animation"] | getKoalagotchiEyeAnimation(),
        doc["eye_brightness"] | getKoalagotchiEyeBrightness()
      );
    }
    const char *mode = doc["mode"] | "eucalyptus";
    const char *mood = doc["mood"] | "";
    const int contentment = doc["contentment"] | 75;
    const int xpPercent = doc["xp_percent"] | 88;
    drawKoalagotchiModeScreen(mode, mood, contentment, xpPercent);

    StaticJsonDocument<192> ack;
    ack["type"] = "screen_ack";
    ack["mode"] = mode;
    ack["renderer"] = "koalagotchi_mode_screens";
    ack["eye_look"] = getKoalagotchiEyeLook();
    sendJson(ack);
  } else if (!strcmp(type, "eye_style") || !strcmp(type, "custom_eyes")) {
    if (doc["reset"] | false) {
      resetKoalagotchiEyeStyle();
    } else {
      setKoalagotchiEyeStyle(
        doc["look"] | getKoalagotchiEyeLook(),
        doc["left_color"] | getKoalagotchiLeftEyeHex(),
        doc["right_color"] | getKoalagotchiRightEyeHex(),
        doc["animation"] | getKoalagotchiEyeAnimation(),
        doc["brightness"] | getKoalagotchiEyeBrightness()
      );
    }
    drawKoalagotchiModeScreen(doc["mode"] | "eucalyptus", doc["mood"] | "custom", doc["contentment"] | 75, doc["xp_percent"] | 88);
    emitEyeStyleStatus("eye_style_ack");
  } else if (!strcmp(type, "eye_status")) {
    emitEyeStyleStatus();
  } else if (!strcmp(type, "mic_status") || !strcmp(type, "voice_status")) {
    emitVoiceStackStatus();
    emitMicStatus();
  } else if (!strcmp(type, "simulate_voice_wake")) {
    const char *phrase = doc["phrase"] | WAKE_WORD;
    if (strstr(phrase, WAKE_WORD) != nullptr) {
      emitVoiceWakeEvent(1.0f, "serial_test");
    }
  } else if (!strcmp(type, "simulate_voice_command")) {
    const char *phrase = doc["phrase"] | "killerkoala voice commands";
    emitVoiceCommandEvent(phrase, "serial_test");
  }
}

void pollSerial() {
  static String line;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      handlePiCommand(line);
      line = "";
    } else if (c != '\r') {
      line += c;
      if (line.length() > 1536) line = "";
    }
  }
}

void heartbeat() {
  if (millis() - lastHeartbeat < 5000) return;
  lastHeartbeat = millis();
  StaticJsonDocument<256> doc;
  doc["type"] = "heartbeat";
  doc["uptime_ms"] = millis();
  doc["free_heap"] = ESP.getFreeHeap();
  doc["eye_look"] = getKoalagotchiEyeLook();
  doc["eye_animation"] = getKoalagotchiEyeAnimation();
  doc["mic_ready"] = micBackendReady;
  doc["mic_status"] = micBackendStatus;
  sendJson(doc);
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(1200);

  setupDisplay();
  runBootAnimation();

  setupButtons();
  setupMic();
#if ENABLE_LOCAL_BLE_SCAN
  setupBle();
#endif
  drawKoalagotchiModeScreen("eucalyptus", "calm", 75, 88);
  emitBoot();
}

void loop() {
  pollSerial();
  pollButtons();
  pollVoiceWake();
  tickKoalagotchiEyes();
#if ENABLE_LOCAL_BLE_SCAN
  runBleScanCycle();
#endif
  heartbeat();
  delay(10);
}
