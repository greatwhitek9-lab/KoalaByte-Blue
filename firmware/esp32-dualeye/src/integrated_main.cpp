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
#include "dualeye_display.h"
#include "koalagotchi_mode_screens.h"

namespace {
constexpr uint8_t kMenuRowsMax = 6;
constexpr uint32_t kOverlayRefreshMs = 120;
constexpr uint32_t kResultHoldMs = 5200;
constexpr uint16_t kBlack = 0x0000;

struct MenuRow {
  char label[36];
  int position;
  bool selected;
  bool enabled;
};

Preferences prefs;
WiFiUDP udp;
String wifiSsid, wifiPassword, piHost, serialLine;
uint16_t piPort = KOALA_PI_UDP_DEFAULT_PORT;
IPAddress piAddress;

bool bleReady = false;
bool wifiStarted = false;
bool wifiReady = false;
bool audioStarted = false;
bool bleScanBusy = false;
bool wifiScanBusy = false;
bool menuVisible = false;
bool actionStatusVisible = false;
bool voiceMode = false;
bool utteranceActive = false;
bool menuWasVisibleBeforeUtterance = false;
bool overlayError = false;

uint32_t lastWifiRetry = 0;
uint32_t lastHeartbeat = 0;
uint32_t lastOverlayDraw = 0;
uint32_t actionStatusUntil = 0;
uint32_t faceReturnAt = 0;
uint32_t utteranceId = 0;
uint32_t utteranceSequence = 0;
uint32_t utteranceStartMs = 0;
uint32_t lastSpeechMs = 0;

uint8_t stereoMic[MIC_PCM_CHUNK_BYTES * 2];
uint8_t monoMic[MIC_PCM_CHUNK_BYTES];
char base64Buffer[900];

MenuRow menuRows[kMenuRowsMax];
uint8_t menuRowCount = 0;
int menuSelectedPosition = 1;
int menuTotalItems = 1;
char menuTitle[34] = "MAIN CANOPY";
char menuGroup[50] = "KOALABYTE BLUE";
char selectedLabel[74] = "Menu";
char currentAction[74] = "";
char currentResult[98] = "";
char currentEvent[34] = "";

uint16_t rgb565(uint8_t red, uint8_t green, uint8_t blue) {
  return static_cast<uint16_t>(((red & 0xF8U) << 8U) |
                               ((green & 0xFCU) << 3U) | (blue >> 3U));
}

void copyText(char *destination, size_t size, const char *value,
              const char *fallback = "") {
  snprintf(destination, size, "%s", value && value[0] ? value : fallback);
}

String clipped(const char *text, size_t limit) {
  String value(text ? text : "");
  value.replace("\n", " ");
  value.replace("\r", " ");
  if (value.length() > limit) value = value.substring(0, limit - 1) + "~";
  return value;
}

void drawCentered(Adafruit_GC9A01A &display, const char *text, int16_t y,
                  uint8_t size, uint16_t color) {
  if (!text || !text[0]) return;
  display.setTextWrap(false);
  display.setTextSize(size);
  display.setTextColor(color);
  int16_t x1, y1;
  uint16_t width, height;
  display.getTextBounds(text, 0, y, &x1, &y1, &width, &height);
  display.setCursor(max(0, (DISPLAY_WIDTH - static_cast<int>(width)) / 2), y);
  display.print(text);
}

void drawWrapped(Adafruit_GC9A01A &display, const char *text, int16_t x,
                 int16_t y, uint8_t size, uint16_t color, uint8_t maxChars,
                 uint8_t maxLines) {
  String remaining(text ? text : "");
  remaining.trim();
  display.setTextSize(size);
  display.setTextColor(color);
  display.setTextWrap(false);
  for (uint8_t line = 0; line < maxLines && remaining.length(); ++line) {
    int take = min(static_cast<int>(maxChars), static_cast<int>(remaining.length()));
    if (take < static_cast<int>(remaining.length())) {
      int split = remaining.lastIndexOf(' ', take);
      if (split > 4) take = split;
    }
    String part = remaining.substring(0, take);
    part.trim();
    display.setCursor(x, y + line * (8 * size + 4));
    display.print(part);
    remaining = remaining.substring(take);
    remaining.trim();
  }
}

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
  doc["type"] = "status";
  doc["device"] = "esp32-s3-dualeye";
  doc["message"] = message;
  sendPayload(doc);
}

