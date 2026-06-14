#include <Arduino.h>
#include <ArduinoJson.h>
#include <NimBLEDevice.h>
#include "config.h"

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

void emitBoot() {
  StaticJsonDocument<256> doc;
  doc["type"] = "boot";
  doc["device"] = "esp32-dualeye";
  doc["fw"] = KOALABLUE_FW_VERSION;
  doc["companion"] = COMPANION_NAME;
  doc["wake_word"] = WAKE_WORD;
  doc["ble_scan"] = ENABLE_LOCAL_BLE_SCAN;
  doc["mic_wake"] = ENABLE_MIC_WAKE;
  doc["display_stub"] = ENABLE_DISPLAY_STUB;
  sendJson(doc);
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

void handlePiCommand(const String &line) {
  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, line);
  if (err) return;

  const char *type = doc["type"] | "";
  if (!strcmp(type, "koala_says")) {
    const char *msg = doc["message"] | "";
    StaticJsonDocument<192> ack;
    ack["type"] = "display_ack";
    ack["message"] = msg;
    sendJson(ack);
  } else if (!strcmp(type, "screen")) {
    StaticJsonDocument<128> ack;
    ack["type"] = "screen_ack";
    ack["mode"] = doc["mode"] | "unknown";
    sendJson(ack);
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
      if (line.length() > 768) line = "";
    }
  }
}

void heartbeat() {
  if (millis() - lastHeartbeat < 5000) return;
  lastHeartbeat = millis();
  StaticJsonDocument<160> doc;
  doc["type"] = "heartbeat";
  doc["uptime_ms"] = millis();
  doc["free_heap"] = ESP.getFreeHeap();
  sendJson(doc);
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(1200);
  setupButtons();
#if ENABLE_LOCAL_BLE_SCAN
  setupBle();
#endif
  emitBoot();
}

void loop() {
  pollSerial();
  pollButtons();
  pollVoiceWake();
#if ENABLE_LOCAL_BLE_SCAN
  runBleScanCycle();
#endif
  heartbeat();
  delay(10);
}
