#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <math.h>

#include "boot_animation.h"
#include "config.h"
#include "dualeye_display.h"

namespace {
constexpr int kSize = 200;
GFXcanvas16 leftBoot(kSize, kSize);
GFXcanvas16 rightBoot(kSize, kSize);

uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
  return (uint16_t)(((uint16_t)(r & 0xF8) << 8) |
                    ((uint16_t)(g & 0xFC) << 3) | (b >> 3));
}

void centerText(GFXcanvas16 &canvas, const char *text, int y, uint8_t size,
                uint16_t color) {
  canvas.setTextSize(size);
  canvas.setTextColor(color);
  canvas.setTextWrap(false);
  int16_t x1, y1;
  uint16_t w, h;
  canvas.getTextBounds(text, 0, y, &x1, &y1, &w, &h);
  canvas.setCursor((kSize - (int)w) / 2, y);
  canvas.print(text);
}

void drawBootEye(GFXcanvas16 &canvas, bool leftEye, float progress,
                 float pulse) {
  const uint16_t bg = rgb565(3, 6, 11);
  const uint16_t fur = rgb565(91, 102, 116);
  const uint16_t furHi = rgb565(177, 192, 205);
  const uint16_t purple = rgb565(165, 75, 255);
  const uint16_t green = rgb565(50, 255, 113);
  const uint16_t eyeColor = leftEye ? purple : green;

  canvas.fillScreen(bg);
  canvas.fillCircle(100, 100, 96, fur);
  canvas.drawCircle(100, 100, 96, furHi);
  canvas.drawCircle(100, 100, 89, rgb565(34, 43, 57));
  for (int i = 0; i < 30; ++i) {
    float a = i * 0.2094f;
    int x = 100 + (int)(cosf(a) * 91.0f);
    int y = 100 + (int)(sinf(a) * 91.0f);
    canvas.drawLine(x, y, x + (int)(cosf(a) * 7.0f),
                    y + (int)(sinf(a) * 7.0f), furHi);
  }

  int ry = 34 + (int)(pulse * 3.0f);
  canvas.fillEllipse(100, 88, 58, ry, rgb565(7, 12, 20));
  canvas.drawEllipse(100, 88, 66, ry + 8, eyeColor);
  canvas.fillEllipse(100, 88, 54, ry - 4, rgb565(194, 214, 224));
  canvas.fillCircle(100 + (leftEye ? 4 : -4), 88, 28, eyeColor);
  canvas.fillCircle(100 + (leftEye ? 4 : -4), 88, 13, rgb565(1, 4, 8));
  canvas.fillCircle(108 + (leftEye ? 4 : -4), 79, 4, 0xFFFF);

  for (int o = -2; o <= 2; ++o) {
    if (leftEye) canvas.drawLine(43, 48 + o, 120, 62 + o, rgb565(26, 34, 46));
    else canvas.drawLine(157, 48 + o, 80, 62 + o, rgb565(26, 34, 46));
  }

  canvas.drawRoundRect(20, 156, 160, 12, 5, rgb565(45, 61, 72));
  int filled = (int)(156.0f * progress);
  if (filled > 0) canvas.fillRoundRect(22, 158, filled, 8, 4, eyeColor);
  centerText(canvas, leftEye ? "KILLER" : "KOALA", 178, 1, eyeColor);
}
}

void setupDisplay() {
  dualEyeDisplayBegin();
  dualEyeClear(rgb565(3, 6, 11));
}

void runBootAnimation() {
#if ENABLE_DISPLAY_BOOT_ANIMATION
  const uint32_t start = millis();
  while (millis() - start < BOOT_ANIMATION_TOTAL_MS) {
    const uint32_t elapsed = millis() - start;
    float progress = (float)elapsed / (float)BOOT_ANIMATION_TOTAL_MS;
    if (progress > 1.0f) progress = 1.0f;
    float pulse = 0.5f + 0.5f * sinf((float)elapsed * 0.018f);
    drawBootEye(leftBoot, true, progress, pulse);
    drawBootEye(rightBoot, false, progress, 1.0f - pulse);
    dualEyePushCanvas(1, leftBoot, 20, 20);
    dualEyePushCanvas(2, rightBoot, 20, 20);
    delay(BOOT_ANIMATION_FRAME_MS);
  }
#endif
}