void clearDisplayModes() {
  const bool hadFullScreenUi = menuVisible || actionStatusVisible;
  menuVisible = false;
  actionStatusVisible = false;
  if (hadFullScreenUi) dualEyeClear(kBlack);
}

void clearOverlay() {
  currentAction[0] = '\0';
  currentResult[0] = '\0';
  currentEvent[0] = '\0';
  overlayError = false;
}

void setOverlay(const char *action, const char *result, const char *event,
                bool error = false) {
  copyText(currentAction, sizeof(currentAction), action);
  copyText(currentResult, sizeof(currentResult), result);
  copyText(currentEvent, sizeof(currentEvent), event);
  overlayError = error;
  lastOverlayDraw = 0;
}

void drawPanelBars(Adafruit_GC9A01A &display, bool leftPanel) {
  const uint16_t purple = rgb565(165, 75, 255);
  const uint16_t green = rgb565(50, 255, 113);
  const uint16_t white = rgb565(230, 236, 232);
  const uint16_t dim = rgb565(104, 113, 118);
  uint16_t accent = leftPanel ? purple : green;
  if (overlayError) {
    const bool phase = ((millis() / 180U) & 1U) != 0;
    accent = phase ? purple : green;
  }

  display.fillRect(0, 0, DISPLAY_WIDTH, 19, kBlack);
  display.fillRect(0, DISPLAY_HEIGHT - 19, DISPLAY_WIDTH, 19, kBlack);
  display.drawFastHLine(18, 18, DISPLAY_WIDTH - 36, accent);
  display.drawFastHLine(18, DISPLAY_HEIGHT - 20, DISPLAY_WIDTH - 36, accent);
  display.setTextWrap(false);
  display.setTextSize(1);
  display.setTextColor(dim);
  display.setCursor(25, 5);
  display.print(leftPanel ? "ACTION" : (overlayError ? "ALARM" : "EVENT"));

  const char *line = leftPanel ? currentAction
                               : (currentResult[0] ? currentResult : currentEvent);
  String value = clipped(line, 31);
  display.setTextColor(white);
  display.setCursor(25, DISPLAY_HEIGHT - 14);
  display.print(value);
}

void drawStatusBars(bool force = false) {
  if (menuVisible || actionStatusVisible ||
      (!currentAction[0] && !currentResult[0] && !currentEvent[0])) {
    return;
  }
  if (!force && millis() - lastOverlayDraw < kOverlayRefreshMs) return;
  lastOverlayDraw = millis();

  if (dualEyePanelReady(1)) drawPanelBars(dualEyeLcd1(), true);
  if (dualEyePanelReady(2)) {
    drawPanelBars(dualEyeLcd2(), false);
    if (!dualEyePanelReady(1) && currentAction[0]) {
      Adafruit_GC9A01A &display = dualEyeLcd2();
      display.fillRect(76, 0, 146, 18, kBlack);
      display.setTextSize(1);
      display.setTextColor(rgb565(225, 229, 226));
      display.setCursor(76, 5);
      display.print(clipped(currentAction, 23));
    }
  }
}

void setFace(const char *state, const char *message = "") {
  clearDisplayModes();
  const char *look = "cyber";
  const char *animation = "idle";
  if (!strcmp(state, "wake") || !strcmp(state, "listening")) animation = "pulse";
  else if (!strcmp(state, "thinking")) animation = "scan";
  else if (!strcmp(state, "speaking")) animation = "blink";
  else if (!strcmp(state, "action")) animation = "glitch";
  else if (!strcmp(state, "success")) {
    look = "star";
    animation = "pulse";
  } else if (!strcmp(state, "error")) {
    look = "angry";
    animation = "glitch";
  }
  setKoalagotchiEyeStyle(look, "#A54BFF", "#32FF71", animation, 100);
  drawKoalagotchiModeScreen("killerkoala",
                            message && message[0] ? message : state, 85, 92);
  drawStatusBars(true);
}

void showIdleEyes() {
  voiceMode = false;
  faceReturnAt = 0;
  clearOverlay();
  setFace("idle", "calm");
}

