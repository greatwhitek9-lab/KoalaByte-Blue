Import("env")

from pathlib import Path

project = Path(env.subst("$PROJECT_DIR"))
path = project / "src" / "integrated_main.cpp"
text = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"alarm-background patch expected exactly one {label} anchor, found {count}"
        )
    text = text.replace(old, new, 1)


replace_once(
    """bool overlayError = false;
""",
    """bool overlayError = false;
bool alarmBackgroundActive = false;
uint32_t lastAlarmBackgroundDraw = 0;
""",
    "alarm state",
)

replace_once(
    """void setFace(const char *state, const char *message = "") {
""",
    """void drawAlarmPanel(Adafruit_GC9A01A &display, bool leftPanel) {
  const bool greenPhase = ((millis() / 180U) & 1U) != 0;
  const uint16_t purple = rgb565(165, 75, 255);
  const uint16_t green = rgb565(50, 255, 113);
  const uint16_t active = greenPhase ? green : purple;
  const uint16_t opposite = greenPhase ? purple : green;
  const uint16_t top = leftPanel ? active : opposite;
  const uint16_t bottom = leftPanel ? opposite : active;

  // Keep the center eye canvas visible. Only the surrounding cyber background
  // panels and warning rails alternate purple and green.
  display.fillRect(0, 0, DISPLAY_WIDTH, 24, top);
  display.fillRect(0, DISPLAY_HEIGHT - 24, DISPLAY_WIDTH, 24, bottom);
  display.fillRect(0, 24, 22, DISPLAY_HEIGHT - 48, bottom);
  display.fillRect(DISPLAY_WIDTH - 22, 24, 22, DISPLAY_HEIGHT - 48, top);
  display.drawRoundRect(23, 25, DISPLAY_WIDTH - 46, DISPLAY_HEIGHT - 50, 18,
                        greenPhase ? purple : green);
  for (int x = 28; x < DISPLAY_WIDTH - 28; x += 36) {
    display.fillRect(x, 4, 16, 5, bottom);
    display.fillRect(x + 16, DISPLAY_HEIGHT - 9, 16, 5, top);
  }
}

void drawAlarmBackground(bool force = false) {
  if (!alarmBackgroundActive) return;
  if (!force && millis() - lastAlarmBackgroundDraw < 70U) return;
  lastAlarmBackgroundDraw = millis();
  if (dualEyePanelReady(1)) drawAlarmPanel(dualEyeLcd1(), true);
  if (dualEyePanelReady(2)) drawAlarmPanel(dualEyeLcd2(), false);
}

void setFace(const char *state, const char *message = "") {
""",
    "alarm renderer insertion",
)

replace_once(
    """  else if (!strcmp(state, "action")) animation = "glitch";
  else if (!strcmp(state, "success")) {
""",
    """  else if (!strcmp(state, "action")) animation = "glitch";
  else if (!strcmp(state, "error") || !strcmp(state, "alarmed") ||
           !strcmp(state, "fault") || !strcmp(state, "exception")) {
    look = "angry";
    animation = "glitch";
    alarmBackgroundActive = true;
  } else if (!strcmp(state, "success")) {
""",
    "alert face state",
)

replace_once(
    """void showIdleEyes() {
  voiceMode = false;
""",
    """void showIdleEyes() {
  alarmBackgroundActive = false;
  lastAlarmBackgroundDraw = 0;
  voiceMode = false;
""",
    "alarm clear on idle",
)

replace_once(
    """void renderEyesIfActive() {
  if (!menuVisible && !actionStatusVisible) {
    tickKoalagotchiEyes();
    drawStatusBars();
  }
}
""",
    """void renderEyesIfActive() {
  if (!menuVisible && !actionStatusVisible) {
    tickKoalagotchiEyes();
    drawStatusBars();
    drawAlarmBackground();
  }
}
""",
    "alarm redraw after eye animation",
)

