#include <Arduino.h>
#include <math.h>

#include "boot_animation.h"
#include "config.h"

#if ENABLE_DISPLAY_BOOT_ANIMATION
#include <TFT_eSPI.h>

static TFT_eSPI tft = TFT_eSPI();

static uint16_t c565(uint8_t r, uint8_t g, uint8_t b) {
  return tft.color565(r, g, b);
}

static int scaled(float value, int base) {
  return (int)(value * (float)base);
}

static void glowCircle(int x, int y, int r, uint16_t core, uint16_t mid, uint16_t outer, float pulse) {
  int bloom = max(2, (int)(r * (0.8f + pulse * 1.2f)));
  tft.fillCircle(x, y, r + bloom, outer);
  tft.fillCircle(x, y, r + max(1, bloom / 2), mid);
  tft.fillCircle(x, y, r, core);
  tft.fillCircle(x + max(1, r / 3), y - max(1, r / 3), max(1, r / 5), TFT_WHITE);
}

static void drawSegmentedProgress(float progress) {
  const int w = tft.width();
  const int h = tft.height();
  const int barW = max(120, (int)(w * 0.70f));
  const int barH = max(6, (int)(h * 0.035f));
  const int x0 = (w - barW) / 2;
  const int y0 = h - max(42, (int)(h * 0.16f));
  const int segmentGap = 4;
  const int segmentW = 7;
  const int count = max(8, barW / (segmentW + segmentGap));
  const int lit = min(count, max(0, (int)(progress * (float)count)));

  const uint16_t dim = c565(24, 26, 34);
  const uint16_t magenta = c565(235, 70, 255);
  const uint16_t blue = c565(65, 170, 255);

  tft.drawLine(x0 - 14, y0 + barH / 2, x0 - 4, y0 + barH / 2, magenta);
  tft.drawLine(x0 + barW + 4, y0 + barH / 2, x0 + barW + 14, y0 + barH / 2, blue);

  for (int i = 0; i < count; ++i) {
    int x = x0 + i * (segmentW + segmentGap);
    uint16_t color = dim;
    if (i < lit) {
      color = (i < count / 2) ? magenta : blue;
    }
    tft.fillRoundRect(x, y0, segmentW, barH, 2, color);
  }
}