void drawMenuRight() {
  if (!dualEyePanelReady(2)) return;
  Adafruit_GC9A01A &display = dualEyeLcd2();
  const uint16_t background = rgb565(2, 9, 12);
  const uint16_t panel = rgb565(5, 19, 23);
  const uint16_t green = rgb565(50, 255, 113);
  const uint16_t purple = rgb565(165, 75, 255);
  const uint16_t white = rgb565(226, 233, 229);
  const uint16_t disabled = rgb565(92, 101, 103);

  display.fillScreen(background);
  display.drawCircle(120, 120, 118, purple);
  display.drawCircle(120, 120, 115, green);
  drawCentered(display, clipped(menuTitle, 18).c_str(), 11, 2, green);
  char count[24];
  snprintf(count, sizeof(count), "%02d/%02d", menuSelectedPosition,
           max(menuTotalItems, 1));
  drawCentered(display, count, 31, 1, purple);

  const uint8_t rows = menuRowCount ? menuRowCount : 1;
  for (uint8_t index = 0; index < rows && index < kMenuRowsMax; ++index) {
    const MenuRow &row = menuRows[index];
    const int y = 43 + index * 28;
    const bool selected = row.selected ||
                          (!menuRowCount && row.position == menuSelectedPosition);
    const uint16_t fill = selected ? green : panel;
    const uint16_t text = selected ? background : (row.enabled ? white : disabled);
    display.fillRoundRect(15, y, 210, 24, 7, fill);
    display.drawRoundRect(15, y, 210, 24, 7, selected ? purple : green);
    display.setTextSize(1);
    display.setTextWrap(false);
    display.setTextColor(text);
    display.setCursor(23, y + 8);
    display.print(clipped(row.label, 31));
  }

  display.fillRect(34, 215, 172, 17, background);
  drawCentered(display, "K5/K6 MOVE  K3 SELECT", 220, 1, green);
}

void drawMenuLeft() {
  if (!dualEyePanelReady(1)) return;
  Adafruit_GC9A01A &display = dualEyeLcd1();
  const uint16_t background = rgb565(2, 7, 10);
  const uint16_t purple = rgb565(165, 75, 255);
  const uint16_t green = rgb565(50, 255, 113);
  const uint16_t white = rgb565(228, 233, 230);
  display.fillScreen(background);
  display.drawCircle(120, 120, 117, purple);
  display.drawRoundRect(22, 28, 196, 182, 18, green);
  drawCentered(display, "KOALABYTE BLUE", 35, 2, purple);
  drawCentered(display, clipped(menuGroup, 24).c_str(), 61, 1, green);
  drawCentered(display, "SELECTED", 89, 1, white);
  drawWrapped(display, selectedLabel, 35, 108, 1, white, 28, 4);
  drawCentered(display, "K2 BACK  K1 MENU", 188, 1, green);
}

void drawMenuScreen() {
  menuVisible = true;
  actionStatusVisible = false;
  faceReturnAt = 0;
  drawMenuLeft();
  drawMenuRight();
}

void drawActionPanel(Adafruit_GC9A01A &display, bool leftPanel,
                     const char *status) {
  const uint16_t background = rgb565(2, 7, 10);
  const uint16_t purple = rgb565(165, 75, 255);
  const uint16_t green = rgb565(50, 255, 113);
  const uint16_t white = rgb565(230, 235, 232);
  const uint16_t accent = leftPanel ? purple : green;
  display.fillScreen(background);
  display.drawCircle(120, 120, 117, accent);
  display.drawRoundRect(20, 25, 200, 190, 18, accent);
  drawCentered(display, leftPanel ? "ACTION" : "STATUS", 38, 2, accent);
  if (leftPanel) {
    drawWrapped(display, currentAction, 33, 82, 1, white, 29, 5);
  } else {
    drawCentered(display, status && status[0] ? status : "RUNNING", 75, 2,
                 accent);
    drawWrapped(display, currentResult, 33, 112, 1, white, 29, 5);
  }
}

