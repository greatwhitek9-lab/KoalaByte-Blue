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

struct Rgb {
  uint8_t r;
  uint8_t g;
  uint8_t b;
};

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
  uint32_t lastMotionMs;
};

EyeRuntime eyes = {
    "cyber", "idle", "#A54BFF", "#32FF71",
    {165, 75, 255}, {50, 255, 113}, 100,
    0.0f, 0.0f, 0.0f, 0.0f, 0, 0, 0, 0, 0};

char lastMode[24] = "eucalyptus";
char lastMood[96] = "calm";
int lastContentment = 75;
int lastXp = 88;
bool hasScene = false;

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

Rgb mixRgb(Rgb a, Rgb b, float t) {
  t = clampFloat(t, 0.0f, 1.0f);
  return {(uint8_t)(a.r + (b.r - a.r) * t),
          (uint8_t)(a.g + (b.g - a.g) * t),
          (uint8_t)(a.b + (b.b - a.b) * t)};
}

float smoothstep(float t) {
  t = clampFloat(t, 0.0f, 1.0f);
  return t * t * (3.0f - 2.0f * t);
}

float blinkAmount(uint32_t now) {
  if (eyes.blinkStartMs == 0) return 0.0f;
  const uint32_t elapsed = now - eyes.blinkStartMs;
  if (elapsed >= 235) {
    eyes.blinkStartMs = 0;
    return 0.0f;
  }
  if (elapsed < 72) return smoothstep((float)elapsed / 72.0f);
  if (elapsed < 112) return 1.0f;
  return 1.0f - smoothstep((float)(elapsed - 112) / 123.0f);
}

