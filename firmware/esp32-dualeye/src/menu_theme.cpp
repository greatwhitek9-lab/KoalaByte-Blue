#include <Arduino.h>
#include <TFT_eSPI.h>

#include "menu_theme.h"

static uint16_t menuColor(TFT_eSPI &tft, uint8_t r, uint8_t g, uint8_t b) {
  return tft.color565(r, g, b);
}

static void drawLeaf(TFT_eSPI &tft, int x, int y, int r, int lean) {
  const uint16_t leafDark = menuColor(tft, 34, 95, 62);
  const uint16_t leaf = menuColor(tft, 93, 168, 112);
  const uint16_t vein = menuColor(tft, 152, 225, 168);
  tft.fillCircle(x, y, r, leafDark);
  tft.fillCircle(x + lean, y, max(2, r - 3), leaf);
  tft.drawLine(x - r / 2, y, x + r / 2 + lean, y, vein);
}

static void drawBubbleText(TFT_eSPI &tft, const char *text, int x, int y, uint16_t fill, uint16_t outline, int textSize, int outlineRadius) {
  tft.setTextDatum(MC_DATUM);
  tft.setTextSize(textSize);
  tft.setTextColor(outline, TFT_BLACK);
  for (int dx = -outlineRadius; dx <= outlineRadius; ++dx) {
    for (int dy = -outlineRadius; dy <= outlineRadius; ++dy) {
      if (dx * dx + dy * dy <= outlineRadius * outlineRadius) {
        tft.drawString(text, x + dx, y + dy);
      }
    }
  }
  tft.setTextColor(fill, outline);
  tft.drawString(text, x, y);
}

void drawEucalyptusMenuBorder(TFT_eSPI &tft) {
  const int w = tft.width();
  const int h = tft.height();
  const int m = max(8, min(w, h) / 28);
  const uint16_t bark = menuColor(tft, 73, 58, 34);
  const uint16_t barkHi = menuColor(tft, 123, 94, 50);

  tft.drawRect(m, m, w - (2 * m), h - (2 * m), bark);
  tft.drawRect(m + 2, m + 2, w - (2 * (m + 2)), h - (2 * (m + 2)), barkHi);

  const int xStep = max(24, w / 9);
  for (int x = m + 18; x < w - m - 10; x += xStep) {
    drawLeaf(tft, x, m + 2, 6, 3);
    drawLeaf(tft, x + xStep / 3, h - m - 2, 6, -3);
  }

  const int yStep = max(24, h / 6);
  for (int y = m + 20; y < h - m - 10; y += yStep) {
    drawLeaf(tft, m + 2, y, 6, 3);
    drawLeaf(tft, w - m - 2, y + yStep / 3, 6, -3);
  }
}

void drawJungleMenuTitle(TFT_eSPI &tft, const char *title) {
  const int w = tft.width();
  const int h = tft.height();
  const uint16_t fill = menuColor(tft, 143, 221, 103);
  const uint16_t outline = menuColor(tft, 28, 67, 38);
  drawBubbleText(tft, title, w / 2, max(24, h / 8), fill, outline, 2, 3);
}

void drawJungleMenuItem(TFT_eSPI &tft, int row, const char *label, bool selected, bool enabled) {
  const int w = tft.width();
  const int h = tft.height();
  const int rowH = max(34, h / 7);
  const int x = w / 10;
  const int y = max(54, h / 4) + row * rowH;
  const int boxW = w - (2 * x);
  const int boxH = max(26, rowH - 8);

  const uint16_t itemFill = enabled ? menuColor(tft, 245, 236, 158) : menuColor(tft, 112, 119, 104);
  const uint16_t itemOutline = selected ? menuColor(tft, 49, 170, 82) : menuColor(tft, 31, 84, 44);
  const uint16_t selectedFill = menuColor(tft, 190, 246, 124);
  const uint16_t selectedGlow = menuColor(tft, 123, 245, 144);
  const uint16_t textFill = menuColor(tft, 9, 30, 20);

  if (selected) {
    tft.drawRoundRect(x - 5, y - 5, boxW + 10, boxH + 10, 14, selectedGlow);
    drawLeaf(tft, x - 10, y + boxH / 2, 6, 3);
    drawLeaf(tft, x + boxW + 10, y + boxH / 2, 6, -3);
  }

  tft.fillRoundRect(x, y, boxW, boxH, 12, selected ? selectedFill : itemFill);
  tft.drawRoundRect(x, y, boxW, boxH, 12, itemOutline);
  drawBubbleText(tft, label, w / 2, y + boxH / 2, textFill, selected ? selectedFill : itemFill, 1, 1);
}