void showActionStatus(const char *action, const char *result,
                      const char *status, uint32_t durationMs = 0) {
  menuVisible = false;
  actionStatusVisible = true;
  voiceMode = false;
  copyText(currentAction, sizeof(currentAction), action, "KoalaByte action");
  copyText(currentResult, sizeof(currentResult), result, "Executing on Pi");
  copyText(currentEvent, sizeof(currentEvent), status, "RUNNING");
  if (dualEyePanelReady(1)) drawActionPanel(dualEyeLcd1(), true, status);
  if (dualEyePanelReady(2)) {
    if (dualEyePanelReady(1)) {
      drawActionPanel(dualEyeLcd2(), false, status);
    } else {
      Adafruit_GC9A01A &display = dualEyeLcd2();
      drawActionPanel(display, false, status);
      display.fillRect(33, 146, 174, 44, rgb565(2, 7, 10));
      drawWrapped(display, currentAction, 38, 151, 1, rgb565(230, 235, 232),
                  27, 2);
    }
  }
  actionStatusUntil = durationMs ? millis() + durationMs : 0;
}

void loadMenu(JsonDocument &doc) {
  copyText(menuTitle, sizeof(menuTitle), doc["menu_title"] | "Main Canopy");
  copyText(menuGroup, sizeof(menuGroup), doc["selected_group"] | "KoalaByte Blue");
  copyText(selectedLabel, sizeof(selectedLabel), doc["selected_label"] | "Menu");
  menuSelectedPosition = doc["selected_position"] | 1;
  menuTotalItems = doc["total_items"] | 1;
  menuRowCount = 0;
  JsonArrayConst items = doc["visible_items"].as<JsonArrayConst>();
  for (JsonObjectConst item : items) {
    if (menuRowCount >= kMenuRowsMax) break;
    MenuRow &row = menuRows[menuRowCount++];
    copyText(row.label, sizeof(row.label), item["label"] | "Menu item");
    row.position = item["position"] | static_cast<int>(menuRowCount);
    row.selected = item["selected"] | false;
    row.enabled = item["enabled"] | true;
  }
  if (!menuRowCount) {
    menuRowCount = 1;
    copyText(menuRows[0].label, sizeof(menuRows[0].label), selectedLabel);
    menuRows[0].position = menuSelectedPosition;
    menuRows[0].selected = true;
    menuRows[0].enabled = doc["selected_enabled"] | true;
  }
}

void emitNodeStatus() {
  StaticJsonDocument<896> doc;
  doc["type"] = "node_status";
  doc["device"] = "esp32-s3-dualeye";
  doc["fw"] = KOALABLUE_FW_VERSION;
  doc["touch"] = false;
  doc["lcd1_ready"] = dualEyePanelReady(1);
  doc["lcd2_ready"] = dualEyePanelReady(2);
  doc["display_mode"] = menuVisible ? "menu" : actionStatusVisible ? "action_status" : "eyes";
  doc["execution_owner"] = KOALA_EXECUTION_OWNER;
  doc["expression_coordinator"] = KOALA_EXPRESSION_SYNC_COORDINATOR;
  doc["expression_sync_requires_ble"] = false;
  doc["wifi_started"] = wifiStarted;
  doc["wifi_ready"] = wifiReady;
  doc["wifi_ip"] = wifiReady ? WiFi.localIP().toString() : "";
  doc["pi_host"] = piHost;
  doc["pi_port"] = piPort;
  doc["ble_ready"] = bleReady;
  doc["audio_ready"] = dualEyeAudioReady();
  doc["mic_ready"] = dualEyeMicrophoneReady();
  doc["speaker_ready"] = dualEyeSpeakerReady();
  doc["audio_status"] = dualEyeAudioStatus();
  doc["free_heap"] = ESP.getFreeHeap();
  sendPayload(doc);
}

bool resolvePiAddress() {
  if (!piHost.length()) return false;
  if (piAddress.fromString(piHost)) return true;
  return WiFi.hostByName(piHost.c_str(), piAddress) == 1;
}

void loadWifiConfig() {
  prefs.begin(KOALA_WIFI_NVS_NAMESPACE, true);
  wifiSsid = prefs.getString("ssid", "");
  wifiPassword = prefs.getString("pass", "");
  piHost = prefs.getString("pi", "");
  piPort = prefs.getUShort("port", KOALA_PI_UDP_DEFAULT_PORT);
  prefs.end();
}

