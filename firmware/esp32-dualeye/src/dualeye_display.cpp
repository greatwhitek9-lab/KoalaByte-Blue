#include "dualeye_display.h"

#include <Arduino.h>
#include <SPI.h>

#include "config.h"

namespace {
Adafruit_GC9A01A lcd1(&SPI, DISPLAY_SPI_DC_PIN, DISPLAY_LCD1_CS_PIN, DISPLAY_LCD1_RESET_PIN);
Adafruit_GC9A01A lcd2(&SPI, DISPLAY_SPI_DC_PIN, DISPLAY_LCD2_CS_PIN, DISPLAY_LCD2_RESET_PIN);
GFXcanvas16 *sharedCanvas = nullptr;
bool ready = false;
bool lcd1Ready = false;
bool lcd2Ready = false;

void setBacklightPin(int pin, bool on) {
  if (pin < 0) return;
  digitalWrite(pin, on ? HIGH : LOW);
}

bool allocateSharedCanvas() {
  if (sharedCanvas && sharedCanvas->getBuffer()) return true;
  delete sharedCanvas;
  sharedCanvas = new GFXcanvas16(KOALA_EYE_CANVAS_SIZE, KOALA_EYE_CANVAS_SIZE);
  if (!sharedCanvas || !sharedCanvas->getBuffer()) {
    Serial.println("{\"type\":\"display_fault\",\"stage\":\"framebuffer\",\"reason\":\"allocation_failed\"}");
    delete sharedCanvas;
    sharedCanvas = nullptr;
    return false;
  }
  Serial.printf("{\"type\":\"display_stage\",\"stage\":\"framebuffer_ready\",\"bytes\":%lu}\n",
                (unsigned long)KOALA_EYE_CANVAS_SIZE * (unsigned long)KOALA_EYE_CANVAS_SIZE * 2UL);
  return true;
}
}  // namespace

bool dualEyeDisplayBegin() {
  if (ready) return true;

  Serial.println("{\"type\":\"display_stage\",\"stage\":\"begin\",\"profile\":\"lcd2_first_recovery\"}");

  pinMode(DISPLAY_LCD1_CS_PIN, OUTPUT);
  pinMode(DISPLAY_LCD2_CS_PIN, OUTPUT);
  digitalWrite(DISPLAY_LCD1_CS_PIN, HIGH);
  digitalWrite(DISPLAY_LCD2_CS_PIN, HIGH);

  pinMode(DISPLAY_LCD1_BACKLIGHT_PIN, OUTPUT);
  pinMode(DISPLAY_LCD2_BACKLIGHT_PIN, OUTPUT);
  setBacklightPin(DISPLAY_LCD1_BACKLIGHT_PIN, false);
  setBacklightPin(DISPLAY_LCD2_BACKLIGHT_PIN, false);

  if (!allocateSharedCanvas()) return false;

  SPI.begin(DISPLAY_SPI_SCLK_PIN, DISPLAY_SPI_MISO_PIN, DISPLAY_SPI_MOSI_PIN, -1);

#if KOALA_LCD2_ENABLED
  Serial.println("{\"type\":\"display_stage\",\"stage\":\"lcd2_init\"}");
  lcd2.begin(DISPLAY_SPI_SCLK_HZ);
  lcd2.setRotation(DISPLAY_LCD2_ROTATION);
  lcd2.invertDisplay(DISPLAY_INVERT_COLOR != 0);
  lcd2.fillScreen(0x0000);
  lcd2Ready = true;
  setBacklightPin(DISPLAY_LCD2_BACKLIGHT_PIN, true);
  Serial.println("{\"type\":\"display_stage\",\"stage\":\"lcd2_ready\"}");
#endif

#if KOALA_LCD1_ENABLED
  Serial.println("{\"type\":\"display_stage\",\"stage\":\"lcd1_init\"}");
  lcd1.begin(DISPLAY_SPI_SCLK_HZ);
  lcd1.setRotation(DISPLAY_LCD1_ROTATION);
  lcd1.invertDisplay(DISPLAY_INVERT_COLOR != 0);
  lcd1.fillScreen(0x0000);
  lcd1Ready = true;
  setBacklightPin(DISPLAY_LCD1_BACKLIGHT_PIN, true);
  Serial.println("{\"type\":\"display_stage\",\"stage\":\"lcd1_ready\"}");
#else
  Serial.println("{\"type\":\"display_stage\",\"stage\":\"lcd1_skipped\",\"reason\":\"recovery_profile_damaged_panel\"}");
#endif

  ready = lcd1Ready || lcd2Ready;
  return ready;
}

bool dualEyeDisplayReady() { return ready; }

bool dualEyePanelReady(uint8_t panelNumber) {
  return panelNumber == 1 ? lcd1Ready : panelNumber == 2 ? lcd2Ready : false;
}

bool dualEyeCanvasReady() {
  return sharedCanvas != nullptr && sharedCanvas->getBuffer() != nullptr;
}

Adafruit_GC9A01A &dualEyeLcd1() { return lcd1; }
Adafruit_GC9A01A &dualEyeLcd2() { return lcd2; }

Adafruit_GC9A01A &dualEyePrimaryLcd() {
#if KOALA_PRIMARY_DISPLAY == 1
  return lcd1;
#else
  return lcd2;
#endif
}

Adafruit_GC9A01A &dualEyeSecondaryLcd() {
#if KOALA_PRIMARY_DISPLAY == 1
  return lcd2;
#else
  return lcd1;
#endif
}

GFXcanvas16 &dualEyeCanvas() { return *sharedCanvas; }

void dualEyeSetBacklights(bool lcd1On, bool lcd2On) {
  setBacklightPin(DISPLAY_LCD1_BACKLIGHT_PIN, lcd1Ready && lcd1On);
  setBacklightPin(DISPLAY_LCD2_BACKLIGHT_PIN, lcd2Ready && lcd2On);
}

void dualEyeClear(uint16_t color) {
  if (!ready) return;
  if (lcd1Ready) lcd1.fillScreen(color);
  if (lcd2Ready) lcd2.fillScreen(color);
}

void dualEyePushCanvas(uint8_t panelNumber, GFXcanvas16 &canvas, int16_t x, int16_t y) {
  if (!ready || !dualEyePanelReady(panelNumber) || canvas.getBuffer() == nullptr) return;
  Adafruit_GC9A01A &display = panelNumber == 1 ? lcd1 : lcd2;
  display.startWrite();
  display.setAddrWindow((uint16_t)x, (uint16_t)y, (uint16_t)canvas.width(),
                        (uint16_t)canvas.height());
  display.writePixels(canvas.getBuffer(),
                      (uint32_t)canvas.width() * (uint32_t)canvas.height(),
                      true, false);
  display.endWrite();
}
