#include <Arduino.h>
#include <math.h>
#include <string.h>

#include "config.h"
#include "koalagotchi_mode_screens.h"

#if ENABLE_DISPLAY_BOOT_ANIMATION
#include <TFT_eSPI.h>

static TFT_eSPI tft = TFT_eSPI();
static bool screenReady = false;

struct Rgb {
  uint8_t r;
  uint8_t g;
  uint8_t b;
};

struct EyeState {
  char look[18];
  char animation[18];
  char leftHex[10];
  char rightHex[10];
  Rgb left;
  Rgb right;
  int brightness;
  uint8_t frame;
  uint32_t lastFrameMs;
};

static EyeState eyes = {"cyber", "pulse", "#A54BFF", "#32FF71", {165, 75, 255}, {50, 255, 113}, 100, 0, 0};
static char lastMode[20] = "eucalyptus";
static char lastMood[28] = "calm";
static int lastContentment = 75;
static int lastXp = 88;
static bool hasLast = false;

static uint16_t c565(uint8_t r, uint8_t g, uint8_t b) { return tft.color565(r, g, b); }
static int clampPct(int v) { return v < 0 ? 0 : v > 100 ? 100 : v; }
static int clamp8(int v) { return v < 0 ? 0 : v > 255 ? 255 : v; }

static bool eqi(const char *a, const char *b) {
  if (!a || !b) return false;
  while (*a && *b) {
    char ca = (*a >= 'A' && *a <= 'Z') ? *a + 32 : *a;
    char cb = (*b >= 'A' && *b <= 'Z') ? *b + 32 : *b;
    if (ca != cb) return false;
    ++a;
    ++b;
  }
  return *a == 0 && *b == 0;
}

static int hexNibble(char ch) {
  if (ch >= '0' && ch <= '9') return ch - '0';
  if (ch >= 'a' && ch <= 'f') return ch - 'a' + 10;
  if (ch >= 'A' && ch <= 'F') return ch - 'A' + 10;
  return -1;
}

static Rgb parseColor(const char *hex, Rgb fallback, char *stored, size_t storedLen) {
  if (!hex) return fallback;
  const char *p = hex[0] == '#' ? hex + 1 : hex;
  if (strlen(p) != 6) return fallback;
  int n[6];
  for (int i = 0; i < 6; ++i) {
    n[i] = hexNibble(p[i]);
    if (n[i] < 0) return fallback;
  }
  Rgb out = {(uint8_t)((n[0] << 4) | n[1]), (uint8_t)((n[2] << 4) | n[3]), (uint8_t)((n[4] << 4) | n[5])};
  snprintf(stored, storedLen, "#%02X%02X%02X", out.r, out.g, out.b);
  return out;
}

static Rgb scaleColor(Rgb v, int pct) {
  pct = clampPct(pct);
  return {(uint8_t)clamp8((int)v.r * pct / 100), (uint8_t)clamp8((int)v.g * pct / 100), (uint8_t)clamp8((int)v.b * pct / 100)};
}

static void ready() {
  if (!screenReady) {
    tft.init();
    tft.setRotation(DISPLAY_ROTATION);
    screenReady = true;
  }
}

bool setKoalagotchiEyeStyle(const char *look, const char *left_color, const char *right_color, const char *animation, int brightness_percent) {
  snprintf(eyes.look, sizeof(eyes.look), "%s", look && look[0] ? look : "cyber");
  snprintf(eyes.animation, sizeof(eyes.animation), "%s", animation && animation[0] ? animation : "pulse");
  eyes.left = parseColor(left_color, eyes.left, eyes.leftHex, sizeof(eyes.leftHex));
  eyes.right = parseColor(right_color, eyes.right, eyes.rightHex, sizeof(eyes.rightHex));
  eyes.brightness = clampPct(brightness_percent <= 0 ? 100 : brightness_percent);
  eyes.frame = 0;
  if (screenReady && hasLast) drawKoalagotchiModeScreen(lastMode, lastMood, lastContentment, lastXp);
  return true;
}