void saveWifiConfig(const char *ssid, const char *password, const char *host,
                    uint16_t port) {
  prefs.begin(KOALA_WIFI_NVS_NAMESPACE, false);
  prefs.putString("ssid", ssid ? ssid : "");
  prefs.putString("pass", password ? password : "");
  prefs.putString("pi", host ? host : "");
  prefs.putUShort("port", port ? port : KOALA_PI_UDP_DEFAULT_PORT);
  prefs.end();
  wifiSsid = ssid ? ssid : "";
  wifiPassword = password ? password : "";
  piHost = host ? host : "";
  piPort = port ? port : KOALA_PI_UDP_DEFAULT_PORT;
  piAddress = INADDR_NONE;
}

void renderEyesIfActive() {
  if (!menuVisible && !actionStatusVisible) {
    tickKoalagotchiEyes();
    drawStatusBars();
  }
}

void connectWifi() {
  wifiStarted = true;
  if (!wifiSsid.length()) {
    emitStatus("wifi_unprovisioned_usb_fallback_active");
    return;
  }
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(true);
  WiFi.setHostname(KOALA_WIFI_DEVICE_NAME);
  WiFi.begin(wifiSsid.c_str(), wifiPassword.c_str());
  uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED &&
         millis() - started < KOALA_WIFI_CONNECT_TIMEOUT_MS) {
    renderEyesIfActive();
    delay(20);
  }
  wifiReady = WiFi.status() == WL_CONNECTED;
  if (wifiReady) {
    udp.begin(KOALA_ESP32_UDP_LISTEN_PORT);
    resolvePiAddress();
    emitStatus("wifi_pi_node_ready");
  } else {
    emitStatus("wifi_connect_failed_usb_fallback_active");
  }
}

class SeenCallbacks : public NimBLEAdvertisedDeviceCallbacks {
  void onResult(NimBLEAdvertisedDevice *device) override {
    StaticJsonDocument<448> doc;
    doc["type"] = "ble_seen";
    doc["device"] = "esp32-s3-dualeye";
    doc["name"] = device->haveName() ? device->getName().c_str() : "";
    doc["addr"] = device->getAddress().toString().c_str();
    doc["rssi"] = device->getRSSI();
    doc["transport"] = "esp32-nimble";
    doc["face_sync"] = false;
    sendPayload(doc);
  }
};

void setupBle() {
  NimBLEDevice::init(BLE_DEVICE_NAME);
  NimBLEScan *scan = NimBLEDevice::getScan();
  scan->setAdvertisedDeviceCallbacks(new SeenCallbacks(), true);
  scan->setActiveScan(false);
  scan->setInterval(160);
  scan->setWindow(80);
  NimBLEAdvertising *advertising = NimBLEDevice::getAdvertising();
  advertising->addServiceUUID(BLE_NODE_SERVICE_UUID);
  advertising->setScanResponse(true);
  advertising->start();
  bleReady = true;
  emitStatus("ble_node_ready_pi_coordinates_heltec_expression_sync");
}

void bleScanTask(void *) {
  bleScanBusy = true;
  NimBLEScan *scan = NimBLEDevice::getScan();
  scan->start(BLE_SCAN_SECONDS, false);
  scan->clearResults();
  bleScanBusy = false;
  vTaskDelete(nullptr);
}

void wifiScanTask(void *) {
  wifiScanBusy = true;
  int count = WiFi.scanNetworks(false, true, KOALA_KOMBAT_WIFI_PASSIVE_SCAN, 120);
  int limit = min(count, KOALA_KOMBAT_WIFI_MAX_APS);
  for (int index = 0; index < limit; ++index) {
    StaticJsonDocument<384> doc;
    doc["type"] = "wifi_ap_seen";
    doc["device"] = "esp32-s3-dualeye";
    doc["ssid"] = WiFi.SSID(index);
    doc["bssid"] = WiFi.BSSIDstr(index);
    doc["rssi"] = WiFi.RSSI(index);
    doc["channel"] = WiFi.channel(index);
    doc["transport"] = "esp32-wifi-scan";
    sendPayload(doc);
  }
  WiFi.scanDelete();
  wifiScanBusy = false;
  vTaskDelete(nullptr);
}

