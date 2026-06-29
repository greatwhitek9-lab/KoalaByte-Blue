#include "esp32_touch_menu.h"
#include "config.h"

#include <Wire.h>
#include <string.h>

#ifndef ENABLE_TOUCH_MENU
#define ENABLE_TOUCH_MENU 1
#endif
#ifndef TOUCH_MENU_BACKEND
#define TOUCH_MENU_BACKEND "waveshare_cst816d_i2c"
#endif
#ifndef TOUCH_MENU_CONTROLLER
#define TOUCH_MENU_CONTROLLER "CST816D"
#endif
#ifndef TOUCH_MENU_I2C_ADDR
#define TOUCH_MENU_I2C_ADDR 0x15
#endif
#ifndef TOUCH_MENU_I2C_SDA_PIN
#define TOUCH_MENU_I2C_SDA_PIN 11
#endif
#ifndef TOUCH_MENU_I2C_SCL_PIN
#define TOUCH_MENU_I2C_SCL_PIN 7
#endif
#ifndef TOUCH_MENU_INT_PIN
#define TOUCH_MENU_INT_PIN 12
#endif
#ifndef TOUCH_MENU_RST_PIN
#define TOUCH_MENU_RST_PIN 6
#endif
#ifndef TOUCH_MENU_I2C_CLOCK_HZ
#define TOUCH_MENU_I2C_CLOCK_HZ 400000
#endif
#ifndef TOUCH_MENU_POLL_MS
#define TOUCH_MENU_POLL_MS 10
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
#define TOUCH_MENU_LONG_PRESS_MS 500
#endif

#define CST816_REG_TOUCH_DATA 0x02
#define CST816_REG_CHIP_ID 0xA3

struct TouchMenuState {
  int rawMinX = TOUCH_MENU_RAW_MIN_X;
  int rawMaxX = TOUCH_MENU_RAW_MAX_X;
  int rawMinY = TOUCH_MENU_RAW_MIN_Y;
  int rawMaxY = TOUCH_MENU_RAW_MAX_Y;
  int screenW = TOUCH_MENU_SCREEN_W;
  int screenH = TOUCH_MENU_SCREEN_H;
  int rowHeight = TOUCH_MENU_ROW_HEIGHT;
  int visibleRows = TOUCH_MENU_VISIBLE_ROWS;
  bool invertX = TOUCH_MENU_INVERT_X != 0;
  bool invertY = TOUCH_MENU_INVERT_Y != 0;
  bool swapXY = TOUCH_MENU_SWAP_XY != 0;
  bool calibrated = true;
  bool hardwareReady = false;
  bool wasPressed = false;
  bool longPressSent = false;
  int lastX = 0;
  int lastY = 0;
  int lastRawX = 0;
  int lastRawY = 0;
  uint8_t chipId = 0;
  uint32_t pressStartMs = 0;
  uint32_t lastPollMs = 0;
  uint32_t lastStatusMs = 0;
};

static TouchMenuState touchMenu;
static volatile bool touchIrq = false;

void IRAM_ATTR Arduino_IIC_Touch_Interrupt() {
  touchIrq = true;
}

static int clampInt(int value, int lo, int hi) {
  if (value < lo) return lo;
  if (value > hi) return hi;
  return value;
}

static int mapAxis(int value, int inMin, int inMax, int outMax, bool invert) {
  if (inMax == inMin) return 0;
  long mapped = ((long)(value - inMin) * (long)(outMax - 1)) / (long)(inMax - inMin);
  int out = clampInt((int)mapped, 0, outMax - 1);
  return invert ? (outMax - 1 - out) : out;
}

static void mapRawToScreen(int rawX, int rawY, int &x, int &y) {
  int sx = mapAxis(rawX, touchMenu.rawMinX, touchMenu.rawMaxX, touchMenu.screenW, touchMenu.invertX);
  int sy = mapAxis(rawY, touchMenu.rawMinY, touchMenu.rawMaxY, touchMenu.screenH, touchMenu.invertY);
  if (touchMenu.swapXY) {
    x = clampInt(sy, 0, touchMenu.screenW - 1);
    y = clampInt(sx, 0, touchMenu.screenH - 1);
  } else {
    x = sx;
    y = sy;
  }
}

