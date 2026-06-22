#include "esp32_touch_menu.h"
#include "config.h"

#ifndef ENABLE_TOUCH_MENU
#define ENABLE_TOUCH_MENU 1
#endif
#ifndef TOUCH_MENU_BACKEND
#define TOUCH_MENU_BACKEND "serial_calibrated"
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
#define TOUCH_MENU_RAW_MAX_X 4095
#endif
#ifndef TOUCH_MENU_RAW_MIN_Y
#define TOUCH_MENU_RAW_MIN_Y 0
#endif
#ifndef TOUCH_MENU_RAW_MAX_Y
#define TOUCH_MENU_RAW_MAX_Y 4095
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
  0,
};

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

static const char *commandForEvent(const char *eventName) {
  if (!strcmp(eventName, "down")) return "touch_down";
  if (!strcmp(eventName, "move")) return "touch_move";
  if (!strcmp(eventName, "up")) return "touch_up";
  if (!strcmp(eventName, "tap")) return "touch_tap";
  if (!strcmp(eventName, "long_press")) return "select";
  if (!strcmp(eventName, "long_press_select")) return "select";
  return "touch_event";
}

static void emitTouchEvent(KoalaTouchJsonSender sendJson, const char *eventName, int x, int y, int rawX, int rawY) {
  if (!sendJson) return;
  StaticJsonDocument<320> out;
  out["type"] = "menu_touch";
  out["device"] = "esp32-dualeye";
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
  sendJson(out);
}

void setupTouchMenu() {
  touchMenu.lastStatusMs = 0;
}

void pollTouchMenu(KoalaTouchJsonSender sendJson) {
#if ENABLE_TOUCH_MENU
  if (millis() - touchMenu.lastStatusMs > 30000) {
    touchMenu.lastStatusMs = millis();
    emitTouchMenuStatus(sendJson, "touch_menu_heartbeat");
  }
#else
  (void)sendJson;
#endif
}

void emitTouchMenuStatus(KoalaTouchJsonSender sendJson, const char *statusType) {
  if (!sendJson) return;
  StaticJsonDocument<512> doc;
  doc["type"] = statusType;
  doc["device"] = "esp32-dualeye";
  doc["enabled"] = ENABLE_TOUCH_MENU;
  doc["backend"] = TOUCH_MENU_BACKEND;
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
  doc["note"] = "Touch controller hardware is board-revision-specific; this firmware provides calibrated menu-touch events when raw touch samples or simulated touches are supplied.";
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
    if (x < 0 || y < 0) {
      mapRawToScreen(rawX, rawY, x, y);
    }
    emitTouchEvent(sendJson, eventName, x, y, rawX, rawY);
    return true;
  }
  return false;
}