void beginUtterance(float rms) {
  utteranceActive = true;
  menuWasVisibleBeforeUtterance = menuVisible;
  utteranceId = esp_random();
  utteranceSequence = 0;
  utteranceStartMs = lastSpeechMs = millis();
  if (!menuVisible) {
    setOverlay("VOICE COMMAND", "hearing audio", "MIC", false);
    drawStatusBars(true);
  }
  dualEyeAudioPlayCue(880, 55);
  StaticJsonDocument<384> doc;
  doc["type"] = "audio_utterance_start";
  doc["request_id"] = utteranceId;
  doc["sample_rate"] = AUDIO_INPUT_SAMPLE_RATE;
  doc["channels"] = 1;
  doc["sample_width"] = 2;
  doc["wake_phrases"] = "killerkoala|hey killerkoala";
  doc["rms"] = rms;
  doc["menu_was_visible"] = menuWasVisibleBeforeUtterance;
  doc["execution_owner"] = "raspberry-pi";
  sendPayload(doc);
}

void endUtterance(const char *reason) {
  if (!utteranceActive) return;
  StaticJsonDocument<256> doc;
  doc["type"] = "audio_utterance_end";
  doc["request_id"] = utteranceId;
  doc["chunks"] = utteranceSequence;
  doc["reason"] = reason;
  doc["menu_was_visible"] = menuWasVisibleBeforeUtterance;
  sendPayload(doc);
  utteranceActive = false;
}

void pollMicrophone() {
  if (!dualEyeMicrophoneReady() || dualEyeAudioBusy()) return;
  size_t count = dualEyeAudioRead(stereoMic, sizeof(stereoMic));
  if (count < 4) return;
  float rms = dualEyeAudioRms16Stereo(stereoMic, count);
  const int16_t *stereo = reinterpret_cast<const int16_t *>(stereoMic);
  int16_t *mono = reinterpret_cast<int16_t *>(monoMic);
  size_t frames = min(count / 4, sizeof(monoMic) / 2);
  for (size_t index = 0; index < frames; ++index) mono[index] = stereo[index * 2];
  if (!utteranceActive && rms >= MIC_WAKE_RMS_THRESHOLD) beginUtterance(rms);
  if (!utteranceActive) return;
  if (rms >= MIC_WAKE_RMS_THRESHOLD * 0.55f) lastSpeechMs = millis();
  size_t encodedLength = 0;
  if (mbedtls_base64_encode(
          reinterpret_cast<unsigned char *>(base64Buffer),
          sizeof(base64Buffer) - 1, &encodedLength, monoMic,
          frames * sizeof(int16_t)) == 0) {
    base64Buffer[encodedLength] = 0;
    StaticJsonDocument<1280> doc;
    doc["type"] = "audio_pcm_chunk";
    doc["request_id"] = utteranceId;
    doc["sequence"] = utteranceSequence++;
    doc["pcm_s16le_mono_b64"] = base64Buffer;
    doc["rms"] = rms;
    sendPayload(doc);
  }
  if (millis() - utteranceStartMs >= MIC_UTTERANCE_MAX_MS) {
    endUtterance("max_duration");
  } else if (millis() - lastSpeechMs >= MIC_UTTERANCE_SILENCE_MS) {
    endUtterance("silence");
  }
}

void handleFace(JsonDocument &doc) {
  const char *state = doc["state"] | "idle";
  const char *message = doc["message"] | state;
  voiceMode = strcmp(state, "idle") != 0 && strcmp(state, "hidden") != 0;
  if (voiceMode) {
    setOverlay(currentAction[0] ? currentAction : "VOICE COMMAND", message, state,
               !strcmp(state, "error"));
  } else {
    clearOverlay();
  }
  setFace(state, message);
  if (!strcmp(state, "success")) faceReturnAt = millis() + 2600;
  else if (!strcmp(state, "error")) faceReturnAt = millis() + 6000;
}

