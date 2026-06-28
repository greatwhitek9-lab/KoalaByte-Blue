#include "esp32_touch_menu.h"
#include "config.h"

#include <Wire.h>

#ifndef ENABLE_TOUCH_MENU
#define ENABLE_TOUCH_MENU 1
#endif
#ifndef TOUCH_MENU_BACKEND
#define TOUCH_MENU_BACKEND "waveshare_cst816x_i2c"
#endif
#ifndef TOUCH_MENU_CONTROLLER
#define TOUCH_MENU_CONTROLLER "CST816x"
#endif
#ifndef TOUCH_MENU_I2C_ADDR
#define TOUCH_MENU_I2C_ADDR 0x15
#endif
#ifndef TOUCH_MENU_I2C_SDA_PIN
#define TOUCH_MENU_I2C_SDA_PIN 6
#endif
#ifndef TOUCH_MENU_I2C_SCL_PIN
#define TOUCH_MENU_I2C_SCL_PIN 7
#endif
#ifndef TOUCH_MENU_INT_PIN
#define TOUCH_MENU_INT_PIN 5
#endif
#ifndef TOUCH_MENU_RST_PIN
#define TOUCH_MENU_RST_PIN 13
#endif
#ifndef TOUCH_MENU_I2C_CLOCK_HZ
#define TOUCH_MENU_I2C_CLOCK_HZ 400000
#endif
#ifndef TOUCH_MENU_POLL_MS
#define TOUCH_MENU_POLL_MS 35
#endif
#ifndef TOUCH_MENU_SCREEN_W
#define TOUCH_MENU_SCREEN_W 240
#endif
#ifndef TOUCH_MENU_SCREEN_H
#define TOUCH_MENU_SCREEN_H 240
#endif
#ifndef TOUCH_MENU_RAW_MIN_X
#define TOUCH_MENU_RAW_MIN_X 0
#endif
#ifndef TOUCH_MENU_RAW_MAX_X
#define TOUCH_MENU_RAW_MAX_X 239
#endif
#ifndef TOUCH_MENU_RAW_MIN_Y
#define TOUCH_MENU_RAW_MIN_Y 0
#endif
#ifndef TOUCH_MENU_RAW_MAX_Y
#define TOUCH_MENU_RAW_MAX_Y 239
#endif
#ifndef TOUCH_MENU_INVERT_X
#define TOUCH_MENU_INVERT_X 0
#endif
#ifndef TOUCH_MENU_INVERT_Y
#define TOUCH_MENU_INVERT_Y 0
#endif
#ifndef TOUCH_MENU_SWAP_XY
#define TOUCH_MENU_SWAP_XY 0
#endif
#ifndef TOUCH_MENU_ROW_HEIGHT
#define TOUCH_MENU_ROW_HEIGHT 40
#endif
#ifndef TOUCH_MENU_VISIBLE_ROWS
#define TOUCH_MENU_VISIBLE_ROWS 6
#endif
#ifndef TOUCH_MENU_LONG_PRESS_MS
#define TOUCH_MENU_LONG_PRESS_MS 750
#endif

#define CST816_REG_GESTURE 0x01
#define CST816_REG_FINGER_NUM 0x02
#define CST816_REG_XPOSH 0x03
#define CST816_REG_CHIP_ID 0xA7

struct TouchMenuState {
  int rawMinX;
  int rawMaxX;
  int rawMinY;
  int rawMaxY;
  int screenW;
  int screenH;
  int rowHeight;
  int visibleRows;
  bool invertX;
  bool invertY;
  bool swapXY;
  bool calibrated;
  bool hardwareReady;
  bool wasPressed;
  bool longPressSent;
  int lastX;
  int lastY;
  int lastRawX;
  int lastRawY;
  uint8_t lastGesture;
  uint8_t chipId;
  uint32_t pressStartMs;
  uint32_t lastPollMs;
  uint32_t lastStatusMs;
};

static TouchMenuState touchMenu = {
  TOUCH_MENU_RAW_MIN_X,
  TOUCH_MENU_RAW_MAX_X,
  TOUCH_MENU_RAW_MIN_Y,
  TOUCH_MENU_RAW_MAX_Y,
  TOUCH_MENU_SCREEN_W,
  TOUCH_MENU_SCREEN_H,
  TOUCH_MENU_ROW_HEIGHT,
  TOUCH_MENU_VISIBLE_ROWS,
  TOUCH_MENU_INVERT_X != 0,
  TOUCH_MENU_INVERT_Y != 0,
  TOUCH_MENU_SWAP_XY != 0,
  true,
  false,
  false,
  false,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
};

