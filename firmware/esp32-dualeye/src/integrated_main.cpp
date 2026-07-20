#include <Arduino.h>
#include <ArduinoJson.h>
#include <NimBLEDevice.h>
#include <Preferences.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <mbedtls/base64.h>

#include "boot_animation.h"
#include "config.h"
#include "dualeye_audio.h"
#include "koalagotchi_mode_screens.h"

namespace {
Preferences prefs;
WiFiUDP udp;
String wifiSsid, wifiPassword, piHost, serialLine;
uint16_t piPort = KOALA_PI_UDP_DEFAULT_PORT;
IPAddress piAddress;
bool bleReady = false, wifiStarted = false, wifiReady = false, audioStarted = false;
bool bleScanBusy = false, wifiScanBusy = false;
uint32_t lastWifiRetry = 0, lastHeartbeat = 0;
bool utteranceActive = false;
uint32_t utteranceId = 0, utteranceSequence = 0, utteranceStartMs = 0, lastSpeechMs = 0;
uint8_t stereoMic[MIC_PCM_CHUNK_BYTES * 2];
uint8_t monoMic[MIC_PCM_CHUNK_BYTES];
char base64Buffer[900];

void sendPayload(JsonDocument &doc, bool allowUdp = true) {
  String payload;
  serializeJson(doc, payload);
  Serial.println(payload);
  if (allowUdp && wifiReady && piAddress != INADDR_NONE && piPort) {
    udp.beginPacket(piAddress, piPort);
    udp.write(reinterpret_cast<const uint8_t *>(payload.c_str()), payload.length());
    udp.endPacket();
  }
}

void emitStatus(const char *message) {
  StaticJsonDocument<256> doc;
  doc["type"] = "status"; doc["device"] = "esp32-s3-dualeye"; doc["message"] = message;
  sendPayload(doc);
}

void setFace(const char *state, const char *message = "") {
  const char *look = "cyber";
  const char *animation = "idle";
  if (!strcmp(state, "wake") || !strcmp(state, "listening")) animation = "pulse";
  else if (!strcmp(state, "thinking")) animation = "scan";
  else if (!strcmp(state, "speaking")) animation = "blink";
  else if (!strcmp(state, "action")) animation = "glitch";
  else if (!strcmp(state, "success")) { look = "star"; animation = "pulse"; }
  else if (!strcmp(state, "error")) { look = "angry"; animation = "glitch"; }
  setKoalagotchiEyeStyle(look, "#A54BFF", "#32FF71", animation, 100);
  drawKoalagotchiModeScreen("killerkoala", message && message[0] ? message : state, 85, 92);
}

void emitNodeStatus() {
  StaticJsonDocument<768> doc;
  doc["type"] = "node_status"; doc["device"] = "esp32-s3-dualeye"; doc["fw"] = KOALABLUE_FW_VERSION;
  doc["touch"] = false; doc["lcd"] = "lcd2_only"; doc["execution_owner"] = KOALA_EXECUTION_OWNER;
  doc["expression_coordinator"] = KOALA_EXPRESSION_SYNC_COORDINATOR; doc["expression_sync_requires_ble"] = false;
  doc["wifi_started"] = wifiStarted; doc["wifi_ready"] = wifiReady;
  doc["wifi_ip"] = wifiReady ? WiFi.localIP().toString() : ""; doc["pi_host"] = piHost; doc["pi_port"] = piPort;
  doc["ble_ready"] = bleReady; doc["audio_ready"] = dualEyeAudioReady();
  doc["mic_ready"] = dualEyeMicrophoneReady(); doc["speaker_ready"] = dualEyeSpeakerReady();
  doc["audio_status"] = dualEyeAudioStatus(); doc["free_heap"] = ESP.getFreeHeap();
  sendPayload(doc);
}

bool resolvePiAddress() {
  if (!piHost.length()) return false;
  if (piAddress.fromString(piHost)) return true;
  return WiFi.hostByName(piHost.c_str(), piAddress) == 1;
}

void loadWifiConfig() {
  prefs.begin(KOALA_WIFI_NVS_NAMESPACE, true);
  wifiSsid = prefs.getString("ssid", ""); wifiPassword = prefs.getString("pass", "");
  piHost = prefs.getString("pi", ""); piPort = prefs.getUShort("port", KOALA_PI_UDP_DEFAULT_PORT);
  prefs.end();
}

void saveWifiConfig(const char *ssid, const char *password, const char *host, uint16_t port) {
  prefs.begin(KOALA_WIFI_NVS_NAMESPACE, false);
  prefs.putString("ssid", ssid ? ssid : ""); prefs.putString("pass", password ? password : "");
  prefs.putString("pi", host ? host : ""); prefs.putUShort("port", port ? port : KOALA_PI_UDP_DEFAULT_PORT); prefs.end();
  wifiSsid = ssid ? ssid : ""; wifiPassword = password ? password : ""; piHost = host ? host : "";
  piPort = port ? port : KOALA_PI_UDP_DEFAULT_PORT; piAddress = INADDR_NONE;
}

void connectWifi() {
  wifiStarted = true;
  if (!wifiSsid.length()) { emitStatus("wifi_unprovisioned_usb_fallback_active"); return; }
  WiFi.mode(WIFI_STA); WiFi.setSleep(true); WiFi.setHostname(KOALA_WIFI_DEVICE_NAME);
  WiFi.begin(wifiSsid.c_str(), wifiPassword.c_str());
  uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < KOALA_WIFI_CONNECT_TIMEOUT_MS) {
    tickKoalagotchiEyes(); delay(20);
  }
  wifiReady = WiFi.status() == WL_CONNECTED;
  if (wifiReady) { udp.begin(KOALA_ESP32_UDP_LISTEN_PORT); resolvePiAddress(); emitStatus("wifi_pi_node_ready"); }
  else emitStatus("wifi_connect_failed_usb_fallback_active");
}