void resetKoalagotchiEyeStyle() { setKoalagotchiEyeStyle("cyber", "#A54BFF", "#32FF71", "pulse", 100); }
const char *getKoalagotchiEyeLook() { return eyes.look; }
const char *getKoalagotchiEyeAnimation() { return eyes.animation; }
const char *getKoalagotchiLeftEyeHex() { return eyes.leftHex; }
const char *getKoalagotchiRightEyeHex() { return eyes.rightHex; }
int getKoalagotchiEyeBrightness() { return eyes.brightness; }

static void drawBar(int x, int y, int w, int h, int pct, uint16_t fg) {
  pct = clampPct(pct);
  tft.fillRoundRect(x, y, w, h, 4, c565(8, 15, 24));
  tft.drawRoundRect(x, y, w, h, 4, c565(50, 90, 105));
  tft.fillRoundRect(x + 2, y + 2, (w - 4) * pct / 100, h - 4, 3, fg);
}

static void drawStar(int x, int y, int r, uint16_t fg) {
  tft.fillTriangle(x, y - r, x - r / 3, y - r / 4, x + r / 3, y - r / 4, fg);
  tft.fillTriangle(x, y + r, x - r / 3, y + r / 4, x + r / 3, y + r / 4, fg);
  tft.fillTriangle(x - r, y, x - r / 4, y - r / 3, x - r / 4, y + r / 3, fg);
  tft.fillTriangle(x + r, y, x + r / 4, y - r / 3, x + r / 4, y + r / 3, fg);
  tft.fillCircle(x, y, r / 2, fg);
}

static void drawLeaf(int x, int y, uint16_t fill, uint16_t edge) {
  tft.fillTriangle(x - 16, y, x, y - 6, x + 16, y, fill);
  tft.fillTriangle(x - 16, y, x, y + 6, x + 16, y, fill);
  tft.drawLine(x - 16, y, x + 16, y, edge);
}

static void drawBoomerang(int cx, int cy, uint16_t fill, uint16_t edge) {
  int px[] = {cx - 54, cx - 14, cx + 4, cx - 12, cx + 56, cx + 72, cx + 3};
  int py[] = {cy + 34, cy - 44, cy - 35, cy - 1, cy - 42, cy - 22, cy + 56};
  for (int i = 0; i < 5; ++i) {
    tft.fillTriangle(px[0], py[0], px[i + 1], py[i + 1], px[i + 2], py[i + 2], fill);
  }
  for (int i = 0; i < 7; ++i) {
    const int j = (i + 1) % 7;
    tft.drawLine(px[i], py[i], px[j], py[j], edge);
  }
}

static void drawOneEye(int x, int y, Rgb rgb, bool leftSide) {
  int frame = eyes.frame % 16;
  int pulse = eqi(eyes.animation, "pulse") ? (frame < 8 ? frame : 16 - frame) : 0;
  int r = 18 + pulse / 2;
  int ry = r;
  if (eqi(eyes.animation, "blink") && (frame == 5 || frame == 6)) ry = 3;
  if (eqi(eyes.animation, "sleepy")) ry = 8;
  Rgb sc = scaleColor(rgb, eyes.brightness);
  uint16_t fg = c565(sc.r, sc.g, sc.b);
  uint16_t glow = c565(clamp8(sc.r + 35), clamp8(sc.g + 35), clamp8(sc.b + 35));
  uint16_t bg = c565(3, 6, 10);

  tft.drawCircle(x, y, r + 5, glow);
  tft.drawCircle(x, y, r + 2, fg);

  if (eqi(eyes.look, "star")) {
    drawStar(x, y, r, fg);
  } else if (eqi(eyes.look, "heart")) {
    tft.fillCircle(x - r / 3, y - r / 4, r / 2, fg);
    tft.fillCircle(x + r / 3, y - r / 4, r / 2, fg);
    tft.fillTriangle(x - r, y, x + r, y, x, y + r, fg);
  } else if (eqi(eyes.look, "slit")) {
    tft.fillEllipse(x, y, r, max(3, ry / 2), fg);
    tft.fillRoundRect(x - 2, y - ry, 4, ry * 2, 2, bg);
  } else if (eqi(eyes.look, "angry")) {
    tft.fillEllipse(x, y, r, ry, fg);
    tft.drawLine(x - r, y - 12, x + r, y - 3, bg);
    tft.fillCircle(x + (leftSide ? 3 : -3), y, 5, bg);
  } else if (eqi(eyes.look, "x")) {
    tft.drawLine(x - r, y - r, x + r, y + r, fg);
    tft.drawLine(x + r, y - r, x - r, y + r, fg);
  } else {
    tft.fillEllipse(x, y, r, ry, fg);
    tft.fillCircle(x + (leftSide ? 3 : -3), y, 6, bg);
  }

  if (eqi(eyes.animation, "scan")) {
    int sx = x - r + ((frame * r * 2) / 15);
    tft.drawFastVLine(sx, y - r, r * 2, TFT_WHITE);
  } else if (eqi(eyes.animation, "glitch")) {
    tft.fillRect(x - r, y - 2 + (frame % 3), r * 2, 3, glow);
  }
}

