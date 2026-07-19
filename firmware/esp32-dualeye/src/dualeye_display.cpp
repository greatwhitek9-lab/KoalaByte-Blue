#include "dualeye_display.h"

#include <Arduino.h>
#include <SPI.h>

#include "config.h"

namespace {
Adafruit_GC9A01A lcd1(&SPI, DISPLAY_SPI_DC_PIN, DISPLAY_LCD1_CS_PIN, DISPLAY_LCD1_RESET_PIN);
Adafruit_GC9A01A lcd2(&SPI, DISPLAY_SPI_DC_PIN, DISPLAY_LCD2_CS_PIN, DISPLAY_LCD2_RESET_PIN);
bool ready = false;

void setBacklightPin(int pin, bool on) {
  if (pin < 0) return;
  digitalWrite(pin, on ? HIGH : LOW);
}
}  // namespace

bool dualEyeDisplayBegin() {
  if (ready) return true;

  pinMode(DISPLAY_LCD1_CS_PIN, OUTPUT);
  pinMode(DISPLAY_LCD2_CS_PIN, OUTPUT);
  digitalWrite(DISPLAY_LCD1_CS_PIN, HIGH);
  digitalWrite(DISPLAY_LCD2_CS_PIN, HIGH);

  pinMode(DISPLAY_LCD1_BACKLIGHT_PIN, OUTPUT);
  pinMode(DISPLAY_LCD2_BACKLIGHT_PIN, OUTPUT);
  setBacklightPin(DISPLAY_LCD1_BACKLIGHT_PIN, false);
  setBacklightPin(DISPLAY_LCD2_BACKLIGHT_PIN, false);

  SPI.begin(DISPLAY_SPI_SCLK_PIN, DISPLAY_SPI_MISO_PIN, DISPLAY_SPI_MOSI_PIN, -1);

  lcd1.begin(DISPLAY_SPI_SCLK_HZ);
  lcd1.setRotation(DISPLAY_LCD1_ROTATION);
  lcd1.invertDisplay(DISPLAY_INVERT_COLOR != 0);

  lcd2.begin(DISPLAY_SPI_SCLK_HZ);
  lcd2.setRotation(DISPLAY_LCD2_ROTATION);
  lcd2.invertDisplay(DISPLAY_INVERT_COLOR != 0);

  lcd1.fillScreen(0x0000);
  lcd2.fillScreen(0x0000);
  dualEyeSetBacklights(true, true);
  ready = true;
  return true;
}

bool dualEyeDisplayReady() { return ready; }

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

void dualEyeSetBacklights(bool lcd1On, bool lcd2On) {
  setBacklightPin(DISPLAY_LCD1_BACKLIGHT_PIN, lcd1On);
  setBacklightPin(DISPLAY_LCD2_BACKLIGHT_PIN, lcd2On);
}

void dualEyeClear(uint16_t color) {
  if (!ready) return;
  lcd1.fillScreen(color);
  lcd2.fillScreen(color);
}

void dualEyePushCanvas(uint8_t panelNumber, GFXcanvas16 &canvas, int16_t x, int16_t y) {
  if (!ready || canvas.getBuffer() == nullptr) return;
  Adafruit_GC9A01A &display = panelNumber == 1 ? lcd1 : lcd2;
  display.startWrite();
  display.setAddrWindow((uint16_t)x, (uint16_t)y, (uint16_t)canvas.width(),
                        (uint16_t)canvas.height());
  display.writePixels(canvas.getBuffer(),
                      (uint32_t)canvas.width() * (uint32_t)canvas.height(),
                      true, false);
  display.endWrite();
}
