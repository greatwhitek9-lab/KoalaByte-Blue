#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <math.h>
#include <string.h>

#include "config.h"
#include "dualeye_display.h"
#include "koalagotchi_mode_screens.h"

namespace {
constexpr int kCanvas = KOALA_EYE_CANVAS_SIZE;
constexpr int kCenter = kCanvas / 2;
constexpr uint32_t kFrameMs = 1000U / KOALA_EYE_RENDER_FPS;

GFXcanvas16 leftCanvas(kCanvas, kCanvas);
GFXcanvas16 rightCanvas(kCanvas, kCanvas);

struct Rgb { uint8_t r, g, b; };
struct EyeRuntime {
  char look[18];
  char animation[18];
  char leftHex[10];
  char rightHex[10];
  Rgb left;
  Rgb right;
  int brightness;
  float gazeX;
  float gazeY;
  float targetX;
  float targetY;
  uint32_t nextGazeMs;
  uint32_t nextBlinkMs;
  uint32_t blinkStartMs;
  uint32_t lastFrameMs;
};

EyeRuntime eyes = {
  "cyber", "idle", "#A54BFF", "#32FF71",
  {165, 75, 255}, {50, 255, 113}, 100,
  0, 0, 0, 0, 0, 0, 0, 0
};

char lastMode[24] = "eucalyptus";
char lastMood[96] = "calm";
int lastContentment = 75;
int lastXp = 88;
bool hasScene = false;
bool primaryTextMode = false;

uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
  return (uint16_t)(((uint16_t)(r & 0xF8) << 8) |
                    ((uint16_t)(g & 0xFC) << 3) | (b >> 3));
}

int clampInt(int value, int lo, int hi) {
  return value < lo ? lo : value > hi ? hi : value;
}

float clampFloat(float value, float lo, float hi) {
  return value < lo ? lo : value > hi ? hi : value;
}