class SeenCallbacks : public NimBLEAdvertisedDeviceCallbacks {
  void onResult(NimBLEAdvertisedDevice *device) override {
    StaticJsonDocument<448> doc;
    doc["type"] = "ble_seen"; doc["device"] = "esp32-s3-dualeye";
    doc["name"] = device->haveName() ? device->getName().c_str() : "";
    doc["addr"] = device->getAddress().toString().c_str(); doc["rssi"] = device->getRSSI();
    doc["transport"] = "esp32-nimble"; doc["face_sync"] = false; sendPayload(doc);
  }
};

void setupBle() {
  NimBLEDevice::init(BLE_DEVICE_NAME);
  NimBLEScan *scan = NimBLEDevice::getScan();
  scan->setAdvertisedDeviceCallbacks(new SeenCallbacks(), true); scan->setActiveScan(false); scan->setInterval(160); scan->setWindow(80);
  NimBLEAdvertising *advertising = NimBLEDevice::getAdvertising();
  advertising->addServiceUUID(BLE_NODE_SERVICE_UUID); advertising->setScanResponse(true); advertising->start();
  bleReady = true; emitStatus("ble_node_ready_not_used_for_face_sync");
}

void bleScanTask(void *) {
  bleScanBusy = true; NimBLEScan *scan = NimBLEDevice::getScan();
  scan->start(BLE_SCAN_SECONDS, false); scan->clearResults(); bleScanBusy = false; vTaskDelete(nullptr);
}

void wifiScanTask(void *) {
  wifiScanBusy = true; int count = WiFi.scanNetworks(false, true, KOALA_KOMBAT_WIFI_PASSIVE_SCAN, 120);
  int limit = min(count, KOALA_KOMBAT_WIFI_MAX_APS);
  for (int i = 0; i < limit; ++i) {
    StaticJsonDocument<384> doc;
    doc["type"] = "wifi_ap_seen"; doc["device"] = "esp32-s3-dualeye"; doc["ssid"] = WiFi.SSID(i);
    doc["bssid"] = WiFi.BSSIDstr(i); doc["rssi"] = WiFi.RSSI(i); doc["channel"] = WiFi.channel(i);
    doc["transport"] = "esp32-wifi-scan"; sendPayload(doc);
  }
  WiFi.scanDelete(); wifiScanBusy = false; vTaskDelete(nullptr);
}

void beginUtterance(float rms) {
  utteranceActive = true; utteranceId = esp_random(); utteranceSequence = 0; utteranceStartMs = lastSpeechMs = millis();
  setFace("listening", "listening"); dualEyeAudioPlayCue(880, 55);
  StaticJsonDocument<384> doc;
  doc["type"] = "audio_utterance_start"; doc["request_id"] = utteranceId; doc["sample_rate"] = AUDIO_INPUT_SAMPLE_RATE;
  doc["channels"] = 1; doc["sample_width"] = 2; doc["wake_phrases"] = "killerkoala|hey killerkoala";
  doc["rms"] = rms; doc["execution_owner"] = "raspberry-pi"; sendPayload(doc);
}

