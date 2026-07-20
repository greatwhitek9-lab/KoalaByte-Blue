Import("env")

from pathlib import Path

project = Path(env.subst("$PROJECT_DIR"))
path = project / "src" / "integrated_main_wake_session.cpp"
text = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"tone-expression patch expected exactly one {label} anchor, found {count}"
        )
    text = text.replace(old, new, 1)


replace_once(
    """char currentAction[74] = "";
char currentResult[98] = "";
char currentEvent[34] = "";
""",
    """char currentAction[74] = "";
char currentResult[98] = "";
char currentEvent[34] = "";
char activeSpeechTone[24] = "neutral";
char activeSpeechSubject[28] = "conversation";
char activeSpeechLook[16] = "cyber";
char activeSpeechAnimation[16] = "blink";
char activeSpeechLeftEye[12] = "#A54BFF";
char activeSpeechRightEye[12] = "#32FF71";
uint8_t activeSpeechIntensity = 100;
""",
    "speech expression state",
)

replace_once(
    """void handleFace(JsonDocument &doc) {
""",
    """void toneDefaults(const char *state, const char *tone,
                  const char *&look, const char *&animation,
                  const char *&left, const char *&right) {
  look = "cyber";
  animation = "blink";
  left = "#A54BFF";
  right = "#32FF71";
  if (!strcmp(tone, "angry")) {
    look = "angry"; animation = "glitch"; left = "#FF2B2B"; right = "#FF7A00";
  } else if (!strcmp(tone, "error")) {
    look = "x"; animation = "glitch"; left = "#FF2B55"; right = "#A54BFF";
  } else if (!strcmp(tone, "happy")) {
    look = "heart"; animation = "pulse"; left = "#32FF71"; right = "#A54BFF";
  } else if (!strcmp(tone, "excited")) {
    look = "star"; animation = "pulse"; left = "#32FF71"; right = "#FFD84A";
  } else if (!strcmp(tone, "curious")) {
    look = "round"; animation = "scan"; left = "#4DD9FF"; right = "#A54BFF";
  } else if (!strcmp(tone, "focused")) {
    look = "cyber"; animation = "scan"; left = "#4DD9FF"; right = "#32FF71";
  } else if (!strcmp(tone, "concerned")) {
    look = "slit"; animation = "pulse"; left = "#FFB000"; right = "#A54BFF";
  } else if (!strcmp(tone, "disappointed")) {
    look = "sleepy"; animation = "blink"; left = "#5D7CFF"; right = "#A54BFF";
  } else if (!strcmp(tone, "mischievous")) {
    look = "slit"; animation = "glitch"; left = "#A54BFF"; right = "#32FF71";
  } else if (!strcmp(state, "thinking")) {
    animation = "scan";
  }
}

void applyToneFace(JsonDocument &doc, const char *state, const char *message) {
  const char *tone = doc["tone"] | state;
  const char *subject = doc["subject"] | "conversation";
  const char *fallbackLook;
  const char *fallbackAnimation;
  const char *fallbackLeft;
  const char *fallbackRight;
  toneDefaults(state, tone, fallbackLook, fallbackAnimation, fallbackLeft, fallbackRight);

  const char *look = doc["eye_look"] | fallbackLook;
  const char *animation = doc["eye_animation"] | fallbackAnimation;
  const char *left = doc["left_eye"] | fallbackLeft;
  const char *right = doc["right_eye"] | fallbackRight;
  int intensity = doc["intensity"] | doc["brightness"] | 100;
  intensity = constrain(intensity, 20, 100);

  copyText(activeSpeechTone, sizeof(activeSpeechTone), tone, "neutral");
  copyText(activeSpeechSubject, sizeof(activeSpeechSubject), subject, "conversation");
  copyText(activeSpeechLook, sizeof(activeSpeechLook), look, "cyber");
  copyText(activeSpeechAnimation, sizeof(activeSpeechAnimation), animation, "blink");
  copyText(activeSpeechLeftEye, sizeof(activeSpeechLeftEye), left, "#A54BFF");
  copyText(activeSpeechRightEye, sizeof(activeSpeechRightEye), right, "#32FF71");
  activeSpeechIntensity = static_cast<uint8_t>(intensity);

  clearDisplayModes();
  setKoalagotchiEyeStyle(activeSpeechLook, activeSpeechLeftEye,
                         activeSpeechRightEye, activeSpeechAnimation,
                         activeSpeechIntensity);
  drawKoalagotchiModeScreen("killerkoala",
                            message && message[0] ? message : activeSpeechTone,
                            85, 92);
  drawStatusBars(true);
}

void showStoredSpeechExpression(const char *message) {
  clearDisplayModes();
  setKoalagotchiEyeStyle(activeSpeechLook, activeSpeechLeftEye,
                         activeSpeechRightEye, activeSpeechAnimation,
                         activeSpeechIntensity);
  drawKoalagotchiModeScreen("killerkoala",
                            message && message[0] ? message : activeSpeechTone,
                            85, 92);
  drawStatusBars(true);
}

void handleFace(JsonDocument &doc) {
""",
    "tone helper insertion",
)

replace_once(
    """  setFace(state, message);
  if (!strcmp(state, "success")) faceReturnAt = millis() + 2600;
""",
    """  applyToneFace(doc, state, message);
  if (!strcmp(state, "success")) faceReturnAt = millis() + 2600;
""",
    "face tone application",
)

replace_once(
    """    setFace("speaking", doc["message"] | "speaking");
    dualEyeAudioWriteMono16(reinterpret_cast<const int16_t *>(decoded),
""",
    """    showStoredSpeechExpression(doc["message"] | "speaking");
    dualEyeAudioWriteMono16(reinterpret_cast<const int16_t *>(decoded),
""",
    "audio chunk expression retention",
)

path.write_text(text, encoding="utf-8")
print(f"Patched tone/subject expression retention during Pi speech: {path}")