replace_once(
    """void handleEyeStyle(JsonDocument &doc) {
  clearDisplayModes();
""",
    """void handleEyeStyle(JsonDocument &doc) {
  clearDisplayModes();
  const char *requestedMood = doc["mood"] | doc["tone"] | "neutral";
  const char *requestedLook = doc["eye_look"] | doc["look"] | "cyber";
  const char *requestedAnimation =
      doc["eye_animation"] | doc["animation"] | "idle";
  const bool requestedAlarmStyle =
      !strcmp(requestedMood, "error") || !strcmp(requestedMood, "alarm") ||
      !strcmp(requestedMood, "failed") || !strcmp(requestedMood, "fault") ||
      (!strcmp(requestedLook, "angry") &&
       (!strcmp(requestedAnimation, "glitch") ||
        !strcmp(requestedAnimation, "error")));
  if (!requestedAlarmStyle) {
    alarmBackgroundActive = false;
    overlayError = false;
    lastAlarmBackgroundDraw = 0;
  }
""",
    "normal eye style clears stale alarm",
)

replace_once(
    """void handleFace(JsonDocument &doc) {
  const char *state = doc["state"] | "idle";
  const char *message = doc["message"] | state;
  voiceMode = strcmp(state, "idle") != 0 && strcmp(state, "hidden") != 0;
""",
    """void handleFace(JsonDocument &doc) {
  const char *state = doc["state"] | "idle";
  const char *message = doc["message"] | state;
  const char *tone = doc["tone"] | state;
  if (!strcmp(state, "error_clear") || !strcmp(state, "alarm_clear") ||
      !strcmp(state, "recovered")) {
    alarmBackgroundActive = false;
    overlayError = false;
    showIdleEyes();
    emitStatus("error_alarm_cleared_idle_eyes_restored");
    return;
  }
  const bool alarmRequested = doc["alarm_background"] |
      (!strcmp(state, "error") || !strcmp(state, "alarmed") ||
       !strcmp(state, "fault") || !strcmp(state, "exception") ||
       !strcmp(tone, "error"));
  if (alarmRequested) alarmBackgroundActive = true;
  voiceMode = strcmp(state, "idle") != 0 && strcmp(state, "hidden") != 0;
""",
    "face alarm command handling",
)

replace_once(
    """    setOverlay(currentAction[0] ? currentAction : "VOICE COMMAND", message, state,
               !strcmp(state, "error"));
""",
    """    setOverlay(currentAction[0] ? currentAction :
                   (alarmRequested ? "KOALABYTE ALERT" : "VOICE COMMAND"),
               message, alarmRequested ? "ALARM" : state, alarmRequested);
""",
    "alarm overlay state",
)

replace_once(
    """  applyToneFace(doc, state, message);
  if (!strcmp(state, "success")) faceReturnAt = millis() + 2600;
  else if (!strcmp(state, "error")) faceReturnAt = millis() + 6000;
""",
    """  applyToneFace(doc, state, message);
  if (alarmRequested) {
    // Guarantee the same cyber purple/green angry expression even when an older
    // sender supplies only state=alarmed without a tone payload.
    setKoalagotchiEyeStyle("angry", "#A54BFF", "#32FF71", "glitch", 100);
    drawKoalagotchiModeScreen("killerkoala", "error", 85, 92);
    faceReturnAt = 0;
    emitStatus("error_alarm_latched_waiting_for_pi_clear");
  } else if (!strcmp(state, "success")) {
    faceReturnAt = millis() + 2600;
  }
  drawAlarmBackground(true);
""",
    "latched alarm expression and initial draw",
)

replace_once(
    """  if (!success) {
    voiceMode = true;
    setOverlay(action, message, status, true);
    setFace("error", message);
    faceReturnAt = millis() + 6500;
    return;
  }
""",
    """  if (!success) {
    voiceMode = true;
    setOverlay(action, message, "ALARM", true);
    setFace("error", message);
    alarmBackgroundActive = true;
    faceReturnAt = 0;
    drawAlarmBackground(true);
    emitStatus("pi_execution_error_alarm_latched");
    return;
  }
""",
    "execution-result alarm latch",
)

path.write_text(text, encoding="utf-8")
print(f"Patched flashing purple/green DualEye alarm lifecycle: {path}")