static volatile bool Touch_Interrupt_Flag = false;

void IRAM_ATTR Arduino_IIC_Touch_Interrupt() {
  Touch_Interrupt_Flag = true;
}

static int clampInt(int value, int lo, int hi) {
  if (value < lo) return lo;
  if (value > hi) return hi;
  return value;
}

static int mapAxis(int raw, int rawMin, int rawMax, int outMax, bool invert) {
  if (rawMax == rawMin) return 0;
  long mapped = ((long)(raw - rawMin) * (long)(outMax - 1)) / (long)(rawMax - rawMin);
  int value = clampInt((int)mapped, 0, outMax - 1);
  return invert ? (outMax - 1 - value) : value;
}

static void mapRawToScreen(int rawX, int rawY, int &x, int &y) {
  int mx = mapAxis(rawX, touchMenu.rawMinX, touchMenu.rawMaxX, touchMenu.screenW, touchMenu.invertX);
  int my = mapAxis(rawY, touchMenu.rawMinY, touchMenu.rawMaxY, touchMenu.screenH, touchMenu.invertY);
  if (touchMenu.swapXY) {
    x = clampInt(my, 0, touchMenu.screenW - 1);
    y = clampInt(mx, 0, touchMenu.screenH - 1);
  } else {
    x = mx;
    y = my;
  }
}

