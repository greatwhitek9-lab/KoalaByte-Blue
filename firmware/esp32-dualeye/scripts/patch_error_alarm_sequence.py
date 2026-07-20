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
            f"error-alarm patch expected exactly one {label} anchor, found {count}"
        )
    text = text.replace(old, new, 1)


replace_once(
    '  const char *tone = doc["tone"] | state;\n',
    '''  const bool alarmState = !strcmp(state, "error") ||
                          !strcmp(state, "alarmed") ||
                          !strcmp(state, "fault") ||
                          !strcmp(state, "exception");
  const char *tone = doc["tone"] | (alarmState ? "error" : state);
''',
    "tone alarm default",
)

replace_once(
    '''void handleFace(JsonDocument &doc) {
  const char *state = doc["state"] | "idle";
  const char *message = doc["message"] | state;
  voiceMode = strcmp(state, "idle") != 0 && strcmp(state, "hidden") != 0;
  if (voiceMode) {
    setOverlay(currentAction[0] ? currentAction : "VOICE COMMAND", message, state,
               !strcmp(state, "error"));
  } else {
    clearOverlay();
  }
  applyToneFace(doc, state, message);
  if (!strcmp(state, "success")) faceReturnAt = millis() + 2600;
  else if (!strcmp(state, "error")) faceReturnAt = millis() + 6000;
}
''',
    '''void handleFace(JsonDocument &doc) {
  const char *state = doc["state"] | "idle";
  const char *message = doc["message"] | state;
  const bool clearAlarm = !strcmp(state, "error_clear") ||
                          !strcmp(state, "alarm_clear") ||
                          !strcmp(state, "recovered");
  if (clearAlarm) {
    showIdleEyes();
    emitStatus("error_alarm_cleared_idle_eyes_restored");
    return;
  }

  const bool alarmState = !strcmp(state, "error") ||
                          !strcmp(state, "alarmed") ||
                          !strcmp(state, "fault") ||
                          !strcmp(state, "exception");
  voiceMode = strcmp(state, "idle") != 0 && strcmp(state, "hidden") != 0;
  if (voiceMode) {
    setOverlay(currentAction[0] ? currentAction : "KOALABYTE ALERT", message,
               alarmState ? "ALARM" : state, alarmState);
  } else {
    clearOverlay();
  }
  applyToneFace(doc, state, message);
  if (alarmState) {
    // User/runtime errors remain visible until the Pi sends error_clear. This
    // keeps the ESP32 synchronized with the Heltec lifecycle alarm latch.
    faceReturnAt = 0;
    emitStatus("error_alarm_latched_waiting_for_pi_clear");
  } else if (!strcmp(state, "success")) {
    faceReturnAt = millis() + 2600;
  }
}
''',
    "tone-aware face alarm lifecycle",
)

replace_once(
    '''  if (!success) {
    voiceMode = true;
    setOverlay(action, message, status, true);
    setFace("error", message);
    faceReturnAt = millis() + 6500;
    return;
  }
''',
    '''  if (!success) {
    voiceMode = true;
    setOverlay(action, message, "ALARM", true);
    setFace("error", message);
    // The Pi error-dig sequence owns the clear transition. Hardware/runtime
    // faults therefore stay visible instead of silently expiring.
    faceReturnAt = 0;
    emitStatus("pi_execution_error_alarm_latched");
    return;
  }
''',
    "execution-result alarm latch",
)

path.write_text(text, encoding="utf-8")
print(f"Patched synchronized purple/green error alarm lifecycle: {path}")
