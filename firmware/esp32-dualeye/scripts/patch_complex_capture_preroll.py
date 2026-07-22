Import("env")

from pathlib import Path

project = Path(env.subst("$PROJECT_DIR"))
source = project / "src" / "integrated_main_wake_session.cpp"
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"complex-capture pre-roll expected one {label} anchor, found {count}"
        )
    text = text.replace(old, new, 1)


replace_once(
    """uint8_t cleanVoiceHotFrames = 0;
uint8_t activeMicChannel = 0;
uint32_t cleanMicrophoneReadyAt = 0;
""",
    """uint8_t cleanVoiceHotFrames = 0;
uint8_t activeMicChannel = 0;
uint32_t cleanMicrophoneReadyAt = 0;
uint8_t complexPreRoll[MIC_PRE_ROLL_BLOCKS][MIC_PCM_CHUNK_BYTES] = {};
size_t complexPreRollLengths[MIC_PRE_ROLL_BLOCKS] = {};
uint8_t complexPreRollWrite = 0;
uint8_t complexPreRollCount = 0;
""",
    "pre-roll state",
)

replace_once(
    """void cleanBeginUtterance(float rms) {
""",
    """void resetComplexPreRoll() {
  memset(complexPreRollLengths, 0, sizeof(complexPreRollLengths));
  complexPreRollWrite = 0;
  complexPreRollCount = 0;
}

void rememberComplexPreRoll(const uint8_t *data, size_t length) {
  if (!data || !length) return;
  const size_t take = min(length, static_cast<size_t>(MIC_PCM_CHUNK_BYTES));
  memcpy(complexPreRoll[complexPreRollWrite], data, take);
  complexPreRollLengths[complexPreRollWrite] = take;
  complexPreRollWrite = (complexPreRollWrite + 1U) % MIC_PRE_ROLL_BLOCKS;
  if (complexPreRollCount < MIC_PRE_ROLL_BLOCKS) ++complexPreRollCount;
}

void emitComplexPcmChunk(const uint8_t *data, size_t length, float rms,
                         bool preRoll = false) {
  if (!data || !length) return;
  size_t encodedLength = 0;
  if (mbedtls_base64_encode(
          reinterpret_cast<unsigned char *>(base64Buffer),
          sizeof(base64Buffer) - 1, &encodedLength, data, length) != 0) {
    return;
  }
  base64Buffer[encodedLength] = 0;
  StaticJsonDocument<1280> doc;
  doc["type"] = "audio_pcm_chunk";
  doc["request_id"] = utteranceId;
  doc["sequence"] = utteranceSequence++;
  doc["pcm_s16le_mono_b64"] = base64Buffer;
  doc["rms"] = rms;
  doc["source_channel"] = activeMicChannel;
  doc["pre_roll"] = preRoll;
  sendPayload(doc);
}

void flushComplexPreRoll(float rms) {
  if (!complexPreRollCount) return;
  const uint8_t oldest =
      (complexPreRollWrite + MIC_PRE_ROLL_BLOCKS - complexPreRollCount) %
      MIC_PRE_ROLL_BLOCKS;
  for (uint8_t index = 0; index < complexPreRollCount; ++index) {
    const uint8_t slot = (oldest + index) % MIC_PRE_ROLL_BLOCKS;
    emitComplexPcmChunk(complexPreRoll[slot], complexPreRollLengths[slot], rms,
                        true);
  }
  resetComplexPreRoll();
}

void cleanBeginUtterance(float rms) {
""",
    "pre-roll helpers",
)

replace_once(
    """  cleanVoiceHotFrames = 0;
  utteranceActive = false;
  pauseLocalRecognition();
""",
    """  cleanVoiceHotFrames = 0;
  utteranceActive = false;
  resetComplexPreRoll();
  pauseLocalRecognition();
""",
    "capture-arm reset",
)

replace_once(
    """  utteranceActive = false;
  complexCaptureArmed = false;
  cleanVoiceHotFrames = 0;
  srResumeAt = millis() + 150;
""",
    """  utteranceActive = false;
  complexCaptureArmed = false;
  cleanVoiceHotFrames = 0;
  resetComplexPreRoll();
  srResumeAt = millis() + 150;
""",
    "capture-end reset",
)

replace_once(
    """  complexCaptureArmed = false;
  utteranceActive = false;
  cleanVoiceHotFrames = 0;
  emitLocalVoiceStatus("complex_capture_cancelled", reason);
""",
    """  complexCaptureArmed = false;
  utteranceActive = false;
  cleanVoiceHotFrames = 0;
  resetComplexPreRoll();
  emitLocalVoiceStatus("complex_capture_cancelled", reason);
""",
    "capture-cancel reset",
)

replace_once(
    """  if (!utteranceActive) {
    if (rms >= MIC_WAKE_RMS_THRESHOLD) {
      if (cleanVoiceHotFrames < 255) ++cleanVoiceHotFrames;
      if (cleanVoiceHotFrames >= kVoiceStartConsecutiveFrames) {
        cleanBeginUtterance(rms);
      }
    } else {
      cleanVoiceHotFrames = 0;
    }
  }
  if (!utteranceActive) return;

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
    doc["source_channel"] = activeMicChannel;
    sendPayload(doc);
  }
""",
    """  if (!utteranceActive) {
    bool startedNow = false;
    if (rms >= MIC_WAKE_RMS_THRESHOLD) {
      if (cleanVoiceHotFrames < 255) ++cleanVoiceHotFrames;
      if (cleanVoiceHotFrames >= kVoiceStartConsecutiveFrames) {
        cleanBeginUtterance(rms);
        flushComplexPreRoll(rms);
        startedNow = true;
      }
    } else {
      cleanVoiceHotFrames = 0;
    }
    if (!startedNow) {
      rememberComplexPreRoll(monoMic, frames * sizeof(int16_t));
      return;
    }
  }

  if (rms >= MIC_WAKE_RMS_THRESHOLD * 0.55f) lastSpeechMs = millis();
  emitComplexPcmChunk(monoMic, frames * sizeof(int16_t), rms);
""",
    "capture detection and PCM emission",
)

source.write_text(text, encoding="utf-8")
print("Patched three-block complex voice capture pre-roll")