static void drawKoala(int cx, int cy, bool rowdy) {
  uint16_t fur = c565(158, 169, 182);
  uint16_t face = c565(220, 231, 238);
  uint16_t ear = c565(112, 124, 138);
  uint16_t black = c565(3, 6, 10);
  uint16_t line = c565(29, 35, 43);

  tft.fillEllipse(cx, cy + 70, 60, 13, TFT_BLACK);
  tft.fillCircle(cx - 49, cy - 49, 30, ear);
  tft.fillCircle(cx + 49, cy - 49, 30, ear);
  tft.fillCircle(cx - 49, cy - 49, 15, c565(52, 59, 70));
  tft.fillCircle(cx + 49, cy - 49, 15, c565(52, 59, 70));
  tft.fillRoundRect(cx - 65, cy - 58, 130, 116, 38, fur);
  tft.drawRoundRect(cx - 65, cy - 58, 130, 116, 38, c565(230, 238, 244));
  tft.fillRoundRect(cx - 49, cy - 33, 98, 78, 30, face);
  drawOneEye(cx - 27, cy - 6, eyes.left, true);
  drawOneEye(cx + 27, cy - 6, eyes.right, false);

  if (rowdy) {
    tft.drawLine(cx - 43, cy - 26, cx - 14, cy - 16, line);
    tft.drawLine(cx + 14, cy - 16, cx + 43, cy - 26, line);
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
  ready();
  snprintf(lastMode, sizeof(lastMode), "%s", mode && mode[0] ? mode : "eucalyptus");
  snprintf(lastMood, sizeof(lastMood), "%s", mood && mood[0] ? mood : "calm");
  lastContentment = clampPct(contentment);
  lastXp = clampPct(xp_percent);
  hasLast = true;

  const bool eucalyptusMode = !mode || strcmp(mode, "boomerang") != 0;
  const bool rowdy = !eucalyptusMode || (mood && strstr(mood, "rowdy") != nullptr);
  const int w = tft.width();
  const int h = tft.height();
  const uint16_t cyan = c565(35, 227, 255);
  const uint16_t green = c565(50, 255, 113);
  const uint16_t orange = c565(255, 154, 38);
  const uint16_t yellow = c565(255, 226, 78);
  const uint16_t white = c565(226, 246, 241);
  const uint16_t accent = eucalyptusMode ? green : orange;

  contentment = clampPct(contentment);
  xp_percent = clampPct(xp_percent);
  tft.fillScreen(c565(5, 8, 16));
  for (int x = 0; x < w; x += 24) tft.drawFastVLine(x, 42, h - 82, c565(12, 41, 50));
  for (int y = 48; y < h - 40; y += 24) tft.drawFastHLine(0, y, w, c565(12, 41, 50));
  tft.drawRect(0, 0, w, h, accent);

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

  tft.fillRoundRect(12, 47, 128, 38, 8, c565(8, 15, 24));
  tft.drawRoundRect(12, 47, 128, 38, 8, c565(38, 92, 108));
  tft.setTextColor(c565(102, 143, 150), c565(8, 15, 24));
  tft.drawString("MOOD", 20, 55);
  tft.setTextColor(accent, c565(8, 15, 24));
  tft.drawString(eucalyptusMode ? "CALM" : "ROWDY", 20, 69);

  tft.fillRoundRect(12, 91, 128, 38, 8, c565(8, 15, 24));
  tft.drawRoundRect(12, 91, 128, 38, 8, c565(38, 92, 108));
  tft.setTextColor(c565(102, 143, 150), c565(8, 15, 24));
  tft.drawString("XP", 20, 99);
  drawBar(20, 113, 112, 12, xp_percent, accent);

  tft.fillRoundRect(12, 135, 128, 41, 8, c565(8, 15, 24));
  tft.drawRoundRect(12, 135, 128, 41, 8, c565(38, 92, 108));
  tft.setTextColor(c565(102, 143, 150), c565(8, 15, 24));
  tft.drawString("CONTENT", 20, 143);
  drawBar(20, 157, 112, 12, contentment, accent);

  tft.fillRoundRect(151, 47, w - 163, h - 94, 18, c565(7, 13, 23));
  tft.drawRoundRect(151, 47, w - 163, h - 94, 18, accent);
  tft.fillRect(155, 51, w - 171, h - 102, eucalyptusMode ? c565(5, 32, 22) : c565(37, 16, 6));

  if (eucalyptusMode) {
    for (int i = 0; i < 18; ++i) {
      drawLeaf(170 + (i * 39) % max(1, w - 200), 62 + ((i * 37) % max(1, h - 145)), green, c565(194, 255, 209));
    }
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

  drawKoala(min(w - 95, max(225, w / 2 + 55)), min(h - 160, 155), rowdy);

  tft.fillRoundRect(168, 59, 128, 35, 9, eucalyptusMode ? c565(10, 95, 52) : c565(127, 54, 11));
  tft.drawRoundRect(168, 59, 128, 35, 9, accent);
  tft.setTextColor(white, eucalyptusMode ? c565(10, 95, 52) : c565(127, 54, 11));
  tft.drawString(eucalyptusMode ? "EUCALYPTUS" : "BOOMERANG", 178, 67);
  tft.setTextColor(accent, c565(5, 8, 16));
  tft.drawString("LOOK", 20, h - 71);
  tft.drawString(eyes.look, 60, h - 71);
  tft.drawString("ANIM", 148, h - 71);
  tft.drawString(eyes.animation, 195, h - 71);
  drawFooter(accent, eucalyptusMode);
}

void tickKoalagotchiEyes() {
  if (!screenReady || !hasLast || eqi(eyes.animation, "static")) return;
  uint32_t now = millis();
  if (now - eyes.lastFrameMs < 180) return;
  eyes.lastFrameMs = now;
  eyes.frame = (eyes.frame + 1) % 16;
  drawKoalagotchiModeScreen(lastMode, lastMood, lastContentment, lastXp);
}

#else
void drawKoalagotchiModeScreen(const char *mode, const char *mood, int contentment, int xp_percent) { (void)mode; (void)mood; (void)contentment; (void)xp_percent; }
bool setKoalagotchiEyeStyle(const char *look, const char *left_color, const char *right_color, const char *animation, int brightness_percent) { (void)look; (void)left_color; (void)right_color; (void)animation; (void)brightness_percent; return false; }
void resetKoalagotchiEyeStyle() {}
void tickKoalagotchiEyes() {}
const char *getKoalagotchiEyeLook() { return "disabled"; }
const char *getKoalagotchiEyeAnimation() { return "disabled"; }
const char *getKoalagotchiLeftEyeHex() { return "#000000"; }
const char *getKoalagotchiRightEyeHex() { return "#000000"; }
int getKoalagotchiEyeBrightness() { return 0; }
#endif
