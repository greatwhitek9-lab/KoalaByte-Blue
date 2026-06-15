#pragma once

#include <TFT_eSPI.h>

void drawEucalyptusMenuBorder(TFT_eSPI &tft);
void drawJungleMenuTitle(TFT_eSPI &tft, const char *title);
void drawJungleMenuItem(TFT_eSPI &tft, int row, const char *label, bool selected, bool enabled);