void updateMotion(uint32_t now) {
  if (eyes.nextGazeMs == 0 || now >= eyes.nextGazeMs) {
    eyes.targetX = random(-100, 101) / 100.0f;
    eyes.targetY = random(-55, 56) / 100.0f;
    eyes.nextGazeMs = now + random(700, 2100);
  }

  float dt = eyes.lastMotionMs == 0 ? 0.033f : (now - eyes.lastMotionMs) / 1000.0f;
  eyes.lastMotionMs = now;
  dt = clampFloat(dt, 0.0f, 0.08f);
  const float follow = 1.0f - expf(-8.0f * dt);
  eyes.gazeX += (eyes.targetX - eyes.gazeX) * follow;
  eyes.gazeY += (eyes.targetY - eyes.gazeY) * follow;

  if (eyes.nextBlinkMs == 0) eyes.nextBlinkMs = now + random(1800, 4400);
  if (now >= eyes.nextBlinkMs && eyes.blinkStartMs == 0) {
    eyes.blinkStartMs = now;
    eyes.nextBlinkMs = now + random(1900, 5000);
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

void drawFurTufts(GFXcanvas16 &canvas, uint16_t light, uint16_t mid,
                  bool leftEye) {
  // Irregular clumps only. There is intentionally no radial ring or repeated
  // perimeter marking, which previously made the display resemble a clock.
  canvas.fillTriangle(22, 48, 35, 20, 48, 49, mid);
  canvas.fillTriangle(44, 32, 62, 8, 72, 39, light);
  canvas.fillTriangle(73, 27, 94, 5, 105, 34, mid);
  canvas.fillTriangle(104, 30, 127, 9, 137, 39, light);
  canvas.fillTriangle(137, 35, 157, 17, 169, 49, mid);
  canvas.fillTriangle(23, 150, 8, 169, 40, 166, light);
  canvas.fillTriangle(160, 166, 192, 170, 176, 149, mid);

  const int outerX = leftEye ? 26 : 174;
  const int outerDir = leftEye ? -1 : 1;
  canvas.fillTriangle(outerX, 68, outerX + outerDir * 22, 57,
                      outerX + outerDir * 8, 88, light);
  canvas.fillTriangle(outerX, 116, outerX + outerDir * 25, 126,
                      outerX + outerDir * 7, 99, mid);
}

void drawKoalaFaceBase(GFXcanvas16 &canvas, bool leftEye, Rgb accent,
                       bool errorState, float sirenMix, float breathing) {
  const uint16_t bg = rgb565(2, 5, 9);
  const uint16_t furShadow = rgb565(54, 61, 68);
  const uint16_t furMid = rgb565(103, 112, 119);
  const uint16_t furLight = rgb565(172, 181, 185);
  const uint16_t furWarm = rgb565(126, 128, 124);
  const uint16_t socketShadow = rgb565(13, 15, 18);
  const uint16_t nose = rgb565(17, 18, 20);
  const uint16_t noseHi = rgb565(60, 62, 65);
  const int faceY = 105 + (int)(breathing * 2.0f);
  const int outerX = leftEye ? 10 : 190;
  const int innerX = leftEye ? 190 : 10;

  canvas.fillScreen(bg);

  if (errorState) {
    Rgb wash = scale(accent, 0.32f + 0.25f * sirenMix);
    canvas.fillCircle(kCenter, kCenter, 99, rgb565(wash.r, wash.g, wash.b));
  }

  // Outer ear and dark inner ear establish a recognizable koala silhouette.
  canvas.fillCircle(outerX, 82, 54, furShadow);
  canvas.fillCircle(outerX, 82, 41, rgb565(39, 42, 45));
  canvas.fillCircle(outerX + (leftEye ? 5 : -5), 82, 29, rgb565(72, 67, 68));

  // Layered face, brow and cheek masses imitate the silver-grey Heltec koala.
  canvas.fillEllipse(kCenter, faceY, 98, 101, furShadow);
  canvas.fillEllipse(kCenter, faceY - 2, 91, 95, furMid);
  canvas.fillEllipse(kCenter, faceY - 28, 82, 55, furLight);
  canvas.fillEllipse(kCenter, faceY + 45, 84, 48, furWarm);
  canvas.fillCircle(leftEye ? 54 : 146, 145, 43, furLight);
  canvas.fillCircle(leftEye ? 49 : 151, 151, 34, furMid);

  drawFurTufts(canvas, furLight, furMid, leftEye);

  // Each round display shows one half of the central koala nose. With two
  // panels enabled these inward shapes meet visually at the face centre.
  canvas.fillEllipse(innerX, 126, 31, 62, socketShadow);
  canvas.fillEllipse(innerX, 145, 25, 39, nose);
  canvas.fillEllipse(innerX + (leftEye ? -4 : 4), 130, 12, 20, noseHi);

  // Small temple implant; intentionally sparse and non-circular.
  const int cyberX = leftEye ? 42 : 158;
  const int dir = leftEye ? -1 : 1;
  uint16_t cyber = rgb565(accent.r, accent.g, accent.b);
  canvas.drawLine(cyberX, 73, cyberX + dir * 12, 81, cyber);
  canvas.drawLine(cyberX + dir * 12, 81, cyberX + dir * 8, 97, cyber);
  canvas.fillCircle(cyberX + dir * 8, 101, 2, cyber);
}

void drawBrow(GFXcanvas16 &canvas, bool leftEye, float mood, float lift) {
  const int innerX = leftEye ? 135 : 65;
  const int outerX = leftEye ? 43 : 157;
  const int midX = (innerX + outerX) / 2;
  const int outerY = 62 - (int)(lift * 10.0f) - (int)(mood * 3.0f);
  const int midY = 53 - (int)(lift * 11.0f);
  const int innerY = 59 - (int)(lift * 8.0f) + (int)(mood * 13.0f);
  const uint16_t dark = rgb565(33, 36, 39);
  const uint16_t silver = rgb565(136, 143, 146);

  for (int o = -3; o <= 3; ++o) {
    canvas.drawLine(outerX, outerY + o, midX, midY + o, dark);
    canvas.drawLine(midX, midY + o, innerX, innerY + o, dark);
  }
  canvas.drawLine(outerX + (leftEye ? 4 : -4), outerY - 5,
                  midX, midY - 6, silver);
  canvas.drawLine(midX, midY - 6,
                  innerX + (leftEye ? -4 : 4), innerY - 5, silver);
}

void drawAnimalEye(GFXcanvas16 &canvas, bool leftEye, Rgb baseColor,
                   uint32_t now, bool errorState, bool menuState) {
  const float phase = now * 0.001f;
  const float breathing = 0.5f + 0.5f * sinf(phase * 1.55f);
  const float pulse = 0.5f + 0.5f * sinf(phase * 3.0f);
  const float sirenWave = 0.5f + 0.5f * sinf(phase * 8.3f);
  const float sirenMix = leftEye ? sirenWave : 1.0f - sirenWave;
  const Rgb purple = {165, 75, 255};
  const Rgb green = {50, 255, 113};

  Rgb iris = scale(baseColor,
                   (eyes.brightness / 100.0f) * (0.86f + pulse * 0.20f));
  if (errorState) iris = mixRgb(purple, green, sirenMix);

  drawKoalaFaceBase(canvas, leftEye, iris, errorState, sirenMix, breathing);

  float openness = 1.0f - blinkAmount(now);
  float browMood = 0.0f;
  float browLift = 0.04f;

  if (eqi(eyes.animation, "sleepy") || containsI(lastMood, "sleep")) {
    openness *= 0.48f;
    browLift = -0.08f;
  }
  if (eqi(eyes.animation, "speaking") || eqi(eyes.animation, "blink") ||
      containsI(lastMood, "speaking")) {
    openness *= 0.80f + 0.20f * sinf(phase * 8.6f);
    browLift = 0.22f + 0.13f * sinf(phase * 3.8f);
  }
  if (eqi(eyes.animation, "scan") || containsI(lastMood, "thinking")) {
    browMood = 0.24f;
    openness *= 0.84f;
  }
  if (eqi(eyes.look, "angry") || errorState || containsI(lastMood, "angry")) {
    browMood = 0.88f;
    openness *= errorState ? 0.68f + 0.20f * sirenWave : 0.72f;
  }
  if (containsI(lastMood, "happy") || containsI(lastMood, "success")) {
    browMood = -0.30f;
    browLift = 0.36f;
  }
  if (lastContentment < 35) {
    openness *= 0.78f;
    browMood += 0.22f;
  }

  const int eyeCy = menuState ? 76 : 104;
  const int eyeRx = menuState ? 43 : 57;
  const int openRy = menuState ? 27 : 37;
  const int eyeRy = clampInt((int)(openRy * openness), 2, openRy);
  const uint16_t socket = rgb565(18, 19, 21);
  const uint16_t lid = rgb565(57, 61, 62);
  const uint16_t sclera = rgb565(198, 201, 194);
  const uint16_t irisColor = rgb565(iris.r, iris.g, iris.b);
  const Rgb glowRgb = scale(iris, 1.25f);
  const uint16_t glow = rgb565(glowRgb.r, glowRgb.g, glowRgb.b);

  // Deep, furry socket rather than a circular instrument bezel.
  canvas.fillEllipse(kCenter, eyeCy, eyeRx + 12, eyeRy + 12, socket);
  canvas.fillEllipse(kCenter, eyeCy, eyeRx + 7, eyeRy + 7, lid);
  canvas.fillEllipse(kCenter, eyeCy, eyeRx, eyeRy, sclera);

  int gazeX = (int)(eyes.gazeX * 17.0f) + (leftEye ? 2 : -2);
  int gazeY = (int)(eyes.gazeY * 9.0f);
  if (eqi(eyes.animation, "scan")) gazeX = (int)(sinf(phase * 2.2f) * 18.0f);
  if (errorState) {
    gazeX += (int)(sinf(phase * 13.0f) * 3.0f);
    gazeY += (int)(cosf(phase * 10.0f) * 2.0f);
  }

  const int irisR = menuState ? 18 : 26;
  canvas.fillCircle(kCenter + gazeX, eyeCy + gazeY, irisR + 6, glow);
  canvas.fillCircle(kCenter + gazeX, eyeCy + gazeY, irisR + 2, irisColor);
  canvas.drawCircle(kCenter + gazeX, eyeCy + gazeY, irisR - 3,
                    rgb565(scale(iris, 0.65f).r,
                           scale(iris, 0.65f).g,
                           scale(iris, 0.65f).b));

  // Koala-like vertical animal pupil with moist asymmetric catchlights.
  canvas.fillEllipse(kCenter + gazeX, eyeCy + gazeY,
                     clampInt(irisR / 4, 4, 7),
                     clampInt((int)(irisR * 0.70f), 10, 19),
                     rgb565(1, 3, 4));
  canvas.fillCircle(kCenter + gazeX + (leftEye ? 6 : -6),
                    eyeCy + gazeY - 8, 4, rgb565(245, 248, 241));
  canvas.fillCircle(kCenter + gazeX + (leftEye ? -4 : 4),
                    eyeCy + gazeY + 6, 2, rgb565(183, 207, 202));

  // Soft eyelid contours make blinking read as skin/fur movement.
  const int lx = kCenter - eyeRx;
  const int rx = kCenter + eyeRx;
  canvas.drawLine(lx, eyeCy, kCenter - eyeRx / 2, eyeCy - eyeRy, socket);
  canvas.drawLine(kCenter - eyeRx / 2, eyeCy - eyeRy,
                  kCenter + eyeRx / 2, eyeCy - eyeRy - 2, socket);
  canvas.drawLine(kCenter + eyeRx / 2, eyeCy - eyeRy - 2, rx, eyeCy, socket);
  canvas.drawLine(lx + 4, eyeCy + 2, kCenter, eyeCy + eyeRy + 2,
                  rgb565(92, 98, 98));
  canvas.drawLine(kCenter, eyeCy + eyeRy + 2, rx - 4, eyeCy + 2,
                  rgb565(92, 98, 98));

  drawBrow(canvas, leftEye, browMood, browLift);

  if (errorState) {
    // Two restrained side washes provide the siren effect without drawing a
    // circular alarm ring or obscuring the koala eye.
    const uint16_t warning = rgb565(iris.r, iris.g, iris.b);
    const int sideX = leftEye ? 22 : 178;
    canvas.fillRoundRect(sideX - 6, 112, 12, 45, 5, warning);
    canvas.drawLine(sideX, 104, sideX, 94, warning);
  }
}

void pushPanel(uint8_t panelNumber, bool leftEye, uint32_t now,
               bool errorState, bool menuState) {
  if (!dualEyePanelReady(panelNumber)) return;
  GFXcanvas16 &canvas = dualEyeCanvas();
  const Rgb color = leftEye ? eyes.left : eyes.right;
  drawAnimalEye(canvas, leftEye, color, now, errorState, menuState);

  if (menuState && panelNumber == KOALA_PRIMARY_DISPLAY && !errorState) {
    const uint16_t accent = rgb565(50, 255, 113);
    canvas.fillRoundRect(12, 121, kCanvas - 24, 63, 13, rgb565(4, 9, 13));
    canvas.drawRoundRect(12, 121, kCanvas - 24, 63, 13, accent);
    drawCentered(canvas, "MENU", 130, 2, accent);
    String line(lastMood);
    if (line.length() > 25) line = line.substring(0, 25);
    drawCentered(canvas, line.c_str(), 158, 1, rgb565(219, 226, 220));
  }

  dualEyePushCanvas(panelNumber, canvas, (DISPLAY_WIDTH - kCanvas) / 2,
                    (DISPLAY_HEIGHT - kCanvas) / 2);
}

void renderFrame(uint32_t now) {
  if (!dualEyeDisplayReady() || !dualEyeCanvasReady()) return;
  updateMotion(now);

  const bool errorState = containsI(lastMood, "error") ||
                          containsI(lastMood, "failed") ||
                          eqi(eyes.animation, "error") ||
                          (eqi(eyes.animation, "glitch") &&
                           eqi(eyes.look, "angry"));
  const bool menuState = !errorState &&
                         (eqi(lastMode, "menu") ||
                          eqi(lastMode, "text_input") ||
                          eqi(lastMode, "prompt") ||
                          eqi(lastMode, "warning"));

  // Draw the authoritative good panel first. The same framebuffer is reused
  // for LCD1 only when a replacement panel is explicitly enabled.
  pushPanel(2, false, now, errorState, menuState);
#if KOALA_LCD1_ENABLED
  pushPanel(1, true, now, errorState, false);
#endif
}
}  // namespace

bool setKoalagotchiEyeStyle(const char *look, const char *leftColor,
                            const char *rightColor, const char *animation,
                            int brightnessPercent) {
  snprintf(eyes.look, sizeof(eyes.look), "%s",
           look && look[0] ? look : "cyber");
  snprintf(eyes.animation, sizeof(eyes.animation), "%s",
           animation && animation[0] ? animation : "idle");
  eyes.left = parseHex(leftColor, eyes.left, eyes.leftHex,
                       sizeof(eyes.leftHex));
  eyes.right = parseHex(rightColor, eyes.right, eyes.rightHex,
                        sizeof(eyes.rightHex));
  eyes.brightness = clampInt(brightnessPercent <= 0 ? 100 : brightnessPercent,
                             1, 100);
  return true;
}

void resetKoalagotchiEyeStyle() {
  setKoalagotchiEyeStyle("cyber", "#A54BFF", "#32FF71", "idle", 100);
}

void drawKoalagotchiModeScreen(const char *mode, const char *mood,
                               int contentment, int xpPercent) {
  if (!dualEyeDisplayReady() && !dualEyeDisplayBegin()) return;
  snprintf(lastMode, sizeof(lastMode), "%s",
           mode && mode[0] ? mode : "eucalyptus");
  snprintf(lastMood, sizeof(lastMood), "%s",
           mood && mood[0] ? mood : "calm");
  lastContentment = clampInt(contentment, 0, 100);
  lastXp = clampInt(xpPercent, 0, 100);
  hasScene = true;
  renderFrame(millis());
}

void tickKoalagotchiEyes() {
  if (!hasScene || !dualEyeDisplayReady() || !dualEyeCanvasReady()) return;
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
