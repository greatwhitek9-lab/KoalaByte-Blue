#pragma once

// Draws the KoalaByte Blue high-color Koalagotchi mode screen on the ESP32-S3 DualEye display.
// These screens are display-only status views. The Pi companion still owns the safe workflow logic.
void drawKoalagotchiModeScreen(const char *mode, const char *mood, int contentment, int xp_percent);
