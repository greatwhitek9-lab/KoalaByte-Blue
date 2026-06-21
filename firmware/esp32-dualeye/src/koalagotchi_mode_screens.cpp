#include <Arduino.h>
#include <math.h>
#include <string.h>

#include "config.h"
#include "koalagotchi_mode_screens.h"

#if ENABLE_DISPLAY_BOOT_ANIMATION
#include <TFT_eSPI.h>

static TFT_eSPI tft = TFT_eSPI();
static bool screen_ready = false;

struct EyeRgb {
  uint8_t r;
  uint8_t g;
  uint8_t b;
};

struct EyeStyleState {
  char look[18];
  char animation[18];
  char leftHex[10];
  char rightHex[10];
  EyeRgb left;
  EyeRgb right;
  int brightness;
  uint8_t frame;
  uint32_t lastFrameMs;
  bool active;
};

static EyeStyleState eyeStyle = {
  "cyber",
  "pulse",
  "#A54BFF",
  "#32FF71",
  {165, 75, 255},
  {50, 255, 113},
  100,
  0,
  0,
  true,
};

static char lastMode[20] = "eucalyptus";
static char lastMood[28] = "calm";
static int lastContentment = 75;
static int lastXp = 88;
static bool hasLastScreen = false;

static uint16_t c565(uint8_t r, uint8_t g, uint8_t b) { return tft.color565(r, g, b); }
static uint16_t c565Eye(EyeRgb c) { return c565(c.r, c.g, c.b); }
static int clampPct(int value) { return value < 0 ? 0 : value > 100 ? 100 : value; }
static int clamp8(int value) { return value < 0 ? 0 : value > 255 ? 255 : value; }

static bool eqi(const char *a, const char *b) {
  if (!a || !b) return false;
  while (*a && *b) {
    char ca = *a >= 'A' && *a <= 'Z' ? *a + 32 : *a;
    char cb = *b >= 'A' && *b <= 'Z' ? *b + 32 : *b;
    if (ca != cb) return false;
    ++a;
    ++b;
  }
  return *a == 0 && *b == 0;
}

