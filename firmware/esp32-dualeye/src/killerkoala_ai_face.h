#pragma once

void showKillerKoalaAiFace(
  const char *state,
  const char *message,
  const char *left_color,
  const char *right_color,
  int brightness_percent,
  int duration_ms
);
void hideKillerKoalaAiFace();
bool isKillerKoalaAiFaceActive();
void tickKillerKoalaAiFace();
