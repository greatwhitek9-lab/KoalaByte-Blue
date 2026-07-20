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
            f"local speech lifecycle patch expected exactly one {label} anchor, found {count}"
        )
    text = text.replace(old, new, 1)


replace_once(
    """void showLocalSpeakingEyes() {
  clearDisplayModes();
  clearOverlay();
  setKoalagotchiEyeStyle("cyber", "#A54BFF", "#32FF71", "blink", 100);
  drawKoalagotchiModeScreen("killerkoala", "calm", 85, 92);
}
""",
    """const char *localSpeechTone(LocalVoiceCategory category) {
  switch (category) {
    case LocalVoiceCategory::Wake: return "excited";
    case LocalVoiceCategory::Status: return "focused";
    case LocalVoiceCategory::Help: return "curious";
    case LocalVoiceCategory::Acknowledgement: return "happy";
    case LocalVoiceCategory::Banter: return "mischievous";
    case LocalVoiceCategory::Success: return "happy";
    case LocalVoiceCategory::Error: return "angry";
    case LocalVoiceCategory::Escalate: return "curious";
    default: return "neutral";
  }
}

const char *localSpeechMouth(LocalVoiceCategory category) {
  switch (category) {
    case LocalVoiceCategory::Error: return "snarl";
    case LocalVoiceCategory::Banter: return "sideways_grin";
    case LocalVoiceCategory::Status: return "bite";
    default: return "smile";
  }
}

void showLocalSpeakingEyes(LocalVoiceCategory category) {
  clearDisplayModes();
  clearOverlay();
  const char *look = "cyber";
  const char *left = "#A54BFF";
  const char *right = "#32FF71";
  const char *animation = "blink";
  const char *mood = localSpeechTone(category);
  switch (category) {
    case LocalVoiceCategory::Wake:
    case LocalVoiceCategory::Success:
      look = "star"; left = "#32FF71"; right = "#FFD84A"; animation = "pulse"; break;
    case LocalVoiceCategory::Help:
    case LocalVoiceCategory::Escalate:
      look = "round"; left = "#4DD9FF"; right = "#A54BFF"; animation = "scan"; break;
    case LocalVoiceCategory::Acknowledgement:
      look = "heart"; left = "#32FF71"; right = "#A54BFF"; animation = "pulse"; break;
    case LocalVoiceCategory::Banter:
      look = "slit"; left = "#A54BFF"; right = "#32FF71"; animation = "glitch"; break;
    case LocalVoiceCategory::Error:
      look = "angry"; left = "#FF2B2B"; right = "#FF7A00"; animation = "glitch"; break;
    case LocalVoiceCategory::Status:
      look = "cyber"; left = "#4DD9FF"; right = "#32FF71"; animation = "scan"; break;
    default:
      break;
  }
  setKoalagotchiEyeStyle(look, left, right, animation, 100);
  drawKoalagotchiModeScreen("killerkoala", mood, 85, 92);
}
""",
    "tone-specific local speaking eyes",
)

replace_once(
    """bool playLocalResponse(LocalVoiceCategory category, bool resumeAfter = true) {
  pauseLocalRecognition();
  showLocalSpeakingEyes();
""",
    """void emitLocalSpeechLifecycle(bool active, LocalVoiceCategory category,
                               const char *message = "") {
  StaticJsonDocument<768> doc;
  doc["type"] = "local_speech_state";
  doc["device"] = "esp32-s3-dualeye";
  doc["active"] = active;
  doc["category"] = categoryName(category);
  doc["tone"] = localSpeechTone(category);
  doc["subject"] = "waveshare_local_vocabulary";
  doc["mouth_expression"] = localSpeechMouth(category);
  doc["speech_motion"] = category == LocalVoiceCategory::Error
      ? "hard_emphasis"
      : (category == LocalVoiceCategory::Banter ? "cheeky" : "natural");
  doc["message"] = active ? message : "";
  doc["channel"] = "esp32-local";
  doc["source"] = "esp32-s3-dualeye";
  doc["speaker_owner"] = "esp32-s3";
  doc["target_display"] = "heltec-t114";
  doc["wake_response"] = category == LocalVoiceCategory::Wake;
  doc["requires_pi_response"] = false;
  sendPayload(doc);
}

bool playLocalResponse(LocalVoiceCategory category, bool resumeAfter = true) {
  pauseLocalRecognition();
  showLocalSpeakingEyes(category);
""",
    "local response function declaration",
)

replace_once(
    """  const char *selectedText = "";
  const bool played = localVoicePlayResponse(category, &selectedText);

  StaticJsonDocument<768> doc;
""",
    """  const char *selectedText = "";
  emitLocalSpeechLifecycle(true, category, categoryName(category));
  // Give the Pi bridge one serial/UDP poll interval to start the Heltec mouth.
  delay(12);
  const bool played = localVoicePlayResponse(category, &selectedText);
  emitLocalSpeechLifecycle(false, category, selectedText);

  StaticJsonDocument<768> doc;
""",
    "local playback lifecycle",
)

path.write_text(text, encoding="utf-8")
print(f"Patched tone-aware ESP32 local speech lifecycle: {path}")