static void drawBootFrame(float progress, float pulse) {
  tft.fillScreen(TFT_BLACK);

  const int w = tft.width();
  const int h = tft.height();
  const int base = min(w, h);
  const int cx = w / 2;
  const int cy = scaled(0.36f, h);

  const int headR = scaled(0.265f, base);
  const int earR = scaled(0.135f, base);
  const int eyeR = scaled(0.047f, base) + (int)(pulse * scaled(0.018f, base));
  const int eyeDX = scaled(0.135f, base);
  const int eyeDY = -scaled(0.035f, base);

  const uint16_t face = c565(7, 8, 12);
  const uint16_t edge = c565(28, 31, 40);
  const uint16_t nose = c565(52, 55, 62);
  const uint16_t noseEdge = c565(112, 116, 126);
  const uint16_t tooth = c565(190, 192, 205);
  const uint16_t purple = c565(230, 60, 255);
  const uint16_t purpleDim = c565(65, 12, 95);
  const uint16_t blue = c565(60, 165, 255);
  const uint16_t blueDim = c565(8, 45, 110);
  const uint16_t textGray = c565(116, 118, 130);

  // Ears and face silhouette.
  tft.fillCircle(cx - scaled(0.31f, base), cy - scaled(0.22f, base), earR, face);
  tft.fillCircle(cx + scaled(0.31f, base), cy - scaled(0.22f, base), earR, face);
  tft.drawCircle(cx - scaled(0.31f, base), cy - scaled(0.22f, base), earR, edge);
  tft.drawCircle(cx + scaled(0.31f, base), cy - scaled(0.22f, base), earR, edge);
  tft.fillCircle(cx, cy, headR, face);
  tft.drawCircle(cx, cy, headR, edge);

  // Angry brow slashes.
  tft.drawLine(cx - scaled(0.20f, base), cy - scaled(0.12f, base), cx - scaled(0.04f, base), cy - scaled(0.025f, base), edge);
  tft.drawLine(cx + scaled(0.20f, base), cy - scaled(0.12f, base), cx + scaled(0.04f, base), cy - scaled(0.025f, base), edge);
  tft.drawLine(cx - scaled(0.20f, base), cy - scaled(0.11f, base), cx - scaled(0.04f, base), cy - scaled(0.015f, base), edge);
  tft.drawLine(cx + scaled(0.20f, base), cy - scaled(0.11f, base), cx + scaled(0.04f, base), cy - scaled(0.015f, base), edge);

  // Pulsing eyes: left purple, right true blue.
  glowCircle(cx - eyeDX, cy + eyeDY, eyeR, c565(255, 226, 255), purple, purpleDim, pulse);
  glowCircle(cx + eyeDX, cy + eyeDY, eyeR, c565(232, 246, 255), blue, blueDim, pulse);

  // Nose.
  const int noseW = scaled(0.15f, base);
  const int noseH = scaled(0.21f, base);
  tft.fillRoundRect(cx - noseW / 2, cy + scaled(0.02f, base), noseW, noseH, max(6, noseW / 3), nose);
  tft.drawRoundRect(cx - noseW / 2, cy + scaled(0.02f, base), noseW, noseH, max(6, noseW / 3), noseEdge);

  // Fangs / mouth.
  const int mouthY = cy + scaled(0.28f, base);
  tft.fillTriangle(cx - scaled(0.08f, base), mouthY, cx - scaled(0.03f, base), mouthY - scaled(0.035f, base), cx - scaled(0.01f, base), mouthY + scaled(0.045f, base), tooth);
  tft.fillTriangle(cx + scaled(0.08f, base), mouthY, cx + scaled(0.03f, base), mouthY - scaled(0.035f, base), cx + scaled(0.01f, base), mouthY + scaled(0.045f, base), tooth);
  tft.drawLine(cx - scaled(0.05f, base), mouthY + scaled(0.055f, base), cx + scaled(0.05f, base), mouthY + scaled(0.055f, base), edge);

  // Title.
  const int titleY = h - max(72, scaled(0.26f, h));
  const int textSize = (base >= 280) ? 2 : 1;
  tft.setTextDatum(MC_DATUM);
  tft.setTextSize(textSize);
  tft.setTextColor(purple, TFT_BLACK);
  tft.drawString("KoalaByte", cx - scaled(0.18f, base), titleY);
  tft.setTextColor(blue, TFT_BLACK);
  tft.drawString("Blue", cx + scaled(0.24f, base), titleY);

  drawSegmentedProgress(progress);

  tft.setTextSize(1);
  tft.setTextColor(textGray, TFT_BLACK);
  tft.drawString("BOOTING...", cx, h - max(16, scaled(0.07f, h)));
}

void setupDisplay() {
  tft.init();
  tft.setRotation(DISPLAY_ROTATION);
  tft.fillScreen(TFT_BLACK);
}

void runBootAnimation() {
  const uint32_t totalMs = BOOT_ANIMATION_TOTAL_MS;
  const uint32_t frameMs = BOOT_ANIMATION_FRAME_MS;
  const uint32_t startMs = millis();

  while ((millis() - startMs) < totalMs) {
    const uint32_t elapsed = millis() - startMs;
    float progress = (float)elapsed / (float)totalMs;
    if (progress > 1.0f) progress = 1.0f;

    // Smooth pulse from dim to bright and back while the progress bar advances.
    const float pulse = 0.5f + 0.5f * sinf(((float)elapsed / 220.0f) * 2.0f * PI);
    drawBootFrame(progress, pulse);
    delay(frameMs);
  }

  drawBootFrame(1.0f, 0.55f);
  delay(140);
}

#else

void setupDisplay() {}
void runBootAnimation() {}

#endif