void endUtterance(const char *reason) {
  if (!utteranceActive) return;
  StaticJsonDocument<256> doc;
  doc["type"] = "audio_utterance_end"; doc["request_id"] = utteranceId; doc["chunks"] = utteranceSequence; doc["reason"] = reason;
  sendPayload(doc); utteranceActive = false; setFace("thinking", "thinking");
}

void pollMicrophone() {
  if (!dualEyeMicrophoneReady() || dualEyeAudioBusy()) return;
  size_t count = dualEyeAudioRead(stereoMic, sizeof(stereoMic)); if (count < 4) return;
  float rms = dualEyeAudioRms16Stereo(stereoMic, count);
  const int16_t *stereo = reinterpret_cast<const int16_t *>(stereoMic); int16_t *mono = reinterpret_cast<int16_t *>(monoMic);
  size_t frames = min(count / 4, sizeof(monoMic) / 2); for (size_t i = 0; i < frames; ++i) mono[i] = stereo[i * 2];
  if (!utteranceActive && rms >= MIC_WAKE_RMS_THRESHOLD) beginUtterance(rms);
  if (!utteranceActive) return;
  if (rms >= MIC_WAKE_RMS_THRESHOLD * 0.55f) lastSpeechMs = millis();
  size_t encodedLength = 0;
  if (mbedtls_base64_encode(reinterpret_cast<unsigned char *>(base64Buffer), sizeof(base64Buffer) - 1, &encodedLength,
                            monoMic, frames * sizeof(int16_t)) == 0) {
    base64Buffer[encodedLength] = 0;
    StaticJsonDocument<1280> doc;
    doc["type"] = "audio_pcm_chunk"; doc["request_id"] = utteranceId; doc["sequence"] = utteranceSequence++;
    doc["pcm_s16le_mono_b64"] = base64Buffer; doc["rms"] = rms; sendPayload(doc);
  }
  if (millis() - utteranceStartMs >= MIC_UTTERANCE_MAX_MS) endUtterance("max_duration");
  else if (millis() - lastSpeechMs >= MIC_UTTERANCE_SILENCE_MS) endUtterance("silence");
}

void handleFace(JsonDocument &doc) { const char *state = doc["state"] | "listening"; setFace(state, doc["message"] | state); }

void handleMenu(JsonDocument &doc) {
  const char *label = doc["selected_label"] | "menu"; const char *eventType = doc["event_type"] | "highlight";
  char mood[96]; snprintf(mood, sizeof(mood), "%02d/%02d %s", doc["selected_position"] | 1, doc["total_items"] | 1, label);
  setKoalagotchiEyeStyle("cyber", "#A54BFF", "#32FF71", !strcmp(eventType, "select") ? "pulse" : "scan", 100);
  drawKoalagotchiModeScreen("menu", mood, 82, 90);
}

void handleAudioPcm(JsonDocument &doc) {
  const char *encoded = doc["pcm_s16le_mono_b64"] | ""; if (!encoded[0] || !dualEyeSpeakerReady()) return;
  static uint8_t decoded[SPEAKER_PCM_CHUNK_MAX_BYTES]; size_t decodedLength = 0;
  if (mbedtls_base64_decode(decoded, sizeof(decoded), &decodedLength,
                            reinterpret_cast<const unsigned char *>(encoded), strlen(encoded)) == 0) {
    setFace("speaking", doc["message"] | "speaking");
    dualEyeAudioWriteMono16(reinterpret_cast<const int16_t *>(decoded), decodedLength / 2);
  }
  if (doc["end"] | false) { dualEyeAudioStopPlayback(); setFace("success", "ready"); }
}

void emitVoiceCommand(const char *phrase, const char *source) {
  StaticJsonDocument<640> doc;
  doc["type"] = "voice_command"; doc["request_id"] = esp_random(); doc["phrase"] = phrase; doc["source"] = source;
  doc["wake_word"] = WAKE_WORD; doc["alternate_wake_word"] = WAKE_WORD_ALTERNATE;
  doc["execution_owner"] = "raspberry-pi"; doc["execute_menu_and_submenus_on_pi"] = true; doc["ai_fallback"] = true;
  sendPayload(doc); setFace("thinking", "thinking");
}

