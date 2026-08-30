from __future__ import annotations

from pathlib import Path


def apply_fallback(source: Path) -> None:
    text = source.read_text(encoding="utf-8")

    helper_anchor = "}  // namespace\n\nvoid setup()"
    if helper_anchor not in text:
        raise RuntimeError("Pi wake/STT fallback could not find the final namespace/setup anchor")

    helper = r'''void servicePiWakeSttFallback() {
  static bool announced = false;
  if (!dualEyeMicrophoneReady()) return;

  if (!announced) {
    announced = true;
    StaticJsonDocument<768> doc;
    doc["type"] = "local_voice_status";
    doc["device"] = "esp32-s3-dualeye";
    doc["status"] = "pi_wake_stt_fallback_ready";
    doc["detail"] =
        "ESP-SR quarantined after reset-loop isolation; ES7210 PCM routed to Raspberry Pi wake/STT";
    doc["recognizer"] = "raspberry-pi-stt";
    doc["wake_phrase"] = "killer koala";
    doc["alternate_wake_phrase"] = "hey killer koala";
    doc["sr_ready"] = false;
    doc["mic_ready"] = true;
    doc["speaker_ready"] = dualEyeSpeakerReady();
    doc["audio_status"] = dualEyeAudioStatus();
    doc["multinet_command_count"] = 0;
    doc["pi_wake_stt_fallback"] = true;
    doc["free_heap"] = ESP.getFreeHeap();
    sendPayload(doc);
  }

  // Reuse the proven ES7210 RMS-gated PCM capture from the integrated runtime.
  // The Pi bridge transcribes the completed utterance and rejects it unless the
  // KillerKoala wake phrase is present, so ambient speech is never executed.
  koalaLegacyPollMicrophone();
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
        "koalaLegacyPollMicrophone();",
        "  servicePiWakeSttFallback();",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise RuntimeError(f"Pi wake/STT fallback output missing markers: {missing}")

    source.write_text(text, encoding="utf-8")
    print(
        "Patched DualEye voice runtime to Pi wake/STT fallback; "
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
