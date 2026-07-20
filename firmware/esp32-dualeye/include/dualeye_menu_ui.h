#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

void dualEyeMenuShow(JsonDocument &document);
void dualEyeMenuHide();
bool dualEyeMenuVisible();
void dualEyeMenuTick();
