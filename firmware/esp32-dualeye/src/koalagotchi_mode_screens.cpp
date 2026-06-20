#include <Arduino.h>
#include <string.h>

#include "config.h"
#include "koalagotchi_mode_screens.h"

#if ENABLE_DISPLAY_BOOT_ANIMATION
#include <TFT_eSPI.h>

static TFT_eSPI tft = TFT_eSPI();
static bool screen_ready = false;

static uint16_t c565(uint8_t r, uint8_t g, uint8_t b) { return tft.color565(r, g, b); }
static int clampPct(int value) { return value < 0 ? 0 : value > 100 ? 100 : value; }

static void ensureScreenReady() {
  if (!screen_ready) {
    tft.init();
    tft.setRotation(DISPLAY_ROTATION);
    screen_ready = true;
  }
}

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
  for (int i = 0; i < 7; ++i) tft.drawLine(px[i], py[i], px[(i + 1) % 7], py[(i + 1) % 7], edge);
  uint16_t dark = c565(102, 39, 8);
  tft.drawLine(cx - 41, cy + 25, cx - 12, cy - 28, dark);
  tft.drawLine(cx - 12, cy - 28, cx + 2, cy - 25, dark);
  tft.drawLine(cx + 5, cy + 5, cx + 47, cy - 29, dark);
}

static void drawKoala(int cx, int cy, bool rowdy, uint16_t leftEye, uint16_t rightEye) {
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

  tft.fillCircle(cx - 27, cy - 6, 15, leftEye);
  tft.fillCircle(cx + 27, cy - 6, 15, rightEye);
  tft.fillCircle(cx - 25, cy - 5, 6, black);
  tft.fillCircle(cx + 29, cy - 5, 6, black);
  tft.fillCircle(cx - 21, cy - 12, 3, TFT_WHITE);
  tft.fillCircle(cx + 33, cy - 12, 3, TFT_WHITE);

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
  if (rowdy) {
    tft.drawLine(cx - 20, cy + 34, cx, cy + 43, black);
    tft.drawLine(cx, cy + 43, cx + 20, cy + 34, black);
  } else {
    tft.drawLine(cx - 20, cy + 31, cx - 9, cy + 39, black);
    tft.drawLine(cx - 9, cy + 39, cx, cy + 31, black);
    tft.drawLine(cx, cy + 31, cx + 9, cy + 39, black);
    tft.drawLine(cx + 9, cy + 39, cx + 20, cy + 31, black);
  }

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
  tft.drawString(eucalyptusMode ? "Eucalyptus haze cleaned the noise." : "What comes in gets sent back clean.", 178, 250);

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

#else

void drawKoalagotchiModeScreen(const char *mode, const char *mood, int contentment, int xp_percent) {
  (void)mode;
  (void)mood;
  (void)contentment;
  (void)xp_percent;
}

#endif