static int hexNibble(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

static EyeRgb parseHexColor(const char *hex, EyeRgb fallback, char *stored, size_t storedLen) {
  if (!hex) return fallback;
  const char *p = hex[0] == '#' ? hex + 1 : hex;
  if (strlen(p) != 6) return fallback;
  int n[6];
  for (int i = 0; i < 6; ++i) {
    n[i] = hexNibble(p[i]);
    if (n[i] < 0) return fallback;
  }
  EyeRgb out = {(uint8_t)((n[0] << 4) | n[1]), (uint8_t)((n[2] << 4) | n[3]), (uint8_t)((n[4] << 4) | n[5])};
  if (stored && storedLen > 0) snprintf(stored, storedLen, "#%02X%02X%02X", out.r, out.g, out.b);
  return out;
}

static EyeRgb scaleColor(EyeRgb c, int pct) {
  pct = clampPct(pct);
  return {(uint8_t)clamp8((int)c.r * pct / 100), (uint8_t)clamp8((int)c.g * pct / 100), (uint8_t)clamp8((int)c.b * pct / 100)};
}

static void copyToken(char *dst, size_t len, const char *value, const char *fallback) {
  const char *src = value && value[0] ? value : fallback;
  snprintf(dst, len, "%s", src);
}

static void ensureScreenReady() {
  if (!screen_ready) {
    tft.init();
    tft.setRotation(DISPLAY_ROTATION);
    screen_ready = true;
  }
}

bool setKoalagotchiEyeStyle(const char *look, const char *left_color, const char *right_color, const char *animation, int brightness_percent) {
  copyToken(eyeStyle.look, sizeof(eyeStyle.look), look, "cyber");
  copyToken(eyeStyle.animation, sizeof(eyeStyle.animation), animation, "pulse");
  eyeStyle.left = parseHexColor(left_color, eyeStyle.left, eyeStyle.leftHex, sizeof(eyeStyle.leftHex));
  eyeStyle.right = parseHexColor(right_color, eyeStyle.right, eyeStyle.rightHex, sizeof(eyeStyle.rightHex));
  eyeStyle.brightness = clampPct(brightness_percent <= 0 ? 100 : brightness_percent);
  eyeStyle.active = true;
  eyeStyle.frame = 0;
  if (screen_ready && hasLastScreen) drawKoalagotchiModeScreen(lastMode, lastMood, lastContentment, lastXp);
  return true;
}

void resetKoalagotchiEyeStyle() {
  setKoalagotchiEyeStyle("cyber", "#A54BFF", "#32FF71", "pulse", 100);
}

const char *getKoalagotchiEyeLook() { return eyeStyle.look; }
const char *getKoalagotchiEyeAnimation() { return eyeStyle.animation; }
const char *getKoalagotchiLeftEyeHex() { return eyeStyle.leftHex; }
const char *getKoalagotchiRightEyeHex() { return eyeStyle.rightHex; }
int getKoalagotchiEyeBrightness() { return eyeStyle.brightness; }

static void drawBar(int x, int y, int w, int h, int pct, uint16_t color) {
  pct = clampPct(pct);
  tft.fillRoundRect(x, y, w, h, max(2, h / 3), c565(3, 8, 12));
  tft.drawRoundRect(x, y, w, h, max(2, h / 3), c565(45, 70, 80));
  int fillW = ((w - 4) * pct) / 100;
  if (fillW > 0) tft.fillRoundRect(x + 2, y + 2, fillW, h - 4, max(2, h / 4), color);
}

static void drawLeaf(int x, int y, float scale, bool flip, uint16_t fill, uint16_t edge) {
  int w = max(7, (int)(22.0f * scale));
  int h = max(4, (int)(8.0f * scale));
  int sx = flip ? -1 : 1;
  tft.fillTriangle(x - sx * w, y, x, y - h, x + sx * w, y, fill);
  tft.fillTriangle(x - sx * w, y, x, y + h, x + sx * w, y, fill);
  tft.drawLine(x - sx * w, y, x + sx * w, y, edge);
}

static void drawBoomerang(int cx, int cy, uint16_t fill, uint16_t edge) {
  int px[] = {cx - 54, cx - 14, cx + 4, cx - 12, cx + 56, cx + 72, cx + 3};
  int py[] = {cy + 34, cy - 44, cy - 35, cy - 1, cy - 42, cy - 22, cy + 56};
  for (int i = 0; i < 5; ++i) tft.fillTriangle(px[0], py[0], px[i + 1], py[i + 1], px[i + 2], py[i + 2], fill);
  for (int i = 0; i < 7; ++i) tft.drawLine(px[i], py[i], px[(i + 1) % 7], edge);
}

static void drawStarEye(int cx, int cy, int r, uint16_t color) {
  tft.fillTriangle(cx, cy - r, cx - r / 3, cy - r / 4, cx + r / 3, cy - r / 4, color);
  tft.fillTriangle(cx, cy + r, cx - r / 3, cy + r / 4, cx + r / 3, cy + r / 4, color);
  tft.fillTriangle(cx - r, cy, cx - r / 4, cy - r / 3, cx - r / 4, cy + r / 3, color);
  tft.fillTriangle(cx + r, cy, cx + r / 4, cy - r / 3, cx + r / 4, cy + r / 3, color);
  tft.fillCircle(cx, cy, r / 2, color);
}

static void drawHeartEye(int cx, int cy, int r, uint16_t color) {
  tft.fillCircle(cx - r / 3, cy - r / 4, r / 2, color);
  tft.fillCircle(cx + r / 3, cy - r / 4, r / 2, color);
  tft.fillTriangle(cx - r, cy, cx + r, cy, cx, cy + r, color);
}

static void drawCustomEye(int cx, int cy, EyeRgb rgb, bool leftSide, bool rowdy) {
  int frame = eyeStyle.frame % 16;
  int pulse = eqi(eyeStyle.animation, "pulse") ? (frame < 8 ? frame : 16 - frame) : 0;
  int r = 15 + pulse / 2;
  int ry = 15;
  if (eqi(eyeStyle.animation, "blink") && (frame == 5 || frame == 6)) ry = 3;
  if (eqi(eyeStyle.animation, "sleepy")) ry = 7;
  EyeRgb bright = scaleColor(rgb, eyeStyle.brightness);
  uint16_t eye = c565Eye(bright);
  uint16_t glow = c565(clamp8(bright.r + 35), clamp8(bright.g + 35), clamp8(bright.b + 35));
  uint16_t black = c565(3, 6, 10);

  tft.drawCircle(cx, cy, r + 4, glow);
  tft.drawCircle(cx, cy, r + 2, eye);

  if (eqi(eyeStyle.look, "star")) {
    drawStarEye(cx, cy, r, eye);
  } else if (eqi(eyeStyle.look, "heart")) {
    drawHeartEye(cx, cy, r, eye);
  } else if (eqi(eyeStyle.look, "slit")) {
    tft.fillEllipse(cx, cy, r + 3, max(3, ry / 2), eye);
    tft.fillRoundRect(cx - 2, cy - ry, 4, ry * 2, 2, black);
  } else if (eqi(eyeStyle.look, "sleepy")) {
    tft.fillEllipse(cx, cy + 2, r + 3, 6, eye);
    tft.drawFastHLine(cx - r, cy - 4, r * 2, black);
  } else if (eqi(eyeStyle.look, "angry")) {
    tft.fillEllipse(cx, cy, r + 1, ry, eye);
    tft.drawLine(cx - r, cy - 12, cx + r, cy - 3, black);
    tft.fillCircle(cx + (leftSide ? 3 : -3), cy, 5, black);
  } else if (eqi(eyeStyle.look, "x")) {
    tft.drawLine(cx - r, cy - r, cx + r, cy + r, eye);
    tft.drawLine(cx + r, cy - r, cx - r, cy + r, eye);
    tft.drawLine(cx - r, cy - r + 1, cx + r, cy + r + 1, glow);
    tft.drawLine(cx + r, cy - r + 1, cx - r, cy + r + 1, glow);
  } else if (eqi(eyeStyle.look, "cyber")) {
    tft.fillCircle(cx, cy, r, eye);
    tft.fillCircle(cx + (leftSide ? 2 : -2), cy, 6, black);
    tft.drawFastHLine(cx - r + 2, cy - 6, r * 2 - 4, black);
    tft.drawFastHLine(cx - r + 2, cy + 6, r * 2 - 4, black);
  } else {
    tft.fillEllipse(cx, cy, r, ry, eye);
    tft.fillCircle(cx + (leftSide ? 2 : -2), cy + 1, 6, black);
  }

  if (eqi(eyeStyle.animation, "scan")) {
    int sx = cx - r + ((frame * (r * 2)) / 15);
    tft.drawFastVLine(sx, cy - r, r * 2, TFT_WHITE);
  } else if (eqi(eyeStyle.animation, "glitch")) {
    int dx = (frame % 4) - 1;
    tft.fillRect(cx - r + 2, cy - 2 + dx, r * 2 - 4, 3, glow);
    tft.fillRect(cx - 5 + dx, cy + 7, 10, 2, TFT_WHITE);
  } else if (rowdy) {
    tft.fillCircle(cx + (leftSide ? 7 : -7), cy - 8, 3, TFT_WHITE);
  } else {
    tft.fillCircle(cx + (leftSide ? 6 : -6), cy - 7, 3, TFT_WHITE);
  }
}

static void drawKoala(int cx, int cy, bool rowdy, uint16_t leftEyeFallback, uint16_t rightEyeFallback) {
  uint16_t fur = c565(158, 169, 182);
  uint16_t furDark = c565(111, 123, 137);
  uint16_t inner = c565(52, 59, 70);
  uint16_t face = c565(220, 231, 238);
  uint16_t line = c565(29, 35, 43);
  uint16_t black = c565(3, 6, 10);

  tft.fillEllipse(cx, cy + 70, 60, 13, TFT_BLACK);
  tft.fillCircle(cx - 49, cy - 49, 30, furDark);
  tft.fillCircle(cx + 49, cy - 49, 30, furDark);
  tft.drawCircle(cx - 49, cy - 49, 30, c565(215, 227, 234));
  tft.drawCircle(cx + 49, cy - 49, 30, c565(215, 227, 234));
  tft.fillCircle(cx - 49, cy - 49, 15, inner);
  tft.fillCircle(cx + 49, cy - 49, 15, inner);
  tft.fillRoundRect(cx - 65, cy - 58, 130, 116, 38, fur);
  tft.drawRoundRect(cx - 65, cy - 58, 130, 116, 38, c565(230, 238, 244));
  tft.fillRoundRect(cx - 49, cy - 33, 98, 78, 30, face);

  if (eyeStyle.active) {
    drawCustomEye(cx - 27, cy - 6, eyeStyle.left, true, rowdy);
    drawCustomEye(cx + 27, cy - 6, eyeStyle.right, false, rowdy);
  } else {
    tft.fillCircle(cx - 27, cy - 6, 15, leftEyeFallback);
    tft.fillCircle(cx + 27, cy - 6, 15, rightEyeFallback);
    tft.fillCircle(cx - 25, cy - 5, 6, black);
    tft.fillCircle(cx + 29, cy - 5, 6, black);
    tft.fillCircle(cx - 21, cy - 12, 3, TFT_WHITE);
    tft.fillCircle(cx + 33, cy - 12, 3, TFT_WHITE);
  }

  if (rowdy) {
    tft.drawLine(cx - 43, cy - 26, cx - 14, cy - 16, line);
    tft.drawLine(cx + 14, cy - 16, cx + 43, cy - 26, line);
    tft.drawLine(cx - 43, cy - 25, cx - 14, cy - 15, line);
    tft.drawLine(cx + 14, cy - 15, cx + 43, cy - 25, line);
  } else {
    tft.drawLine(cx - 42, cy - 24, cx - 28, cy - 29, line);
    tft.drawLine(cx - 28, cy - 29, cx - 13, cy - 20, line);
    tft.drawLine(cx + 13, cy - 20, cx + 28, cy - 29, line);
    tft.drawLine(cx + 28, cy - 29, cx + 42, cy - 24, line);
  }

  tft.fillRoundRect(cx - 14, cy + 13, 28, 18, 8, black);
  tft.drawLine(cx - 20, cy + 31, cx - 9, cy + 39, black);
  tft.drawLine(cx - 9, cy + 39, cx, cy + 31, black);
  tft.drawLine(cx, cy + 31, cx + 9, cy + 39, black);
  tft.drawLine(cx + 9, cy + 39, cx + 20, cy + 31, black);

  tft.fillRoundRect(cx - 45, cy + 53, 90, 74, 28, c565(124, 137, 151));
  tft.drawRoundRect(cx - 45, cy + 53, 90, 74, 28, c565(220, 232, 239));
  tft.fillEllipse(cx, cy + 94, 29, 24, c565(216, 227, 234));
  tft.fillRoundRect(cx - 32, cy + 52, 64, 14, 6, c565(7, 16, 26));
  tft.drawRoundRect(cx - 32, cy + 52, 64, 14, 6, c565(35, 227, 255));
  tft.setTextDatum(MC_DATUM);
  tft.setTextSize(1);
  tft.setTextColor(c565(35, 227, 255), c565(7, 16, 26));
  tft.drawString("KB", cx, cy + 60);
}

static void drawFooter(uint16_t accent, bool eucalyptusMode) {
  const int w = tft.width();
  const int y = tft.height() - 39;
  const char *keys[] = {"F1", "F2", "F3", "F4", "F5", "F6"};
  const char *labels[] = {"SCAN", "PET", "EUC", "BOOM", "LOG", "BACK"};
  const int bw = max(45, (w - 30) / 6 - 6);
  tft.fillRoundRect(7, y, w - 14, 32, 8, c565(5, 12, 20));
  tft.drawRoundRect(7, y, w - 14, 32, 8, c565(32, 92, 108));
  tft.setTextSize(1);
  for (int i = 0; i < 6; ++i) {
    int x = 15 + i * (bw + 6);
    bool active = (eucalyptusMode && i == 2) || (!eucalyptusMode && i == 3);
    uint16_t fill = active ? (eucalyptusMode ? c565(36, 55, 32) : c565(55, 36, 18)) : c565(11, 29, 39);
    tft.fillRoundRect(x, y + 7, bw, 18, 5, fill);
    tft.drawRoundRect(x, y + 7, bw, 18, 5, active ? accent : c565(45, 110, 120));
    tft.setTextColor(c565(255, 226, 78), fill);
    tft.drawString(keys[i], x + 11, y + 16);
    tft.setTextColor(c565(226, 246, 241), fill);
    tft.drawString(labels[i], x + bw / 2 + 8, y + 16);
  }
}

void drawKoalagotchiModeScreen(const char *mode, const char *mood, int contentment, int xp_percent) {
  ensureScreenReady();
  snprintf(lastMode, sizeof(lastMode), "%s", mode && mode[0] ? mode : "eucalyptus");
  snprintf(lastMood, sizeof(lastMood), "%s", mood && mood[0] ? mood : "calm");
  lastContentment = clampPct(contentment);
  lastXp = clampPct(xp_percent);
  hasLastScreen = true;

  const bool eucalyptusMode = !mode || strcmp(mode, "boomerang") != 0;
  const bool rowdy = !eucalyptusMode || (mood && strstr(mood, "rowdy") != nullptr);
  const int w = tft.width();
  const int h = tft.height();
  const uint16_t cyan = c565(35, 227, 255);
  const uint16_t green = c565(50, 255, 113);
  const uint16_t purple = c565(165, 75, 255);
  const uint16_t orange = c565(255, 154, 38);
  const uint16_t yellow = c565(255, 226, 78);
  const uint16_t white = c565(226, 246, 241);
  const uint16_t accent = eucalyptusMode ? green : orange;
  const uint16_t stage = eucalyptusMode ? c565(5, 32, 22) : c565(37, 16, 6);

  contentment = clampPct(contentment);
  xp_percent = clampPct(xp_percent);
  tft.fillScreen(c565(5, 8, 16));
  for (int x = 0; x < w; x += 24) tft.drawFastVLine(x, 42, h - 82, c565(12, 41, 50));
  for (int y = 48; y < h - 40; y += 24) tft.drawFastHLine(0, y, w, c565(12, 41, 50));
  tft.drawRect(0, 0, w, h, accent);
  tft.drawRect(1, 1, w - 2, h - 2, accent);

  tft.fillRoundRect(6, 5, w - 12, 35, 9, c565(7, 16, 26));
  tft.drawRoundRect(6, 5, w - 12, 35, 9, accent);
  tft.setTextDatum(TL_DATUM);
  tft.setTextSize(2);
  tft.setTextColor(cyan, c565(7, 16, 26));
  tft.drawString("KILLERKOALA // KOALAGOTCHI", 16, 10);
  tft.setTextSize(1);
  tft.setTextColor(yellow, c565(7, 16, 26));
  tft.drawString("LVL 18: LEGEND", max(280, w - 195), 12);
  tft.setTextColor(accent, c565(7, 16, 26));
  tft.drawString(eucalyptusMode ? "MODE: EUCALYPTUS" : "MODE: BOOMERANG", 16, 31);
  tft.setTextColor(green, c565(7, 16, 26));
  tft.drawString("SAFE LAB", w - 73, 31);

  tft.fillRoundRect(12, 47, 128, 38, 8, c565(8, 15, 24));
  tft.drawRoundRect(12, 47, 128, 38, 8, c565(38, 92, 108));
  tft.setTextColor(c565(102, 143, 150), c565(8, 15, 24)); tft.drawString("SESSION", 20, 55);
  tft.setTextColor(white, c565(8, 15, 24)); tft.drawString("00:18:44", 20, 69);
  tft.setTextColor(accent, c565(8, 15, 24)); tft.drawString("AUTO", 93, 69);

  tft.fillRoundRect(12, 91, 128, 38, 8, c565(8, 15, 24));
  tft.drawRoundRect(12, 91, 128, 38, 8, c565(38, 92, 108));
  tft.setTextColor(c565(102, 143, 150), c565(8, 15, 24)); tft.drawString("MOOD", 20, 99);
  tft.setTextColor(accent, c565(8, 15, 24)); tft.drawString(eucalyptusMode ? "CALM" : "ROWDY", 20, 113);
  drawBar(78, 104, 60, 14, eucalyptusMode ? 75 : 61, accent);

  tft.fillRoundRect(12, 135, 128, 41, 8, c565(8, 15, 24));
  tft.drawRoundRect(12, 135, 128, 41, 8, c565(38, 92, 108));
  tft.setTextColor(c565(102, 143, 150), c565(8, 15, 24)); tft.drawString("SIGNALS", 20, 143);
  tft.setTextColor(cyan, c565(8, 15, 24)); tft.drawString(eucalyptusMode ? "BLE WATCH" : "RETURN ARC", 20, 157);
  tft.setTextColor(accent, c565(8, 15, 24)); tft.drawString(eucalyptusMode ? "BLOCKS: 03" : "LOCK: 97%", 20, 169);

  tft.fillRoundRect(151, 47, w - 163, 168, 18, c565(7, 13, 23));
  tft.drawRoundRect(151, 47, w - 163, 168, 18, accent);
  tft.fillRect(155, 51, w - 171, 160, stage);

  if (eucalyptusMode) {
    for (int i = 0; i < 18; ++i) drawLeaf(170 + (i * 39) % max(1, w - 200), 62 + ((i * 37) % 130), 0.8f + (i % 3) * 0.14f, (i % 2) == 0, green, c565(194, 255, 209));
    tft.drawEllipse(303, 145, 113, 100, c565(20, 106, 60));
    tft.drawEllipse(303, 145, 92, 79, c565(30, 150, 75));
  } else {
    for (int a = 0; a < 360; a += 18) {
      float rad = (float)a * PI / 180.0f;
      tft.fillCircle(303 + (int)(cosf(rad) * 95.0f), 146 + (int)(sinf(rad) * 52.0f), 1, orange);
    }
    tft.drawEllipse(303, 146, 66, 36, c565(127, 54, 11));
    drawBoomerang(307, 84, orange, yellow);
  }

  tft.fillRoundRect(168, 59, 128, 35, 9, eucalyptusMode ? c565(10, 95, 52) : c565(127, 54, 11));
  tft.drawRoundRect(168, 59, 128, 35, 9, accent);
  tft.setTextColor(accent, eucalyptusMode ? c565(10, 95, 52) : c565(127, 54, 11));
  tft.drawString(eucalyptusMode ? "EUCALYPTUS" : "BOOMERANG", 178, 67);
  tft.setTextColor(white, eucalyptusMode ? c565(10, 95, 52) : c565(127, 54, 11));
  tft.drawString(eucalyptusMode ? "DEFENSE AURA" : "RETURN PATH", 178, 81);

  drawKoala(306, eucalyptusMode ? 137 : 141, rowdy, purple, green);

  tft.fillRoundRect(w - 125, 178, 99, 29, 8, stage);
  tft.drawRoundRect(w - 125, 178, 99, 29, 8, eucalyptusMode ? c565(42, 130, 72) : c565(150, 74, 24));
  tft.setTextColor(eucalyptusMode ? green : yellow, stage);
  tft.drawString(eucalyptusMode ? "BLOCKED: 03" : "LOCK: 97%", w - 117, 184);
  tft.setTextColor(white, stage);
  tft.drawString(eucalyptusMode ? "AURA: ON" : "RECALL: RDY", w - 117, 196);

  tft.fillRoundRect(166, 220, w - 180, 53, 12, c565(8, 13, 22));
  tft.drawRoundRect(166, 220, w - 180, 53, 12, accent);
  tft.setTextColor(white, c565(8, 13, 22));
  tft.drawString(eucalyptusMode ? "KillerKoala: chill shield is up." : "KillerKoala: boomerang path locked.", 178, 232);
  tft.setTextColor(accent, c565(8, 13, 22));
  tft.drawString(eucalyptusMode ? eyeStyle.look : eyeStyle.animation, 178, 250);

  tft.fillRoundRect(12, 182, 128, 91, 8, c565(8, 15, 24));
  tft.drawRoundRect(12, 182, 128, 91, 8, c565(38, 92, 108));
  tft.setTextColor(c565(102, 143, 150), c565(8, 15, 24)); tft.drawString("KOALA TASKS", 20, 190);
  const char *taskA[] = {"Watch BLE", "Clean noise", "Hold shield", "XP calm"};
  const char *taskB[] = {"Trace arc", "Return path", "Spin check", "XP rowdy"};
  const char **tasks = eucalyptusMode ? taskA : taskB;
  for (int i = 0; i < 4; ++i) {
    tft.setTextColor(i < 2 ? accent : (i == 2 ? cyan : yellow), c565(8, 15, 24));
    tft.drawString(i < 2 ? "*" : (i == 2 ? ">" : "+"), 22, 207 + i * 15);
    tft.setTextColor(white, c565(8, 15, 24));
    tft.drawString(tasks[i], 40, 207 + i * 15);
  }

  drawFooter(accent, eucalyptusMode);
}

void tickKoalagotchiEyes() {
  if (!screen_ready || !hasLastScreen || !eyeStyle.active) return;
  if (eqi(eyeStyle.animation, "static")) return;
  uint32_t now = millis();
  if (now - eyeStyle.lastFrameMs < 180) return;
  eyeStyle.lastFrameMs = now;
  eyeStyle.frame = (eyeStyle.frame + 1) % 16;
  drawKoalagotchiModeScreen(lastMode, lastMood, lastContentment, lastXp);
}

#else

void drawKoalagotchiModeScreen(const char *mode, const char *mood, int contentment, int xp_percent) {
  (void)mode;
  (void)mood;
  (void)contentment;
  (void)xp_percent;
}

bool setKoalagotchiEyeStyle(const char *look, const char *left_color, const char *right_color, const char *animation, int brightness_percent) {
  (void)look; (void)left_color; (void)right_color; (void)animation; (void)brightness_percent;
  return false;
}
void resetKoalagotchiEyeStyle() {}
void tickKoalagotchiEyes() {}
const char *getKoalagotchiEyeLook() { return "disabled"; }
const char *getKoalagotchiEyeAnimation() { return "disabled"; }
const char *getKoalagotchiLeftEyeHex() { return "#000000"; }
const char *getKoalagotchiRightEyeHex() { return "#000000"; }
int getKoalagotchiEyeBrightness() { return 0; }

#endif
