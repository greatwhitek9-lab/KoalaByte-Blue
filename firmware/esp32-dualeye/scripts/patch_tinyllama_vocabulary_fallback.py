Import("env")

from pathlib import Path

project = Path(env.subst("$PROJECT_DIR"))
path = project / "src" / "integrated_main_wake_session.cpp"
text = path.read_text(encoding="utf-8")

old = """    case SR_EVENT_TIMEOUT:
      ++pendingSrTimeoutCount;
      ESP_SR.setMode(SR_MODE_COMMAND);
      break;
"""
new = """    case SR_EVENT_TIMEOUT:
      ++pendingSrTimeoutCount;
      if (wakeSessionActive && !complexCaptureArmed && !dualEyeAudioBusy()) {
        pendingSrPhrase = phraseId;
        pendingSrCommand = kCmdComplexAi;
        setWakeSessionReason("waveshare_vocabulary_miss_to_tinyllama");
        emitLocalVoiceStatus(
            "local_vocabulary_miss",
            "Waveshare vocabulary did not match; arming Raspberry Pi TinyLlama capture");
      } else {
        ESP_SR.setMode(SR_MODE_COMMAND);
      }
      break;
"""

count = text.count(old)
if count != 1:
    raise RuntimeError(
        f"TinyLlama vocabulary-fallback patch expected one timeout anchor, found {count}"
    )

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print(f"Patched Waveshare local-vocabulary fallback to TinyLlama: {path}")
