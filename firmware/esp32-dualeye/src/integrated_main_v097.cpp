// v0.9.7 entrypoint layered over the validated v0.9.6 local-first runtime.
//
// The underlying implementation remains unchanged except for recognizer table
// ordering: generated full commands and bare local menu controls are registered
// before the short Killer Koala wake phrase. This prevents the wake entry from
// consuming longer phrases such as "Killer Koala launch Koala Kombat Kruisin".

#define prepareSpeechCommandTable koalaV096PrepareSpeechCommandTable
#define setupLocalRecognition koalaV096SetupLocalRecognition
#define serviceLocalRecognition koalaV096ServiceLocalRecognition
#define setup koalaV096Setup
#define loop koalaV096Loop
#include "integrated_main_clean_voice.cpp"
#undef loop
#undef setup
#undef serviceLocalRecognition
#undef setupLocalRecognition
#undef prepareSpeechCommandTable

namespace {
void prepareSpeechCommandTable() {
  size_t outputIndex = 0;

  // Specific phrases must be registered before the short wake-only phrases.
  // MultiNet otherwise reports "Killer Koala" before reaching a longer command.
  for (const auto &command : kGeneratedSpeechCommands) {
    kAllSpeechCommands[outputIndex++] = command;
  }
  for (const auto &command : kBaseSpeechCommands) {
    kAllSpeechCommands[outputIndex++] = command;
  }
}

void setupLocalRecognition() {
  const uint32_t now = millis();
  if (srReady || now < srNextInitAt) return;

  if (!dualEyeMicrophoneReady()) {
    if (now - lastAudioWaitStatusAt >= 5000) {
      lastAudioWaitStatusAt = now;
      emitLocalVoiceStatus("waiting_for_es7210_microphone",
                           "local recognition has not started");
    }
    return;
  }

  if (!audioCodecReadyAt) {
    audioCodecReadyAt = now;
    emitLocalVoiceStatus("es7210_settling",
                         "waiting before ESP-SR channel probe");
    return;
  }
  if (now - audioCodecReadyAt < kAudioCodecSettleMs) return;

  srInitAttempted = true;
  probeMicrophoneChannels();
  prepareSpeechCommandTable();
  ESP_SR.onEvent(onSrEvent);
  srReady = ESP_SR.begin(dualEyeAudioBus(), kAllSpeechCommands,
                         kAllSpeechCommandCount, SR_CHANNELS_STEREO,
                         SR_MODE_COMMAND, srInputFormat);
  if (srReady) {
    lastSrHeartbeatAt = now;
    emitLocalVoiceStatus(
        "local_multinet_ready",
        "KillerKoala wake, bare menu controls, K1-K8 and full catalog are active");
  } else {
    srNextInitAt = now + kSrRetryMs;
    emitLocalVoiceStatus(
        "local_multinet_failed",
        "retry scheduled; check command count, model partition and microphone");
  }
}

void serviceLocalRecognition() {
  setupLocalRecognition();
  if (!srReady) return;

  const uint32_t now = millis();
  if (dualEyeAudioBusy()) {
    pauseLocalRecognition();
  } else if (srResumeAt && static_cast<int32_t>(now - srResumeAt) >= 0) {
    srResumeAt = 0;
    resumeLocalRecognition();
  } else if (!complexCaptureArmed) {
    resumeLocalRecognition();
  }

  const int command = pendingSrCommand;
  if (command >= 0) {
    const int phrase = pendingSrPhrase;
    pendingSrCommand = -1;
    pendingSrPhrase = -1;
    processLocalCommand(command, phrase);
  }

  if (reportedSrTimeoutCount != pendingSrTimeoutCount) {
    reportedSrTimeoutCount = pendingSrTimeoutCount;
    if (reportedSrTimeoutCount <= 2 || reportedSrTimeoutCount % 10 == 0) {
      emitLocalVoiceStatus("local_multinet_rearmed_after_timeout",
                           "recognizer remains in always-on command mode");
    }
  }

  if (now - lastSrHeartbeatAt >= kSrHeartbeatMs) {
    lastSrHeartbeatAt = now;
    emitLocalVoiceStatus(
        "local_multinet_listening",
        "wake, bare menu controls, K1-K8 and full catalog recognition active");
  }
}
}  // namespace

void setup() { koalaLegacySetup(); }

void loop() {
  pollSerial();
  pollUdp();
  renderEyesIfActive();
  stageSubsystems();
  serviceLocalRecognition();
  cleanPollMicrophone();
  updateDisplayTimeouts();
  heartbeat();
  delay(1);
}
