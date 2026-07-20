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
    """bool playLocalResponse(LocalVoiceCategory category, bool resumeAfter = true) {
""",
    """void emitLocalSpeechLifecycle(bool active, LocalVoiceCategory category,
                              const char *message = "") {
  StaticJsonDocument<512> doc;
  doc["type"] = "local_speech_state";
  doc["device"] = "esp32-s3-dualeye";
  doc["active"] = active;
  doc["category"] = categoryName(category);
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
print(f"Patched ESP32 local speech start/stop lifecycle: {path}")