void handleMenu(JsonDocument &doc) {
  loadMenu(doc);
  const char *eventType = doc["event_type"] | "highlight";
  const char *source = doc["source"] | "";
  const bool voiceRequest = doc["voice_request"] | (!strcmp(source, "pi-companion"));
  const bool selected = !strcmp(eventType, "select") ||
                        !strcmp(eventType, "touch_long_press_select");
  copyText(currentAction, sizeof(currentAction), selectedLabel);

  if (selected && voiceRequest) {
    voiceMode = true;
    setOverlay(selectedLabel, "executing on Raspberry Pi", "RUNNING", false);
    setFace("action", selectedLabel);
    return;
  }
  if (selected) {
    showActionStatus(selectedLabel, "Executing on Raspberry Pi", "RUNNING");
    return;
  }
  voiceMode = false;
  clearOverlay();
  drawMenuScreen();
}

void handleAudioPcm(JsonDocument &doc) {
  const char *encoded = doc["pcm_s16le_mono_b64"] | "";
  if (!encoded[0] || !dualEyeSpeakerReady()) return;
  static uint8_t decoded[SPEAKER_PCM_CHUNK_MAX_BYTES];
  size_t decodedLength = 0;
  if (mbedtls_base64_decode(
          decoded, sizeof(decoded), &decodedLength,
          reinterpret_cast<const unsigned char *>(encoded), strlen(encoded)) == 0) {
    voiceMode = true;
    setOverlay(currentAction[0] ? currentAction : "KILLERKOALA",
               doc["message"] | "speaking", "SPEAKING", false);
    setFace("speaking", doc["message"] | "speaking");
    dualEyeAudioWriteMono16(reinterpret_cast<const int16_t *>(decoded),
                            decodedLength / 2);
  }
  if (doc["end"] | false) {
    dualEyeAudioStopPlayback();
    setFace("success", "ready");
    faceReturnAt = millis() + 2200;
  }
}

void emitVoiceCommand(const char *phrase, const char *source) {
  StaticJsonDocument<640> doc;
  doc["type"] = "voice_command";
  doc["request_id"] = esp_random();
  doc["phrase"] = phrase;
  doc["source"] = source;
  doc["wake_word"] = WAKE_WORD;
  doc["alternate_wake_word"] = WAKE_WORD_ALTERNATE;
  doc["execution_owner"] = "raspberry-pi";
  doc["execute_menu_and_submenus_on_pi"] = true;
  doc["ai_fallback"] = true;
  sendPayload(doc);
  voiceMode = true;
  setOverlay("VOICE COMMAND", phrase, "THINKING", false);
  setFace("thinking", "thinking");
}

void handleExecutionResult(JsonDocument &doc) {
  const char *status = doc["status"] | "success";
  const char *message = doc["message"] | status;
  const bool success = !strcmp(status, "success") || !strcmp(status, "ai_response");
  const char *action = currentAction[0] ? currentAction : (doc["action"] | "KoalaByte action");
  if (!success) {
    voiceMode = true;
    setOverlay(action, message, status, true);
    setFace("error", message);
    faceReturnAt = millis() + 6500;
    return;
  }
  if (voiceMode || (doc["voice_request"] | false)) {
    setOverlay(action, message, "COMPLETE", false);
    setFace("success", message);
    faceReturnAt = millis() + 3200;
  } else {
    showActionStatus(action, message, "COMPLETE", kResultHoldMs);
  }
}