static bool readRegs(uint8_t reg, uint8_t *buffer, size_t length) {
  Wire.beginTransmission((uint8_t)TOUCH_MENU_I2C_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  int got = Wire.requestFrom((uint8_t)TOUCH_MENU_I2C_ADDR, (uint8_t)length);
  if (got != (int)length) return false;
  for (size_t i = 0; i < length; ++i) {
    buffer[i] = Wire.available() ? Wire.read() : 0;
  }
  return true;
}

static bool probeCst816d() {
  uint8_t id = 0;
  if (!readRegs(CST816_REG_CHIP_ID, &id, 1)) return false;
  touchMenu.chipId = id;
  return true;
}

static bool getTouch(int &rawX, int &rawY, uint8_t &points) {
  uint8_t b[6] = {0};
  if (!readRegs(CST816_REG_TOUCH_DATA, b, sizeof(b))) return false;
  if (b[0] == 0xFF) b[0] = 0x00;
  points = b[0] & 0x01;
  if (points == 0) return true;
  rawX = ((int)(b[1] & 0x0F) << 8) | b[2];
  rawY = ((int)(b[3] & 0x0F) << 8) | b[4];
  return true;
}

static void emitTouchEvent(KoalaTouchJsonSender sendJson, const char *eventName, int x, int y, int rawX, int rawY) {
  if (!sendJson) return;
  StaticJsonDocument<384> out;
  out["type"] = "menu_touch";
  out["device"] = "esp32-dualeye";
  out["controller"] = TOUCH_MENU_CONTROLLER;
  out["backend"] = TOUCH_MENU_BACKEND;
  out["event"] = eventName;
  out["command"] = !strcmp(eventName, "long_press") ? "select" : (!strcmp(eventName, "tap") ? "touch_tap" : "touch_event");
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
  sendJson(out);
}

void setupTouchMenu() {
#if ENABLE_TOUCH_MENU
  if (TOUCH_MENU_RST_PIN >= 0) {
    pinMode(TOUCH_MENU_RST_PIN, OUTPUT);
    digitalWrite(TOUCH_MENU_RST_PIN, LOW);
    delay(5);
    digitalWrite(TOUCH_MENU_RST_PIN, HIGH);
    delay(50);
  }
  Wire.begin(TOUCH_MENU_I2C_SDA_PIN, TOUCH_MENU_I2C_SCL_PIN);
  Wire.setClock(TOUCH_MENU_I2C_CLOCK_HZ);
  if (TOUCH_MENU_INT_PIN >= 0) {
    pinMode(TOUCH_MENU_INT_PIN, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(TOUCH_MENU_INT_PIN), Arduino_IIC_Touch_Interrupt, FALLING);
  }
  touchMenu.hardwareReady = probeCst816d();
  touchIrq = true;
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
  if (!touchIrq && now - touchMenu.lastPollMs < TOUCH_MENU_POLL_MS) return;
  touchIrq = false;
  touchMenu.lastPollMs = now;

  int rawX = touchMenu.lastRawX;
  int rawY = touchMenu.lastRawY;
  uint8_t points = 0;
  if (!getTouch(rawX, rawY, points)) return;
  if (points > 0) {
    int x = 0;
    int y = 0;
    mapRawToScreen(rawX, rawY, x, y);
    touchMenu.lastX = x;
    touchMenu.lastY = y;
    touchMenu.lastRawX = rawX;
    touchMenu.lastRawY = rawY;
    if (!touchMenu.wasPressed) {
      touchMenu.wasPressed = true;
      touchMenu.longPressSent = false;
      touchMenu.pressStartMs = now;
      emitTouchEvent(sendJson, "down", x, y, rawX, rawY);
    } else if (!touchMenu.longPressSent && now - touchMenu.pressStartMs >= TOUCH_MENU_LONG_PRESS_MS) {
      touchMenu.longPressSent = true;
      emitTouchEvent(sendJson, "long_press", x, y, rawX, rawY);
    } else {
      emitTouchEvent(sendJson, "move", x, y, rawX, rawY);
    }
  } else if (touchMenu.wasPressed) {
    bool shortTap = (now - touchMenu.pressStartMs) < TOUCH_MENU_LONG_PRESS_MS;
    touchMenu.wasPressed = false;
    emitTouchEvent(sendJson, shortTap ? "tap" : "up", touchMenu.lastX, touchMenu.lastY, touchMenu.lastRawX, touchMenu.lastRawY);
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
  doc["note"] = "Waveshare CST816D register reader mirrors vendor sample: chip id 0xA3, data block 0x02.";
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
  if (!strcmp(type, "simulate_touch")) {
    const char *eventName = doc["event"] | "tap";
    int x = doc["x"] | 0;
    int y = doc["y"] | 0;
    emitTouchEvent(sendJson, eventName, x, y, x, y);
    return true;
  }
  return false;
}
