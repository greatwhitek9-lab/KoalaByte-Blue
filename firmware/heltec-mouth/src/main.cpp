#include <Arduino.h>
#include <ArduinoJson.h>

#ifndef LED_BUILTIN
#define LED_BUILTIN 35
#endif

static String inputLine;
static String currentState = "boot";
static String currentMessage = "killerkoala online";
static unsigned long faceUntilMs = 0;
static bool faceEnabled = true;
static bool ledOn = false;
static unsigned long lastHeartbeatMs = 0;

static void sendJson(const JsonDocument &doc) {
  serializeJson(doc, Serial);
  Serial.println();
}

static void sendAck(const char *state, bool ok = true) {
  StaticJsonDocument<384> doc;
  doc["type"] = "killerkoala_tft_ack";
  doc["device"] = "heltec-t114-color";
  doc["state"] = state;
  doc["active"] = ok;
  doc["gnss_enabled"] = true;
  doc["transport"] = "usb-cdc";
  sendJson(doc);
}

static void sendStatus() {
  StaticJsonDocument<448> doc;
  doc["type"] = "heltec_mouth_status";
  doc["device"] = "heltec-t114";
  doc["transport"] = "usb-cdc";
  doc["state"] = currentState;
  doc["message"] = currentMessage;
  doc["face_enabled"] = faceEnabled;
  doc["uptime_ms"] = millis();
  sendJson(doc);
}

static void sendGnssStatus() {
  StaticJsonDocument<384> doc;
  doc["type"] = "gnss_status";
  doc["device"] = "heltec-t114";
  doc["transport"] = "usb-cdc";
  doc["enabled"] = true;
  doc["note"] = "GNSS forwarding uses newline JSON when a receiver stream is attached to this profile.";
  sendJson(doc);
}

static void handleFace(JsonDocument &doc) {
  faceEnabled = doc["enabled"] | true;
  currentState = String((const char *)(doc["state"] | "listening"));
  currentMessage = String((const char *)(doc["message"] | ""));
  unsigned long duration = doc["duration_ms"] | 4500;
  faceUntilMs = millis() + duration;
  digitalWrite(LED_BUILTIN, faceEnabled ? HIGH : LOW);
  sendAck(currentState.c_str(), true);
}

static void handleLine(const String &line) {
  StaticJsonDocument<768> doc;
  DeserializationError err = deserializeJson(doc, line);
  if (err) {
    StaticJsonDocument<192> out;
    out["type"] = "error";
    out["device"] = "heltec-t114";
    out["error"] = "invalid_json";
    sendJson(out);
    return;
  }
  const char *type = doc["type"] | "";
  if (!strcmp(type, "killerkoala_face") || !strcmp(type, "ai_face")) {
    handleFace(doc);
  } else if (!strcmp(type, "gnss_status")) {
    sendGnssStatus();
  } else if (!strcmp(type, "status")) {
    sendStatus();
  } else {
    StaticJsonDocument<192> out;
    out["type"] = "error";
    out["device"] = "heltec-t114";
    out["error"] = "unknown_type";
    out["received"] = type;
    sendJson(out);
  }
}

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  Serial.begin(115200);
  unsigned long start = millis();
  while (!Serial && millis() - start < 3000) {
    delay(10);
  }
  sendStatus();
}

void loop() {
  while (Serial.available()) {
    char c = static_cast<char>(Serial.read());
    if (c == '\n' || c == '\r') {
      if (inputLine.length() > 0) {
        handleLine(inputLine);
        inputLine = "";
      }
    } else if (inputLine.length() < 700) {
      inputLine += c;
    }
  }

  if (faceEnabled && faceUntilMs > 0 && millis() > faceUntilMs) {
    faceUntilMs = 0;
    digitalWrite(LED_BUILTIN, LOW);
  }

  if (millis() - lastHeartbeatMs > 5000) {
    lastHeartbeatMs = millis();
    ledOn = !ledOn;
    if (!faceEnabled || faceUntilMs == 0) {
      digitalWrite(LED_BUILTIN, ledOn ? HIGH : LOW);
    }
  }
}