void handleCommand(const String &line) {
  StaticJsonDocument<4096> doc; if (deserializeJson(doc, line)) return;
  const char *type = doc["type"] | "";
  if (!strcmp(type, "killerkoala_face") || !strcmp(type, "ai_face")) handleFace(doc);
  else if (!strcmp(type, "menu_sync")) handleMenu(doc);
  else if (!strcmp(type, "wifi_config")) {
    saveWifiConfig(doc["ssid"] | "", doc["password"] | "", doc["pi_host"] | "", doc["pi_port"] | KOALA_PI_UDP_DEFAULT_PORT);
    WiFi.disconnect(true, true); delay(50); connectWifi(); emitNodeStatus();
  } else if (!strcmp(type, "node_status") || !strcmp(type, "mic_status") || !strcmp(type, "audio_status")) emitNodeStatus();
  else if (!strcmp(type, "scan_nodes")) {
    if (bleReady && !bleScanBusy && !dualEyeAudioBusy()) xTaskCreatePinnedToCore(bleScanTask, "BleScan", 4096, nullptr, 1, nullptr, 0);
    if (wifiReady && !wifiScanBusy && !dualEyeAudioBusy()) xTaskCreatePinnedToCore(wifiScanTask, "WifiScan", 4096, nullptr, 1, nullptr, 0);
  } else if (!strcmp(type, "simulate_voice_command")) emitVoiceCommand(doc["phrase"] | "killerkoala voice commands", "serial_test");
  else if (!strcmp(type, "audio_pcm")) handleAudioPcm(doc);
  else if (!strcmp(type, "audio_stop")) { dualEyeAudioStopPlayback(); setFace("idle", "calm"); }
  else if (!strcmp(type, "pi_execution_result")) {
    const char *status = doc["status"] | "success"; setFace(!strcmp(status, "success") ? "success" : "error", doc["message"] | status);
  } else if (!strcmp(type, "screen")) {
    drawKoalagotchiModeScreen(doc["mode"] | "eucalyptus", doc["mood"] | "calm", doc["contentment"] | 75, doc["xp_percent"] | 88);
  }
}

void pollSerial() {
  while (Serial.available()) {
    char c = static_cast<char>(Serial.read());
    if (c == '\n') { handleCommand(serialLine); serialLine = ""; }
    else if (c != '\r') { serialLine += c; if (serialLine.length() > 8192) serialLine = ""; }
  }
}

void pollUdp() {
  if (!wifiReady) return; int packet = udp.parsePacket(); if (packet <= 0) return;
  String line; line.reserve(packet + 1); while (udp.available()) line += static_cast<char>(udp.read()); handleCommand(line);
}

void stageSubsystems() {
  uint32_t now = millis();
  if (!bleReady && now >= SUBSYSTEM_BLE_START_MS && ESP.getFreeHeap() >= SUBSYSTEM_READY_MIN_FREE_HEAP) setupBle();
  if (!wifiStarted && now >= SUBSYSTEM_WIFI_START_MS && ESP.getFreeHeap() >= SUBSYSTEM_READY_MIN_FREE_HEAP) connectWifi();
  if (!audioStarted && now >= SUBSYSTEM_AUDIO_START_MS && ESP.getFreeHeap() >= SUBSYSTEM_READY_MIN_FREE_HEAP) {
    audioStarted = true; dualEyeAudioBegin(); emitNodeStatus();
  }
  if (wifiStarted && !wifiReady && wifiSsid.length() && now - lastWifiRetry >= KOALA_WIFI_RETRY_INTERVAL_MS) {
    lastWifiRetry = now; connectWifi();
  }
}

void heartbeat() { if (millis() - lastHeartbeat >= 5000) { lastHeartbeat = millis(); emitNodeStatus(); } }
}

void setup() {
  Serial.begin(SERIAL_BAUD); delay(1200); setupDisplay(); runBootAnimation(); loadWifiConfig();
  drawKoalagotchiModeScreen("eucalyptus", "calm", 75, 88); emitStatus("display_stable_staged_subsystems_pending");
}

void loop() {
  pollSerial(); pollUdp(); tickKoalagotchiEyes(); stageSubsystems(); pollMicrophone(); heartbeat(); delay(1);
}
