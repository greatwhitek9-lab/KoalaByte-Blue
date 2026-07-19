#pragma once

#include <Adafruit_GFX.h>
#include <Adafruit_GC9A01A.h>

bool dualEyeDisplayBegin();
bool dualEyeDisplayReady();
bool dualEyePanelReady(uint8_t panelNumber);
bool dualEyeCanvasReady();

Adafruit_GC9A01A &dualEyeLcd1();
Adafruit_GC9A01A &dualEyeLcd2();
Adafruit_GC9A01A &dualEyePrimaryLcd();
Adafruit_GC9A01A &dualEyeSecondaryLcd();
GFXcanvas16 &dualEyeCanvas();

void dualEyeSetBacklights(bool lcd1On, bool lcd2On);
void dualEyeClear(uint16_t color);
void dualEyePushCanvas(uint8_t panelNumber, GFXcanvas16 &canvas, int16_t x, int16_t y);
