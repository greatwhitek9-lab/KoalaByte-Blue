#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

using KoalaTouchJsonSender = void (*)(JsonDocument &doc);

void setupTouchMenu();
void pollTouchMenu(KoalaTouchJsonSender sendJson);
void emitTouchMenuStatus(KoalaTouchJsonSender sendJson, const char *statusType = "touch_menu_status");
bool handleTouchMenuCommand(JsonDocument &doc, KoalaTouchJsonSender sendJson);