void handleCommand(const String &line) {
  StaticJsonDocument<6144> doc;
  if (deserializeJson(doc, line)) return;
  const char *type = doc["type"] | "";
  if (!strcmp(type, "killerkoala_face") || !strcmp(type, "ai_face") ||
      !strcmp(type, "ai_face_sync")) {
    handleFace(doc);
  } else if (!strcmp(type, "menu_sync")) {
    handleMenu(doc);
  } else if (!strcmp(type, "wifi_config")) {
    saveWifiConfig(doc["ssid"] | "", doc["password"] | "",
                   doc["pi_host"] | "",
                   doc["pi_port"] | KOALA_PI_UDP_DEFAULT_PORT);
    WiFi.disconnect(true, true);
    delay(50);
    connectWifi();
    emitNodeStatus();
  } else if (!strcmp(type, "node_status") || !strcmp(type, "mic_status") ||
             !strcmp(type, "audio_status")) {
    emitNodeStatus();
  } else if (!strcmp(type, "scan_nodes")) {
    if (bleReady && !bleScanBusy && !dualEyeAudioBusy()) {
      xTaskCreatePinnedToCore(bleScanTask, "BleScan", 4096, nullptr, 1, nullptr, 0);
    }
    if (wifiReady && !wifiScanBusy && !dualEyeAudioBusy()) {
      xTaskCreatePinnedToCore(wifiScanTask, "WifiScan", 4096, nullptr, 1, nullptr, 0);
    }
  } else if (!strcmp(type, "simulate_voice_command")) {
    emitVoiceCommand(doc["phrase"] | "killerkoala voice commands", "serial_test");
  } else if (!strcmp(type, "audio_pcm")) {
    handleAudioPcm(doc);
  } else if (!strcmp(type, "audio_stop")) {
    dualEyeAudioStopPlayback();
    showIdleEyes();
  } else if (!strcmp(type, "pi_execution_result")) {
    handleExecutionResult(doc);
  } else if (!strcmp(type, "voice_rejected")) {
    clearOverlay();
    if (menuWasVisibleBeforeUtterance) drawMenuScreen();
    else showIdleEyes();
  } else if (!strcmp(type, "action_status")) {
    showActionStatus(doc["action"] | "KoalaByte action",
                     doc["message"] | "Executing on Raspberry Pi",
                     doc["status"] | "RUNNING", doc["duration_ms"] | 0);
  } else if (!strcmp(type, "screen")) {
    clearDisplayModes();
    drawKoalagotchiModeScreen(doc["mode"] | "eucalyptus",
                              doc["mood"] | "calm",
                              doc["contentment"] | 75,
                              doc["xp_percent"] | 88);
  }
}

void pollSerial() {
  while (Serial.available()) {
    char value = static_cast<char>(Serial.read());
    if (value == '\n') {
      handleCommand(serialLine);
      serialLine = "";
    } else if (value != '\r') {
      serialLine += value;
      if (serialLine.length() > 12288) serialLine = "";
    }
  }
}

void pollUdp() {
  if (!wifiReady) return;
  int packet = udp.parsePacket();
  if (packet <= 0) return;
  String line;
  line.reserve(packet + 1);
  while (udp.available()) line += static_cast<char>(udp.read());
  handleCommand(line);
}

void stageSubsystems() {
  const uint32_t now = millis();
  if (!bleReady && now >= SUBSYSTEM_BLE_START_MS &&
      ESP.getFreeHeap() >= SUBSYSTEM_READY_MIN_FREE_HEAP) {
    setupBle();
  }
  if (!wifiStarted && now >= SUBSYSTEM_WIFI_START_MS &&
      ESP.getFreeHeap() >= SUBSYSTEM_READY_MIN_FREE_HEAP) {
    connectWifi();
  }
  if (!audioStarted && now >= SUBSYSTEM_AUDIO_START_MS &&
      ESP.getFreeHeap() >= SUBSYSTEM_READY_MIN_FREE_HEAP) {
    audioStarted = true;
    dualEyeAudioBegin();
    emitNodeStatus();
  }
  if (wifiStarted && !wifiReady && wifiSsid.length() &&
      now - lastWifiRetry >= KOALA_WIFI_RETRY_INTERVAL_MS) {
    lastWifiRetry = now;
    connectWifi();
  }
}

void updateDisplayTimeouts() {
  const uint32_t now = millis();
  if (actionStatusVisible && actionStatusUntil &&
      static_cast<int32_t>(now - actionStatusUntil) >= 0) {
    showIdleEyes();
  }
  if (!menuVisible && !actionStatusVisible && faceReturnAt &&
      static_cast<int32_t>(now - faceReturnAt) >= 0 && !dualEyeAudioBusy()) {
    showIdleEyes();
  }
}

void heartbeat() {
  if (millis() - lastHeartbeat < 5000) return;
  lastHeartbeat = millis();
  emitNodeStatus();
}
}  // namespace

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(1200);
  setupDisplay();
  runBootAnimation();
  loadWifiConfig();
  showIdleEyes();
  emitStatus("idle_eyes_ready_staged_wifi_ble_audio_pending");
}

void loop() {
  pollSerial();
  pollUdp();
  renderEyesIfActive();
  stageSubsystems();
  pollMicrophone();
  updateDisplayTimeouts();
  heartbeat();
  delay(1);
}