static bool cst816ReadRegs(uint8_t reg, uint8_t *buffer, size_t length) {
  Wire.beginTransmission((uint8_t)TOUCH_MENU_I2C_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  int got = Wire.requestFrom((uint8_t)TOUCH_MENU_I2C_ADDR, (uint8_t)length);
  if (got != (int)length) return false;
  for (size_t i = 0; i < length && Wire.available(); ++i) {
    buffer[i] = Wire.read();
  }
  return true;
}

static bool cst816Probe() {
  uint8_t chip = 0;
  if (cst816ReadRegs(CST816_REG_CHIP_ID, &chip, 1)) {
    touchMenu.chipId = chip;
    return true;
  }
  uint8_t probe[6] = {0};
  bool ok = cst816ReadRegs(CST816_REG_GESTURE, probe, sizeof(probe));
  touchMenu.chipId = ok ? 0x00 : 0xff;
  return ok;
}

static bool cst816ReadTouch(int &rawX, int &rawY, uint8_t &gesture, uint8_t &fingers) {
  uint8_t data[6] = {0};
  if (!cst816ReadRegs(CST816_REG_GESTURE, data, sizeof(data))) return false;
  gesture = data[0];
  fingers = data[1] & 0x0f;
  if (fingers == 0) return true;
  rawX = ((int)(data[2] & 0x0f) << 8) | data[3];
  rawY = ((int)(data[4] & 0x0f) << 8) | data[5];
  return true;
}

static const char *gestureName(uint8_t gesture) {
  switch (gesture) {
    case 0x01: return "swipe_up";
    case 0x02: return "swipe_down";
    case 0x03: return "swipe_left";
    case 0x04: return "swipe_right";
    case 0x05: return "tap";
    case 0x0b: return "double_tap";
    case 0x0c: return "long_press";
    default: return "touch";
  }
}

static const char *commandForEvent(const char *eventName) {
  if (!strcmp(eventName, "down")) return "touch_down";
  if (!strcmp(eventName, "move")) return "touch_move";
  if (!strcmp(eventName, "up")) return "touch_up";
  if (!strcmp(eventName, "tap")) return "touch_tap";
  if (!strcmp(eventName, "double_tap")) return "select";
  if (!strcmp(eventName, "long_press")) return "select";
  if (!strcmp(eventName, "long_press_select")) return "select";
  return "touch_event";
}

static void emitTouchEvent(KoalaTouchJsonSender sendJson, const char *eventName, int x, int y, int rawX, int rawY) {
  if (!sendJson) return;
  StaticJsonDocument<384> out;
  out["type"] = "menu_touch";
  out["device"] = "esp32-dualeye";
  out["controller"] = TOUCH_MENU_CONTROLLER;
  out["backend"] = TOUCH_MENU_BACKEND;
  out["event"] = eventName;
  out["command"] = commandForEvent(eventName);
  out["x"] = x;
  out["y"] = y;
  out["raw_x"] = rawX;
  out["raw_y"] = rawY;
  out["row"] = clampInt(y / max(1, touchMenu.rowHeight), 0, max(0, touchMenu.visibleRows - 1));
  out["row_height"] = touchMenu.rowHeight;
  out["screen_w"] = touchMenu.screenW;
  out["screen_h"] = touchMenu.screenH;
  out["calibrated"] = touchMenu.calibrated;
  out["hardware_ready"] = touchMenu.hardwareReady;
  out["gesture"] = gestureName(touchMenu.lastGesture);
  sendJson(out);
}

void setupTouchMenu() {
#if ENABLE_TOUCH_MENU
  touchMenu.lastStatusMs = 0;
  touchMenu.lastPollMs = 0;
  touchMenu.wasPressed = false;
  touchMenu.longPressSent = false;

  if (TOUCH_MENU_RST_PIN >= 0) {
    pinMode(TOUCH_MENU_RST_PIN, OUTPUT);
    digitalWrite(TOUCH_MENU_RST_PIN, LOW);
    delay(8);
    digitalWrite(TOUCH_MENU_RST_PIN, HIGH);
    delay(55);
  }

  Wire.begin(TOUCH_MENU_I2C_SDA_PIN, TOUCH_MENU_I2C_SCL_PIN);
  Wire.setClock(TOUCH_MENU_I2C_CLOCK_HZ);

  if (TOUCH_MENU_INT_PIN >= 0) {
    pinMode(TOUCH_MENU_INT_PIN, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(TOUCH_MENU_INT_PIN), Arduino_IIC_Touch_Interrupt, FALLING);
  }

  touchMenu.hardwareReady = cst816Probe();
  Touch_Interrupt_Flag = true;
#endif
}

void pollTouchMenu(KoalaTouchJsonSender sendJson) {
#if ENABLE_TOUCH_MENU
  const uint32_t now = millis();
  if (now - touchMenu.lastStatusMs > 30000) {
    touchMenu.lastStatusMs = now;
    emitTouchMenuStatus(sendJson, "touch_menu_heartbeat");
  }

  if (!touchMenu.hardwareReady) return;
  const bool pollDue = now - touchMenu.lastPollMs >= TOUCH_MENU_POLL_MS;
  if (!Touch_Interrupt_Flag && !pollDue) return;
  Touch_Interrupt_Flag = false;
  touchMenu.lastPollMs = now;

  int rawX = touchMenu.lastRawX;
  int rawY = touchMenu.lastRawY;
  uint8_t gesture = 0;
  uint8_t fingers = 0;
  if (!cst816ReadTouch(rawX, rawY, gesture, fingers)) return;
  touchMenu.lastGesture = gesture;

  if (fingers > 0) {
    int x = 0;
    int y = 0;
    mapRawToScreen(rawX, rawY, x, y);
    const bool firstPress = !touchMenu.wasPressed;
    touchMenu.wasPressed = true;
    touchMenu.lastX = x;
    touchMenu.lastY = y;
    touchMenu.lastRawX = rawX;
    touchMenu.lastRawY = rawY;
    if (firstPress) {
      touchMenu.pressStartMs = now;
      touchMenu.longPressSent = false;
      emitTouchEvent(sendJson, "down", x, y, rawX, rawY);
      if (gesture == 0x05) emitTouchEvent(sendJson, "tap", x, y, rawX, rawY);
      if (gesture == 0x0b) emitTouchEvent(sendJson, "double_tap", x, y, rawX, rawY);
      if (gesture == 0x0c) {
        touchMenu.longPressSent = true;
        emitTouchEvent(sendJson, "long_press", x, y, rawX, rawY);
      }
    } else {
      emitTouchEvent(sendJson, "move", x, y, rawX, rawY);
      if (!touchMenu.longPressSent && now - touchMenu.pressStartMs >= TOUCH_MENU_LONG_PRESS_MS) {
        touchMenu.longPressSent = true;
        emitTouchEvent(sendJson, "long_press", x, y, rawX, rawY);
      }
    }
  } else if (touchMenu.wasPressed) {
    touchMenu.wasPressed = false;
    emitTouchEvent(sendJson, "up", touchMenu.lastX, touchMenu.lastY, touchMenu.lastRawX, touchMenu.lastRawY);
  }
#else
  (void)sendJson;
#endif
}

void emitTouchMenuStatus(KoalaTouchJsonSender sendJson, const char *statusType) {
  if (!sendJson) return;
  StaticJsonDocument<768> doc;
  doc["type"] = statusType;
  doc["device"] = "esp32-dualeye";
  doc["enabled"] = ENABLE_TOUCH_MENU;
  doc["backend"] = TOUCH_MENU_BACKEND;
  doc["controller"] = TOUCH_MENU_CONTROLLER;
  doc["hardware_ready"] = touchMenu.hardwareReady;
  doc["i2c_addr"] = TOUCH_MENU_I2C_ADDR;
  doc["i2c_sda"] = TOUCH_MENU_I2C_SDA_PIN;
  doc["i2c_scl"] = TOUCH_MENU_I2C_SCL_PIN;
  doc["int_pin"] = TOUCH_MENU_INT_PIN;
  doc["rst_pin"] = TOUCH_MENU_RST_PIN;
  doc["chip_id"] = touchMenu.chipId;
  doc["screen_w"] = touchMenu.screenW;
  doc["screen_h"] = touchMenu.screenH;
  doc["raw_min_x"] = touchMenu.rawMinX;
  doc["raw_max_x"] = touchMenu.rawMaxX;
  doc["raw_min_y"] = touchMenu.rawMinY;
  doc["raw_max_y"] = touchMenu.rawMaxY;
  doc["invert_x"] = touchMenu.invertX;
  doc["invert_y"] = touchMenu.invertY;
  doc["swap_xy"] = touchMenu.swapXY;
  doc["row_height"] = touchMenu.rowHeight;
  doc["visible_rows"] = touchMenu.visibleRows;
  doc["long_press_ms"] = TOUCH_MENU_LONG_PRESS_MS;
  doc["note"] = "Waveshare ESP32-S3 DualEye/Touch CST816x I2C touch reader emits menu_touch JSON events; serial raw_touch/simulate_touch remains available for bench testing.";
  sendJson(doc);
}

bool handleTouchMenuCommand(JsonDocument &doc, KoalaTouchJsonSender sendJson) {
  const char *type = doc["type"] | "";
  if (!strcmp(type, "touch_status")) {
    emitTouchMenuStatus(sendJson);
    return true;
  }
  if (!strcmp(type, "touch_calibration")) {
    touchMenu.rawMinX = doc["raw_min_x"] | touchMenu.rawMinX;
    touchMenu.rawMaxX = doc["raw_max_x"] | touchMenu.rawMaxX;
    touchMenu.rawMinY = doc["raw_min_y"] | touchMenu.rawMinY;
    touchMenu.rawMaxY = doc["raw_max_y"] | touchMenu.rawMaxY;
    touchMenu.screenW = doc["screen_w"] | touchMenu.screenW;
    touchMenu.screenH = doc["screen_h"] | touchMenu.screenH;
    touchMenu.rowHeight = doc["row_height"] | touchMenu.rowHeight;
    touchMenu.visibleRows = doc["visible_rows"] | touchMenu.visibleRows;
    touchMenu.invertX = doc["invert_x"] | touchMenu.invertX;
    touchMenu.invertY = doc["invert_y"] | touchMenu.invertY;
    touchMenu.swapXY = doc["swap_xy"] | touchMenu.swapXY;
    touchMenu.calibrated = true;
    emitTouchMenuStatus(sendJson, "touch_calibration_ack");
    return true;
  }
  if (!strcmp(type, "menu_frame")) {
    touchMenu.rowHeight = doc["row_height"] | touchMenu.rowHeight;
    touchMenu.visibleRows = doc["visible_rows"] | touchMenu.visibleRows;
    touchMenu.screenW = doc["screen_w"] | touchMenu.screenW;
    touchMenu.screenH = doc["screen_h"] | touchMenu.screenH;
    emitTouchMenuStatus(sendJson, "menu_frame_ack");
    return true;
  }
  if (!strcmp(type, "simulate_touch") || !strcmp(type, "raw_touch")) {
    const char *eventName = doc["event"] | "tap";
    int x = doc["x"] | -1;
    int y = doc["y"] | -1;
    int rawX = doc["raw_x"] | x;
    int rawY = doc["raw_y"] | y;
    touchMenu.lastGesture = !strcmp(eventName, "tap") ? 0x05 : (!strcmp(eventName, "long_press") ? 0x0c : 0x00);
    if (x < 0 || y < 0) {
      mapRawToScreen(rawX, rawY, x, y);
    }
    emitTouchEvent(sendJson, eventName, x, y, rawX, rawY);
    return true;
  }
  return false;
}