bool eqi(const char *a, const char *b) {
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

bool containsI(const char *text, const char *needle) {
  if (!text || !needle) return false;
  String a(text);
  String b(needle);
  a.toLowerCase();
  b.toLowerCase();
  return a.indexOf(b) >= 0;
}

int hexNibble(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

Rgb parseHex(const char *value, Rgb fallback, char *stored, size_t storedLen) {
  if (!value) return fallback;
  const char *p = value[0] == '#' ? value + 1 : value;
  if (strlen(p) != 6) return fallback;
  int n[6];
  for (int i = 0; i < 6; ++i) {
    n[i] = hexNibble(p[i]);
    if (n[i] < 0) return fallback;
  }
  Rgb out = {(uint8_t)((n[0] << 4) | n[1]),
             (uint8_t)((n[2] << 4) | n[3]),
             (uint8_t)((n[4] << 4) | n[5])};
  snprintf(stored, storedLen, "#%02X%02X%02X", out.r, out.g, out.b);
  return out;
}

Rgb scale(Rgb c, float amount) {
  amount = clampFloat(amount, 0.0f, 1.5f);
  return {(uint8_t)clampInt((int)(c.r * amount), 0, 255),
          (uint8_t)clampInt((int)(c.g * amount), 0, 255),
          (uint8_t)clampInt((int)(c.b * amount), 0, 255)};
}

float smoothstep(float t) {
  t = clampFloat(t, 0.0f, 1.0f);
  return t * t * (3.0f - 2.0f * t);
}

float blinkAmount(uint32_t now) {
  if (eyes.blinkStartMs == 0) return 0.0f;
  const uint32_t elapsed = now - eyes.blinkStartMs;
  if (elapsed >= 230) {
    eyes.blinkStartMs = 0;
    return 0.0f;
  }
  if (elapsed < 75) return smoothstep((float)elapsed / 75.0f);
  if (elapsed < 115) return 1.0f;
  return 1.0f - smoothstep((float)(elapsed - 115) / 115.0f);
}

void updateMotion(uint32_t now) {
  if (eyes.nextGazeMs == 0 || now >= eyes.nextGazeMs) {
    eyes.targetX = random(-100, 101) / 100.0f;
    eyes.targetY = random(-65, 66) / 100.0f;
    eyes.nextGazeMs = now + random(650, 1900);
  }
  eyes.gazeX += (eyes.targetX - eyes.gazeX) * 0.13f;
  eyes.gazeY += (eyes.targetY - eyes.gazeY) * 0.13f;

  if (eyes.nextBlinkMs == 0) eyes.nextBlinkMs = now + random(1700, 4300);
  if (now >= eyes.nextBlinkMs && eyes.blinkStartMs == 0) {
    eyes.blinkStartMs = now;
    eyes.nextBlinkMs = now + random(1800, 4700);
  }
}

void drawCentered(GFXcanvas16 &canvas, const char *text, int16_t y,
                  uint8_t size, uint16_t color) {
  if (!text || !text[0]) return;
  canvas.setTextSize(size);
  canvas.setTextColor(color);
  canvas.setTextWrap(false);
  int16_t x1, y1;
  uint16_t w, h;
  canvas.getTextBounds(text, 0, y, &x1, &y1, &w, &h);
  canvas.setCursor((kCanvas - (int)w) / 2, y);
  canvas.print(text);
}

void drawFur(GFXcanvas16 &canvas, uint16_t base, uint16_t edge, float phase) {
  canvas.fillScreen(rgb565(3, 6, 11));
  canvas.fillCircle(kCenter, kCenter + 8, 96, base);
  canvas.drawCircle(kCenter, kCenter + 8, 96, edge);
  for (int i = 0; i < 34; ++i) {
    float a = (float)i * 0.1848f + phase * 0.025f;
    int x = kCenter + (int)(cosf(a) * (91 + (i % 4)));
    int y = kCenter + 8 + (int)(sinf(a) * (91 + ((i + 1) % 4)));
    int dx = (int)(cosf(a) * 8);
    int dy = (int)(sinf(a) * 8);
    canvas.drawLine(x, y, x + dx, y + dy, edge);
  }
  canvas.drawCircle(kCenter, kCenter + 8, 82, rgb565(52, 62, 75));
  canvas.drawCircle(kCenter, kCenter + 8, 80, rgb565(18, 25, 34));
}

void drawBrow(GFXcanvas16 &canvas, bool leftEye, float mood, float lift,
              uint16_t color) {
  const int innerX = leftEye ? 118 : 82;
  const int outerX = leftEye ? 46 : 154;
  const int baseY = 57 - (int)(lift * 12.0f);
  const int innerY = baseY + (int)(mood * 13.0f);
  const int outerY = baseY - (int)(mood * 5.0f);
  for (int o = -2; o <= 2; ++o) {
    canvas.drawLine(outerX, outerY + o, innerX, innerY + o, color);
  }
  canvas.drawLine(outerX + 5, outerY - 5, innerX - 5, innerY - 5,
                  rgb565(110, 123, 138));
}

void drawEye(GFXcanvas16 &canvas, bool leftEye, Rgb baseColor, uint32_t now,
             bool errorState, bool menuState) {
  float phase = (float)now * 0.001f;
  uint16_t fur = rgb565(94, 104, 117);
  uint16_t furEdge = rgb565(176, 191, 203);
  drawFur(canvas, fur, furEdge, phase);

  const float breathing = 0.5f + 0.5f * sinf(phase * 1.7f);
  const float pulse = 0.5f + 0.5f * sinf(phase * 3.4f);
  float blink = blinkAmount(now);
  float openness = 1.0f - blink;
  float browMood = 0.0f;
  float browLift = 0.05f;

  if (eqi(eyes.animation, "sleepy") || containsI(lastMood, "sleep")) openness *= 0.48f;
  if (eqi(eyes.animation, "speaking") || containsI(lastMood, "speaking")) {
    openness *= 0.80f + 0.20f * sinf(phase * 9.0f);
    browLift = 0.25f + 0.14f * sinf(phase * 4.0f);
  }
  if (eqi(eyes.animation, "scan") || containsI(lastMood, "thinking")) {
    browMood = 0.28f;
    openness *= 0.82f;
  }
  if (eqi(eyes.look, "angry") || errorState || containsI(lastMood, "angry")) {
    browMood = 0.92f;
    openness *= 0.72f;
  }
  if (containsI(lastMood, "happy") || containsI(lastMood, "success")) {
    browMood = -0.32f;
    browLift = 0.38f;
  }

  Rgb iris = scale(baseColor, (eyes.brightness / 100.0f) * (0.86f + pulse * 0.22f));
  if (errorState) {
    const bool phaseA = ((now / 190U) & 1U) == 0U;
    const bool purple = leftEye ? phaseA : !phaseA;
    iris = purple ? Rgb{165, 75, 255} : Rgb{50, 255, 113};
  }

  uint16_t irisColor = rgb565(iris.r, iris.g, iris.b);
  Rgb glowRgb = scale(iris, 1.25f);
  uint16_t glow = rgb565(glowRgb.r, glowRgb.g, glowRgb.b);
  uint16_t socket = rgb565(7, 12, 20);
  uint16_t sclera = rgb565(190, 209, 219);

  int eyeRx = menuState ? 42 : 58;
  int eyeRy = max(3, (int)((menuState ? 29 : 39) * openness));
  int eyeCy = menuState ? 72 : 105;

  canvas.fillEllipse(kCenter, eyeCy, eyeRx + 10, eyeRy + 10, socket);
  canvas.drawEllipse(kCenter, eyeCy, eyeRx + 12, eyeRy + 12, glow);
  canvas.drawEllipse(kCenter, eyeCy, eyeRx + 7, eyeRy + 7, irisColor);
  canvas.fillEllipse(kCenter, eyeCy, eyeRx, eyeRy, sclera);

  int gazeX = (int)(eyes.gazeX * 17.0f) + (leftEye ? 2 : -2);
  int gazeY = (int)(eyes.gazeY * 10.0f);
  if (eqi(eyes.animation, "scan")) gazeX = (int)(sinf(phase * 2.3f) * 19.0f);
  if (errorState) {
    gazeX += (int)(sinf(phase * 14.0f) * 3.0f);
    gazeY += (int)(cosf(phase * 11.0f) * 2.0f);
  }

  int irisR = menuState ? 19 : 27;
  canvas.fillCircle(kCenter + gazeX, eyeCy + gazeY, irisR + 6, glow);
  canvas.fillCircle(kCenter + gazeX, eyeCy + gazeY, irisR, irisColor);
  canvas.fillCircle(kCenter + gazeX, eyeCy + gazeY, irisR / 2, rgb565(1, 4, 8));
  canvas.fillCircle(kCenter + gazeX + 6, eyeCy + gazeY - 7, 4, 0xFFFF);
  canvas.drawCircle(kCenter + gazeX, eyeCy + gazeY, irisR + 10,
                    rgb565(40, 49, 63));

  drawBrow(canvas, leftEye, browMood, browLift, rgb565(30, 37, 48));

  for (int i = 0; i < 4; ++i) {
    int y = eyeCy - 45 + i * 30;
    int x1 = leftEye ? 26 : 174;
    int x2 = leftEye ? 44 : 156;
    canvas.drawLine(x1, y, x2, y + (leftEye ? 5 : -5), irisColor);
  }

  if (errorState) {
    const float siren = 0.5f + 0.5f * sinf(phase * 16.0f);
    uint16_t warning = siren > 0.5f ? glow : irisColor;
    canvas.drawCircle(kCenter, kCenter + 8, 94, warning);
    canvas.drawCircle(kCenter, kCenter + 8, 90, warning);
  }
}

void drawPrimaryMenu(uint32_t now) {
  bool errorState = containsI(lastMood, "error") || containsI(lastMood, "failed");
  drawEye(rightCanvas, false, eyes.right, now, errorState, true);
  uint16_t accent = errorState ? rgb565(255, 95, 220) : rgb565(50, 255, 113);
  rightCanvas.fillRoundRect(10, 117, kCanvas - 20, 67, 12, rgb565(5, 12, 20));
  rightCanvas.drawRoundRect(10, 117, kCanvas - 20, 67, 12, accent);
  drawCentered(rightCanvas, errorState ? "ERROR" : "MENU", 126, 2, accent);

  String line(lastMood);
  if (line.length() > 26) line = line.substring(0, 26);
  drawCentered(rightCanvas, line.c_str(), 154, 1, rgb565(220, 232, 238));

  drawEye(leftCanvas, true, eyes.left, now, errorState, false);
}

void renderFrame(uint32_t now) {
  if (!dualEyeDisplayReady()) return;
  updateMotion(now);
  const bool errorState = containsI(lastMood, "error") || containsI(lastMood, "failed") ||
                          eqi(eyes.animation, "error") || eqi(eyes.animation, "glitch");
  const bool menuState = eqi(lastMode, "menu") || eqi(lastMode, "text_input") ||
                         eqi(lastMode, "prompt") || eqi(lastMode, "warning");

  if (menuState && KOALA_CRITICAL_UI_PRIMARY_ONLY) {
    drawPrimaryMenu(now);
  } else {
    drawEye(leftCanvas, true, eyes.left, now, errorState, false);
    drawEye(rightCanvas, false, eyes.right, now, errorState, false);
  }

  dualEyePushCanvas(1, leftCanvas, (DISPLAY_WIDTH - kCanvas) / 2,
                    (DISPLAY_HEIGHT - kCanvas) / 2);
  dualEyePushCanvas(2, rightCanvas, (DISPLAY_WIDTH - kCanvas) / 2,
                    (DISPLAY_HEIGHT - kCanvas) / 2);
}
}  // namespace

bool setKoalagotchiEyeStyle(const char *look, const char *leftColor,
                            const char *rightColor, const char *animation,
                            int brightnessPercent) {
  snprintf(eyes.look, sizeof(eyes.look), "%s", look && look[0] ? look : "cyber");
  snprintf(eyes.animation, sizeof(eyes.animation), "%s",
           animation && animation[0] ? animation : "idle");
  eyes.left = parseHex(leftColor, eyes.left, eyes.leftHex, sizeof(eyes.leftHex));
  eyes.right = parseHex(rightColor, eyes.right, eyes.rightHex, sizeof(eyes.rightHex));
  eyes.brightness = clampInt(brightnessPercent <= 0 ? 100 : brightnessPercent, 1, 100);
  return true;
}

void resetKoalagotchiEyeStyle() {
  setKoalagotchiEyeStyle("cyber", "#A54BFF", "#32FF71", "idle", 100);
}

void drawKoalagotchiModeScreen(const char *mode, const char *mood,
                               int contentment, int xpPercent) {
  if (!dualEyeDisplayReady()) dualEyeDisplayBegin();
  snprintf(lastMode, sizeof(lastMode), "%s", mode && mode[0] ? mode : "eucalyptus");
  snprintf(lastMood, sizeof(lastMood), "%s", mood && mood[0] ? mood : "calm");
  lastContentment = clampInt(contentment, 0, 100);
  lastXp = clampInt(xpPercent, 0, 100);
  hasScene = true;
  primaryTextMode = eqi(lastMode, "menu") || eqi(lastMode, "text_input") ||
                    eqi(lastMode, "prompt") || eqi(lastMode, "warning");
  renderFrame(millis());
}

void tickKoalagotchiEyes() {
  if (!hasScene || !dualEyeDisplayReady()) return;
  const uint32_t now = millis();
  if (now - eyes.lastFrameMs < kFrameMs) return;
  eyes.lastFrameMs = now;
  renderFrame(now);
}

const char *getKoalagotchiEyeLook() { return eyes.look; }
const char *getKoalagotchiEyeAnimation() { return eyes.animation; }
const char *getKoalagotchiLeftEyeHex() { return eyes.leftHex; }
const char *getKoalagotchiRightEyeHex() { return eyes.rightHex; }
int getKoalagotchiEyeBrightness() { return eyes.brightness; }
