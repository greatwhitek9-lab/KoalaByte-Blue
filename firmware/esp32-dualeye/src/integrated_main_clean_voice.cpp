// Clean microphone/VAD wrapper for the proven integrated DualEye runtime.
//
// The original integrated_main.cpp remains the source of truth for displays,
// menus, Wi-Fi/USB, audio playback and Pi coordination. This translation unit
// replaces only setup/loop microphone polling so raw sound never draws an
// AUDIO/MIC overlay or plays a local beep.

#define beginUtterance koalaLegacyBeginUtterance
#define endUtterance koalaLegacyEndUtterance
#define pollMicrophone koalaLegacyPollMicrophone
#define setup koalaLegacySetup
#define loop koalaLegacyLoop
#include "integrated_main.cpp"
#undef loop
#undef setup
#undef pollMicrophone
#undef endUtterance
#undef beginUtterance

namespace {
constexpr uint8_t kVoiceStartConsecutiveFrames = 4;
constexpr uint32_t kMicrophoneWarmupMs = 1800;

uint8_t cleanVoiceHotFrames = 0;
uint32_t cleanMicrophoneReadyAt = 0;

void cleanBeginUtterance(float rms) {
  utteranceActive = true;
  menuWasVisibleBeforeUtterance = menuVisible;
  utteranceId = esp_random();
  utteranceSequence = 0;
  utteranceStartMs = lastSpeechMs = millis();

  // Deliberately do not set an overlay and do not play a cue. The animated
  // eyes remain untouched while PCM is captured for Raspberry Pi STT.
  StaticJsonDocument<448> doc;
  doc["type"] = "audio_utterance_start";
  doc["request_id"] = utteranceId;
  doc["sample_rate"] = AUDIO_INPUT_SAMPLE_RATE;
  doc["channels"] = 1;
  doc["sample_width"] = 2;
  doc["wake_phrases"] = "killerkoala|hey killerkoala";
  doc["rms"] = rms;
  doc["menu_was_visible"] = menuWasVisibleBeforeUtterance;
  doc["execution_owner"] = "raspberry-pi";
  doc["display_policy"] = "eyes_only_until_confirmed_wake";
  doc["local_audio_cue"] = false;
  sendPayload(doc);
}

void cleanEndUtterance(const char *reason) {
  if (!utteranceActive) return;
  StaticJsonDocument<320> doc;
  doc["type"] = "audio_utterance_end";
  doc["request_id"] = utteranceId;
  doc["chunks"] = utteranceSequence;
  doc["reason"] = reason;
  doc["menu_was_visible"] = menuWasVisibleBeforeUtterance;
  doc["display_policy"] = "eyes_unchanged";
  sendPayload(doc);
  utteranceActive = false;
  cleanVoiceHotFrames = 0;
}

void cleanPollMicrophone() {
  if (!dualEyeMicrophoneReady() || dualEyeAudioBusy()) return;

  if (!cleanMicrophoneReadyAt) cleanMicrophoneReadyAt = millis();

  size_t count = dualEyeAudioRead(stereoMic, sizeof(stereoMic));
  if (count < 4) return;

  // Flush codec startup transients without turning them into false speech.
  if (millis() - cleanMicrophoneReadyAt < kMicrophoneWarmupMs) return;

  float rms = dualEyeAudioRms16Stereo(stereoMic, count);
  const int16_t *stereo = reinterpret_cast<const int16_t *>(stereoMic);
  int16_t *mono = reinterpret_cast<int16_t *>(monoMic);
  size_t frames = min(count / 4, sizeof(monoMic) / 2);
  for (size_t index = 0; index < frames; ++index) {
    mono[index] = stereo[index * 2];
  }

  if (!utteranceActive) {
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
    sendPayload(doc);
  }

  if (millis() - utteranceStartMs >= MIC_UTTERANCE_MAX_MS) {
    cleanEndUtterance("max_duration");
  } else if (millis() - lastSpeechMs >= MIC_UTTERANCE_SILENCE_MS) {
    cleanEndUtterance("silence");
  }
}
}  // namespace

void setup() { koalaLegacySetup(); }

void loop() {
  pollSerial();
  pollUdp();
  renderEyesIfActive();
  stageSubsystems();
  cleanPollMicrophone();
  updateDisplayTimeouts();
  heartbeat();
  delay(1);
}
