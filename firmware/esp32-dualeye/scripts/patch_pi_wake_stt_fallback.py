from __future__ import annotations

from pathlib import Path


def apply_fallback(source: Path) -> None:
    text = source.read_text(encoding="utf-8")

    helper_anchor = "}  // namespace\n\nvoid setup()"
    if helper_anchor not in text:
        raise RuntimeError("Pi wake/STT fallback could not find the final namespace/setup anchor")

    helper = r'''void servicePiWakeSttFallback() {
  static bool announced = false;
  static uint8_t activeChannel = 0;
  static uint32_t lastMicLevelStatusAt = 0;

  if (!dualEyeMicrophoneReady() || dualEyeAudioBusy()) return;

  const size_t count = dualEyeAudioRead(stereoMic, sizeof(stereoMic));
  if (count < 4) return;

  const int16_t *stereo = reinterpret_cast<const int16_t *>(stereoMic);
  const size_t frames = min(count / 4, sizeof(monoMic) / 2);
  if (!frames) return;

  double leftSquareSum = 0.0;
  double rightSquareSum = 0.0;
  for (size_t index = 0; index < frames; ++index) {
    const float left = stereo[index * 2] / 32768.0f;
    const float right = stereo[index * 2 + 1] / 32768.0f;
    leftSquareSum += left * left;
    rightSquareSum += right * right;
  }
  const float leftRms = sqrt(leftSquareSum / frames);
  const float rightRms = sqrt(rightSquareSum / frames);

  // The ES7210/TDM wiring can present the active onboard microphone on either
  // stereo slot. Select the stronger channel continuously instead of assuming
  // the left slot, which made the Pi fallback appear deaf on right-slot boards.
  activeChannel = rightRms > leftRms ? 1 : 0;
  const float rms = activeChannel ? rightRms : leftRms;

  if (!announced) {
    announced = true;
    StaticJsonDocument<896> doc;
    doc["type"] = "local_voice_status";
    doc["device"] = "esp32-s3-dualeye";
    doc["status"] = "pi_wake_stt_fallback_ready";
    doc["detail"] =
        "ESP-SR quarantined; adaptive ES7210 stereo PCM routed to Raspberry Pi wake/STT";
    doc["recognizer"] = "raspberry-pi-stt";
    doc["wake_phrase"] = "killer koala";
    doc["alternate_wake_phrase"] = "hey killer koala";
    doc["sr_ready"] = false;
    doc["mic_ready"] = true;
    doc["speaker_ready"] = dualEyeSpeakerReady();
    doc["audio_status"] = dualEyeAudioStatus();
    doc["multinet_command_count"] = 0;
    doc["pi_wake_stt_fallback"] = true;
    doc["adaptive_stereo"] = true;
    doc["active_mic_channel"] = activeChannel;
    doc["left_rms"] = leftRms;
    doc["right_rms"] = rightRms;
    doc["free_heap"] = ESP.getFreeHeap();
    sendPayload(doc);
  }

  for (size_t index = 0; index < frames; ++index) {
    reinterpret_cast<int16_t *>(monoMic)[index] =
        stereo[index * 2 + activeChannel];
  }

  if (!utteranceActive && rms >= MIC_WAKE_RMS_THRESHOLD) {
    koalaLegacyBeginUtterance(rms);
  }
  if (!utteranceActive) {
    const uint32_t now = millis();
    if (now - lastMicLevelStatusAt >= MIC_STATUS_INTERVAL_MS) {
      lastMicLevelStatusAt = now;
      StaticJsonDocument<512> doc;
      doc["type"] = "mic_level_status";
      doc["device"] = "esp32-s3-dualeye";
      doc["active_mic_channel"] = activeChannel;
      doc["left_rms"] = leftRms;
      doc["right_rms"] = rightRms;
      doc["trigger_rms"] = rms;
      doc["threshold"] = MIC_WAKE_RMS_THRESHOLD;
      sendPayload(doc);
    }
    return;
  }

  if (rms >= MIC_WAKE_RMS_THRESHOLD * 0.55f) lastSpeechMs = millis();

  size_t encodedLength = 0;
  if (mbedtls_base64_encode(
          reinterpret_cast<unsigned char *>(base64Buffer),
          sizeof(base64Buffer) - 1, &encodedLength, monoMic,
          frames * sizeof(int16_t)) == 0) {
    base64Buffer[encodedLength] = 0;
    StaticJsonDocument<1280> doc;
    doc["type"] = "audio_pcm_chunk";
    doc["request_id"] = utteranceId;
    doc["sequence"] = utteranceSequence++;
    doc["pcm_s16le_mono_b64"] = base64Buffer;
    doc["rms"] = rms;
    doc["source_channel"] = activeChannel;
    sendPayload(doc);
  }

  if (millis() - utteranceStartMs >= MIC_UTTERANCE_MAX_MS) {
    koalaLegacyEndUtterance("max_duration");
  } else if (millis() - lastSpeechMs >= MIC_UTTERANCE_SILENCE_MS) {
    koalaLegacyEndUtterance("silence");
  }
}

'''

    if "void servicePiWakeSttFallback()" not in text:
        text = text.replace(helper_anchor, helper + helper_anchor, 1)

    loop_start = text.rfind("\nvoid loop() {")
    if loop_start < 0:
        raise RuntimeError("Pi wake/STT fallback could not find the generated loop")
    loop_text = text[loop_start:]
    old = "  serviceLocalRecognition();\n  cleanPollMicrophone();\n"
    count = loop_text.count(old)
    if count != 1:
        raise RuntimeError(
            f"Pi wake/STT fallback expected one ESP-SR loop anchor, found {count}"
        )
    loop_text = loop_text.replace(old, "  servicePiWakeSttFallback();\n", 1)
    text = text[:loop_start] + loop_text

    required = (
        "void servicePiWakeSttFallback()",
        'doc["status"] = "pi_wake_stt_fallback_ready";',
        'doc["pi_wake_stt_fallback"] = true;',
        'doc["adaptive_stereo"] = true;',
        "rightRms > leftRms ? 1 : 0",
        "koalaLegacyBeginUtterance(rms);",
        "koalaLegacyEndUtterance(\"silence\");",
        'doc["type"] = "mic_level_status";',
        "  servicePiWakeSttFallback();",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise RuntimeError(f"Pi wake/STT fallback output missing markers: {missing}")

    source.write_text(text, encoding="utf-8")
    print(
        "Patched DualEye voice runtime to adaptive-stereo Pi wake/STT fallback; "
        "ESP-SR initialization quarantined"
    )


try:
    Import("env")  # type: ignore[name-defined]  # noqa: F821
    _platformio_env = env  # type: ignore[name-defined]  # noqa: F821
except NameError:
    _platformio_env = None


if _platformio_env is not None:
    project = Path(_platformio_env.subst("$PROJECT_DIR"))
    apply_fallback(project / "src" / "integrated_main_wake_session.cpp")
elif __name__ == "__main__":
    project = Path(__file__).resolve().parents[1]
    source = project / "src" / "integrated_main_wake_session.cpp"
    apply_fallback(source)