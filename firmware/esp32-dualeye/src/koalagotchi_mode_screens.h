#pragma once

void drawKoalagotchiModeScreen(const char *mode, const char *mood, int contentment, int xp_percent);
bool setKoalagotchiEyeStyle(const char *look, const char *left_color, const char *right_color, const char *animation, int brightness_percent);
void resetKoalagotchiEyeStyle();
void tickKoalagotchiEyes();
const char *getKoalagotchiEyeLook();
const char *getKoalagotchiEyeAnimation();
const char *getKoalagotchiLeftEyeHex();
const char *getKoalagotchiRightEyeHex();
int getKoalagotchiEyeBrightness();
