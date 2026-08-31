from __future__ import annotations

from pathlib import Path


MARKER = "async_binary_pcm_preroll_v1"


def apply_async_preroll(source: Path) -> None:
    text = source.read_text(encoding="utf-8")

    if MARKER in text:
        required = (
            "VoicePcmFrame voicePreRoll[MIC_PRE_ROLL_BLOCKS]",
            "rememberVoicePreRoll(frame);",
            "flushVoicePreRoll();",
            'doc["pcm_preroll_blocks"] = MIC_PRE_ROLL_BLOCKS;',
        )
        missing = [item for item in required if item not in text]
        if missing:
            raise RuntimeError(
                f"async pre-roll marker present but output incomplete: {missing}"
            )
        print("DualEye async PCM pre-roll already restored")
        return

    pipeline_marker = "freertos_capture_queue_binary_udp_v1"
    if pipeline_marker not in text:
        raise RuntimeError("async pre-roll restore requires binary async PCM pipeline")

    state_anchor = "uint32_t lastVoicePipelineStatusAt = 0;\n"
    state_count = text.count(state_anchor)
    if state_count != 1:
        raise RuntimeError(
            f"async pre-roll restore expected one state anchor, found {state_count}"
        )
    state_patch = state_anchor + f'''\n// {MARKER}\nVoicePcmFrame voicePreRoll[MIC_PRE_ROLL_BLOCKS] = {{}};\nuint8_t voicePreRollWrite = 0;\nuint8_t voicePreRollCount = 0;\n'''
    text = text.replace(state_anchor, state_patch, 1)

    append_anchor = '''void appendVoicePcmFrame(const VoicePcmFrame &frame) {\n  if (!frame.bytes || frame.bytes > MIC_PCM_CHUNK_BYTES) return;\n  if (voiceBatchBytes + frame.bytes > sizeof(voiceBatchPcm)) flushVoicePcmBatch();\n  if (voiceBatchBytes + frame.bytes > sizeof(voiceBatchPcm)) return;\n\n  memcpy(voiceBatchPcm + voiceBatchBytes, frame.pcm, frame.bytes);\n  voiceBatchBytes += frame.bytes;\n  ++voiceBatchFrameCount;\n  if (frame.rms >= voiceBatchPeakRms) {\n    voiceBatchPeakRms = frame.rms;\n    voiceBatchSourceChannel = frame.sourceChannel;\n  }\n  if (voiceBatchFrameCount >= kVoiceBatchFrames) flushVoicePcmBatch();\n}\n'''
    append_count = text.count(append_anchor)
    if append_count != 1:
        raise RuntimeError(
            f"async pre-roll restore expected one append helper anchor, found {append_count}"
        )

    helpers = append_anchor + r'''
void resetVoicePreRoll() {
  voicePreRollWrite = 0;
  voicePreRollCount = 0;
}

void rememberVoicePreRoll(const VoicePcmFrame &frame) {
  if (!frame.bytes || frame.bytes > MIC_PCM_CHUNK_BYTES) return;
  voicePreRoll[voicePreRollWrite] = frame;
  voicePreRollWrite = (voicePreRollWrite + 1U) % MIC_PRE_ROLL_BLOCKS;
  if (voicePreRollCount < MIC_PRE_ROLL_BLOCKS) ++voicePreRollCount;
}

void flushVoicePreRoll() {
  if (!voicePreRollCount) return;
  const uint8_t oldest =
      (voicePreRollWrite + MIC_PRE_ROLL_BLOCKS - voicePreRollCount) %
      MIC_PRE_ROLL_BLOCKS;
  for (uint8_t index = 0; index < voicePreRollCount; ++index) {
    const uint8_t slot = (oldest + index) % MIC_PRE_ROLL_BLOCKS;
    appendVoicePcmFrame(voicePreRoll[slot]);
  }
  resetVoicePreRoll();
}
'''
    text = text.replace(append_anchor, helpers, 1)

    service_anchor = '''    if (!utteranceActive && frame.rms >= MIC_WAKE_RMS_THRESHOLD) {\n      koalaLegacyBeginUtterance(frame.rms);\n      resetVoicePcmBatch();\n    }\n\n    if (utteranceActive) {\n      appendVoicePcmFrame(frame);\n      if (frame.rms >= MIC_WAKE_RMS_THRESHOLD * 0.55f) {\n        lastSpeechMs = frame.capturedAtMs;\n      }\n    }\n'''
    service_count = text.count(service_anchor)
    if service_count != 1:
        raise RuntimeError(
            f"async pre-roll restore expected one service anchor, found {service_count}"
        )
    service_patch = '''    if (!utteranceActive && frame.rms >= MIC_WAKE_RMS_THRESHOLD) {\n      koalaLegacyBeginUtterance(frame.rms);\n      resetVoicePcmBatch();\n      flushVoicePreRoll();\n    }\n\n    if (utteranceActive) {\n      appendVoicePcmFrame(frame);\n      if (frame.rms >= MIC_WAKE_RMS_THRESHOLD * 0.55f) {\n        lastSpeechMs = frame.capturedAtMs;\n      }\n    } else {\n      rememberVoicePreRoll(frame);\n    }\n'''
    text = text.replace(service_anchor, service_patch, 1)

    status_anchor = '    doc["pcm_wire"] = "binary_udp_v1";\n'
    status_count = text.count(status_anchor)
    if status_count < 2:
        raise RuntimeError(
            f"async pre-roll restore expected binary status anchors, found {status_count}"
        )
    text = text.replace(
        status_anchor,
        status_anchor + '    doc["pcm_preroll_blocks"] = MIC_PRE_ROLL_BLOCKS;\n',
    )

    required = (
        MARKER,
        "VoicePcmFrame voicePreRoll[MIC_PRE_ROLL_BLOCKS]",
        "void rememberVoicePreRoll(const VoicePcmFrame &frame)",
        "void flushVoicePreRoll()",
        "flushVoicePreRoll();",
        "rememberVoicePreRoll(frame);",
        'doc["pcm_preroll_blocks"] = MIC_PRE_ROLL_BLOCKS;',
        "freertos_capture_queue_binary_udp_v1",
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise RuntimeError(f"async pre-roll restore output missing markers: {missing}")

    source.write_text(text, encoding="utf-8")
    print("Restored three-block pre-roll to async binary PCM capture path")


try:
    Import("env")  # type: ignore[name-defined]  # noqa: F821
    _platformio_env = env  # type: ignore[name-defined]  # noqa: F821
except NameError:
    _platformio_env = None


if _platformio_env is not None:
    project = Path(_platformio_env.subst("$PROJECT_DIR"))
    apply_async_preroll(project / "src" / "integrated_main_wake_session.cpp")
elif __name__ == "__main__":
    project = Path(__file__).resolve().parents[1]
    apply_async_preroll(project / "src" / "integrated_main_wake_session.cpp")
