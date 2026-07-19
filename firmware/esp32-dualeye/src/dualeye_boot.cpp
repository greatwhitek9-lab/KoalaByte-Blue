#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <math.h>

#include "boot_animation.h"
#include "config.h"
#include "dualeye_display.h"

namespace {
constexpr int kSize = KOALA_EYE_CANVAS_SIZE;
constexpr int kCenter = kSize / 2;

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

void drawBootKoala(GFXcanvas16 &canvas, bool leftEye, float progress,
                   float pulse) {
  const uint16_t bg = rgb565(2, 5, 9);
  const uint16_t furShadow = rgb565(54, 61, 68);
  const uint16_t furMid = rgb565(105, 113, 119);
  const uint16_t furLight = rgb565(177, 184, 186);
  const uint16_t purple = rgb565(165, 75, 255);
  const uint16_t green = rgb565(50, 255, 113);
  const uint16_t accent = leftEye ? purple : green;
  const int outerX = leftEye ? 10 : 190;
  const int innerX = leftEye ? 190 : 10;

  canvas.fillScreen(bg);
  canvas.fillCircle(outerX, 78, 53, furShadow);
  canvas.fillCircle(outerX, 78, 39, rgb565(42, 43, 46));
  canvas.fillCircle(kCenter, 105, 99, furShadow);
  canvas.fillEllipse(kCenter, 101, 91, 94, furMid);
  canvas.fillEllipse(kCenter, 68, 81, 49, furLight);
  canvas.fillCircle(leftEye ? 52 : 148, 145, 41, furLight);

  // Uneven forehead and cheek fur. No perimeter tick/ruler graphics.
  canvas.fillTriangle(34, 42, 53, 16, 66, 44, furLight);
  canvas.fillTriangle(69, 31, 91, 8, 104, 37, furMid);
  canvas.fillTriangle(109, 34, 133, 12, 145, 43, furLight);
  canvas.fillTriangle(149, 44, 169, 25, 178, 54, furMid);
  canvas.fillTriangle(22, 151, 7, 171, 42, 166, furLight);
  canvas.fillTriangle(160, 166, 191, 170, 176, 148, furMid);

  canvas.fillEllipse(innerX, 128, 31, 62, rgb565(13, 15, 18));
  canvas.fillEllipse(innerX, 147, 25, 39, rgb565(17, 18, 20));
  canvas.fillEllipse(innerX + (leftEye ? -4 : 4), 132, 11, 18,
                     rgb565(61, 63, 66));

  const int eyeCy = 96;
  const int eyeRy = 35 + (int)(pulse * 2.0f);
  canvas.fillEllipse(kCenter, eyeCy, 68, eyeRy + 11, rgb565(18, 19, 21));
  canvas.fillEllipse(kCenter, eyeCy, 61, eyeRy + 6, rgb565(57, 61, 62));
  canvas.fillEllipse(kCenter, eyeCy, 55, eyeRy, rgb565(198, 201, 194));
  canvas.fillCircle(kCenter + (leftEye ? 3 : -3), eyeCy, 31, accent);
  canvas.fillCircle(kCenter + (leftEye ? 3 : -3), eyeCy, 25,
                    leftEye ? rgb565(116, 48, 189) : rgb565(25, 180, 77));
  canvas.fillEllipse(kCenter + (leftEye ? 3 : -3), eyeCy, 6, 19,
                     rgb565(1, 3, 4));
  canvas.fillCircle(kCenter + (leftEye ? 9 : -9), eyeCy - 9, 4,
                    rgb565(245, 248, 241));

  for (int o = -3; o <= 3; ++o) {
    if (leftEye) {
      canvas.drawLine(43, 61 + o, 92, 50 + o, rgb565(33, 36, 39));
      canvas.drawLine(92, 50 + o, 136, 59 + o, rgb565(33, 36, 39));
    } else {
      canvas.drawLine(157, 61 + o, 108, 50 + o, rgb565(33, 36, 39));
      canvas.drawLine(108, 50 + o, 64, 59 + o, rgb565(33, 36, 39));
    }
  }

  canvas.fillRoundRect(22, 168, 156, 10, 5, rgb565(35, 43, 47));
  const int filled = (int)(152.0f * progress);
  if (filled > 0) canvas.fillRoundRect(24, 170, filled, 6, 3, accent);
  centerText(canvas, "KILLERKOALA", 184, 1, accent);
}
}  // namespace

void setupDisplay() {
  Serial.println("{\"type\":\"boot_stage\",\"stage\":\"display_setup_start\"}");
  if (!dualEyeDisplayBegin()) {
    Serial.println("{\"type\":\"boot_fault\",\"stage\":\"display_setup\"}");
    return;
  }
  dualEyeClear(rgb565(2, 5, 9));
  Serial.println("{\"type\":\"boot_stage\",\"stage\":\"display_setup_ready\"}");
}

void runBootAnimation() {
#if ENABLE_DISPLAY_BOOT_ANIMATION
  if (!dualEyeDisplayReady() || !dualEyeCanvasReady()) return;
  Serial.println("{\"type\":\"boot_stage\",\"stage\":\"animation_start\"}");
  const uint32_t start = millis();
  while (millis() - start < BOOT_ANIMATION_TOTAL_MS) {
    const uint32_t elapsed = millis() - start;
    float progress = (float)elapsed / (float)BOOT_ANIMATION_TOTAL_MS;
    if (progress > 1.0f) progress = 1.0f;
    const float pulse = 0.5f + 0.5f * sinf((float)elapsed * 0.016f);
    GFXcanvas16 &canvas = dualEyeCanvas();

    drawBootKoala(canvas, false, progress, pulse);
    dualEyePushCanvas(2, canvas, (DISPLAY_WIDTH - kSize) / 2,
                      (DISPLAY_HEIGHT - kSize) / 2);
#if KOALA_LCD1_ENABLED
    drawBootKoala(canvas, true, progress, 1.0f - pulse);
    dualEyePushCanvas(1, canvas, (DISPLAY_WIDTH - kSize) / 2,
                      (DISPLAY_HEIGHT - kSize) / 2);
#endif
    delay(BOOT_ANIMATION_FRAME_MS);
    yield();
  }
  Serial.println("{\"type\":\"boot_stage\",\"stage\":\"animation_complete\"}");
#endif
}
