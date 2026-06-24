#include <Arduino.h>
#include <ArduinoJson.h>
#include <NimBLEDevice.h>
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
  StaticJsonDocument<768> doc;
  doc["type"] = "voice_stack";
  doc["device"] = "esp32-dualeye";
  doc["wake_word"] = WAKE_WORD;
  doc["front_end"] = ESP32S3_VOICE_FRONTEND_STACK;
  doc["wake_model"] = ESP32S3_WAKE_MODEL;
  doc["command_model"] = ESP32S3_COMMAND_MODEL;
  doc["alias_pack"] = ESP32S3_COMMAND_ALIAS_PACK;
  doc["companion_brain"] = KILLERKOALA_COMPANION_BRAIN;
  doc["response_policy"] = KILLERKOALA_RESPONSE_POLICY;
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
  StaticJsonDocument<768> doc;
  doc["type"] = "boot";
  doc["device"] = "esp32-dualeye";
  doc["fw"] = KOALABLUE_FW_VERSION;
  doc["companion"] = COMPANION_NAME;
  doc["wake_word"] = WAKE_WORD;
  doc["ble_scan"] = ENABLE_LOCAL_BLE_SCAN;
  doc["mic_wake"] = ENABLE_MIC_WAKE;
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
  emitEyeStyleStatus();
#if ENABLE_MIC_WAKE
  if (MIC_I2S_BCLK_PIN < 0 || MIC_I2S_WS_PIN < 0 || MIC_I2S_DIN_PIN < 0) {
    StaticJsonDocument<256> warn;
    warn["type"] = "voice_backend";
    warn["status"] = "mic_enabled_pin_mapping_required";
    warn["wake_word"] = WAKE_WORD;
    warn["message"] = "Mic wake is enabled by default; set DualEye I2S pins for hardware wake-word capture.";
    sendJson(warn);
  }
#endif
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

float sampleMicRms() {
  // Hardware-specific placeholder. Enable only after setting the correct I2S pins and audio driver.
  return 0.0f;
}

void pollVoiceWake() {
#if ENABLE_MIC_WAKE
  float rms = sampleMicRms();
  if (rms >= MIC_WAKE_RMS_THRESHOLD && millis() - lastVoiceWake > MIC_WAKE_COOLDOWN_MS) {
    lastVoiceWake = millis();
    StaticJsonDocument<160> doc;
    doc["type"] = "voice_wake";
    doc["name"] = COMPANION_NAME;
    doc["wake_word"] = WAKE_WORD;
    doc["phrase"] = WAKE_WORD;
    doc["rms"] = rms;
    doc["source"] = "esp32_i2s_mic";
    sendJson(doc);
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

void handlePiCommand(const String &line) {
  StaticJsonDocument<768> doc;
  DeserializationError err = deserializeJson(doc, line);
  if (err) return;

  const char *type = doc["type"] | "";
  if (!strcmp(type, "killerkoala_face") || !strcmp(type, "ai_face")) {
    handleKillerKoalaFace(doc);
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
  } else if (!strcmp(type, "simulate_voice_wake")) {
    const char *phrase = doc["phrase"] | "";
    if (strstr(phrase, WAKE_WORD) != nullptr) {
      StaticJsonDocument<192> wake;
      wake["type"] = "voice_wake";
      wake["name"] = COMPANION_NAME;
      wake["wake_word"] = WAKE_WORD;
      wake["phrase"] = phrase;
      wake["source"] = "serial_test";
      sendJson(wake);
    }
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
      if (line.length() > 1024) line = "";
    }
  }
}

void heartbeat() {
  if (millis() - lastHeartbeat < 5000) return;
  lastHeartbeat = millis();
  StaticJsonDocument<192> doc;
  doc["type"] = "heartbeat";
  doc["uptime_ms"] = millis();
  doc["free_heap"] = ESP.getFreeHeap();
  doc["eye_look"] = getKoalagotchiEyeLook();
  doc["eye_animation"] = getKoalagotchiEyeAnimation();
  sendJson(doc);
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(1200);

  setupDisplay();
  runBootAnimation();

  setupButtons();
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
