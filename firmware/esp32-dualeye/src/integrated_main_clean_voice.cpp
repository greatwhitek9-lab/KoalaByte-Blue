// Local-first voice wrapper for the proven integrated DualEye runtime.
//
// ESP32-S3 responsibilities:
//   - always-on English MultiNet phrase recognition
//   - local Killer Koala wake acknowledgements
//   - local repetitive/basic status, help, greeting, thanks and banter replies
//   - fixed menu/submenu command IDs routed to the Raspberry Pi
//   - explicit complex-AI escalation followed by PCM capture for Pi STT/LLM
//
// Raw sound never draws AUDIO/MIC overlays and ambient PCM is never forwarded.

#define beginUtterance koalaLegacyBeginUtterance
#define endUtterance koalaLegacyEndUtterance
#define pollMicrophone koalaLegacyPollMicrophone
#define pollSerial koalaLegacyPollSerial
#define setup koalaLegacySetup
#define loop koalaLegacyLoop
#include "integrated_main.cpp"
#undef loop
#undef setup
#undef pollSerial
#undef pollMicrophone
#undef endUtterance
#undef beginUtterance

#include <ESP_SR.h>
#include "local_voice_responses.h"

namespace {
constexpr uint8_t kVoiceStartConsecutiveFrames = 4;
constexpr uint8_t kMicProbeBlocks = 8;
constexpr uint32_t kAudioCodecSettleMs = 550;
constexpr uint32_t kComplexCaptureWarmupMs = 350;
constexpr uint32_t kComplexCaptureArmTimeoutMs = 9000;
constexpr uint32_t kSrRetryMs = 5000;
constexpr uint32_t kSrHeartbeatMs = 15000;
constexpr float kMicProbeFloor = 0.00045f;

// MultiNet is intentionally used in command mode as the always-on local phrase
// detector. This avoids pretending that RMS/VAD is a wake-word detector and does
// not require a custom Killer Koala WakeNet model.
enum LocalSrCommand : int {
  kCmdWake = 0,
  kCmdLocalStatus,
  kCmdLocalHelp,
  kCmdLocalGreeting,
  kCmdLocalThanks,
  kCmdLocalBanter,
  kCmdComplexAi,
  kCmdBluezStatus,
  kCmdBluezInventory,
  kCmdBluezScan,
  kCmdBluezAllSafe,
  kCmdBluezMonitor,
  kCmdKoalaKapture,
  kCmdKoalaKry,
  kCmdKoalaByteLab,
  kCmdReport,
  kCmdShutdown,
};

static const sr_cmd_t kLocalSpeechCommands[] = {
    {kCmdWake, "Killer Koala"},
    {kCmdWake, "Hey Killer Koala"},
    {kCmdWake, "Killer Koala wake up"},

    {kCmdLocalStatus, "Killer Koala status"},
    {kCmdLocalStatus, "Killer Koala how are you"},
    {kCmdLocalStatus, "Killer Koala you awake"},
    {kCmdLocalStatus, "Killer Koala what is the go"},
    {kCmdLocalStatus, "Killer Koala give me the rundown"},

    {kCmdLocalHelp, "Killer Koala help"},
    {kCmdLocalHelp, "Killer Koala what can you do"},
    {kCmdLocalHelp, "Killer Koala list commands"},

    {kCmdLocalGreeting, "Killer Koala hello"},
    {kCmdLocalGreeting, "Killer Koala good morning"},
    {kCmdLocalGreeting, "Killer Koala good day"},

    {kCmdLocalThanks, "Killer Koala thank you"},
    {kCmdLocalThanks, "Killer Koala good job"},
    {kCmdLocalThanks, "Killer Koala nice work"},

    {kCmdLocalBanter, "Killer Koala tell me something"},
    {kCmdLocalBanter, "Killer Koala say something funny"},
    {kCmdLocalBanter, "Killer Koala entertain me"},

    {kCmdComplexAi, "Killer Koala ask the AI"},
    {kCmdComplexAi, "Killer Koala complex question"},
    {kCmdComplexAi, "Killer Koala big brain"},

    {kCmdBluezStatus, "Killer Koala check Bluetooth"},
    {kCmdBluezStatus, "Killer Koala suss the Bluetooth stack"},
    {kCmdBluezStatus, "Killer Koala give the radio a squiz"},

    {kCmdBluezInventory, "Killer Koala gear check"},
    {kCmdBluezInventory, "Killer Koala check the tools"},

    {kCmdBluezScan, "Killer Koala scan Bluetooth"},
    {kCmdBluezScan, "Killer Koala sweep the air"},
    {kCmdBluezScan, "Killer Koala sniff the gumtrees"},

    {kCmdBluezAllSafe, "Killer Koala run all safe"},
    {kCmdBluezAllSafe, "Killer Koala safe nest run"},

    {kCmdBluezMonitor, "Killer Koala monitor Bluetooth"},
    {kCmdBluezMonitor, "Killer Koala watch the controller"},

    {kCmdKoalaKapture, "Killer Koala Koala Kapture"},
    {kCmdKoalaKapture, "Killer Koala bag the beacons"},

    {kCmdKoalaKry, "Killer Koala Koala Kry"},
    {kCmdKoalaKry, "Killer Koala chew through the logs"},

    {kCmdKoalaByteLab, "Killer Koala KoalaByte Lab"},
    {kCmdKoalaByteLab, "Killer Koala make a lab plan"},

    {kCmdReport, "Killer Koala write report"},
    {kCmdReport, "Killer Koala summarize session"},
    {kCmdReport, "Killer Koala wrap it up"},

    {kCmdShutdown, "Killer Koala shutdown"},
    {kCmdShutdown, "Killer Koala call it a day"},
};

volatile int pendingSrCommand = -1;
volatile int pendingSrPhrase = -1;
volatile uint32_t pendingSrTimeoutCount = 0;
bool srInitAttempted = false;
bool srReady = false;
bool srPaused = false;
bool complexCaptureArmed = false;
uint32_t complexCaptureArmMs = 0;
uint32_t srResumeAt = 0;
uint32_t audioCodecReadyAt = 0;
uint32_t srNextInitAt = 0;
uint32_t lastSrHeartbeatAt = 0;
uint32_t lastAudioWaitStatusAt = 0;
uint32_t reportedSrTimeoutCount = 0;
uint8_t cleanVoiceHotFrames = 0;
uint8_t activeMicChannel = 0;
uint32_t cleanMicrophoneReadyAt = 0;
float micProbeLeftRms = 0.0f;
float micProbeRightRms = 0.0f;
const char *srInputFormat = "MM";

const char *categoryName(LocalVoiceCategory category) {
  switch (category) {
    case LocalVoiceCategory::Wake: return "wake";
    case LocalVoiceCategory::Status: return "status";
    case LocalVoiceCategory::Help: return "help";
    case LocalVoiceCategory::Greeting: return "greeting";
    case LocalVoiceCategory::Thanks: return "thanks";
    case LocalVoiceCategory::Banter: return "banter";
    case LocalVoiceCategory::Escalate: return "escalate";
    default: return "unknown";
  }
}

const char *commandName(int commandId) {
  switch (commandId) {
    case kCmdWake: return "wake";
    case kCmdLocalStatus: return "local_status";
    case kCmdLocalHelp: return "local_help";
    case kCmdLocalGreeting: return "local_greeting";
    case kCmdLocalThanks: return "local_thanks";
    case kCmdLocalBanter: return "local_banter";
    case kCmdComplexAi: return "complex_ai";
    case kCmdBluezStatus: return "bluez_status";
    case kCmdBluezInventory: return "bluez_inventory";
    case kCmdBluezScan: return "bluez_scan";
    case kCmdBluezAllSafe: return "bluez_all_safe";
    case kCmdBluezMonitor: return "bluez_monitor";
    case kCmdKoalaKapture: return "koala_kapture";
    case kCmdKoalaKry: return "koala_kry";
    case kCmdKoalaByteLab: return "koalabyte_lab";
    case kCmdReport: return "report";
    case kCmdShutdown: return "shutdown";
    default: return "unknown";
  }
}

void emitLocalVoiceStatus(const char *status, const char *detail = "") {
  StaticJsonDocument<896> doc;
  doc["type"] = "local_voice_status";
  doc["device"] = "esp32-s3-dualeye";
  doc["status"] = status;
  doc["detail"] = detail;
  doc["recognizer"] = "arduino-esp-sr-multinet-english";
  doc["wake_phrase"] = "killer koala";
  doc["alternate_wake_phrase"] = "hey killer koala";
  doc["input_format"] = srInputFormat;
  doc["active_mic_channel"] = activeMicChannel;
  doc["probe_left_rms"] = micProbeLeftRms;
  doc["probe_right_rms"] = micProbeRightRms;
  doc["sr_ready"] = srReady;
  doc["sr_timeouts"] = pendingSrTimeoutCount;
  doc["mic_ready"] = dualEyeMicrophoneReady();
  doc["speaker_ready"] = dualEyeSpeakerReady();
  doc["audio_status"] = dualEyeAudioStatus();
  doc["basic_response_owner"] = "esp32-s3";
  doc["basic_response_speaker"] = "esp32-s3-es8311";
  doc["complex_response_owner"] = "raspberry-pi";
  doc["complex_response_speaker"] = "raspberry-pi-local-audio";
  doc["ambient_pcm_forwarding"] = false;
  doc["pi_pcm_to_esp32"] = false;
  doc["free_heap"] = ESP.getFreeHeap();
  sendPayload(doc);
}

void calculateStereoRms(const uint8_t *buffer, size_t length, float &left,
                        float &right) {
  left = 0.0f;
  right = 0.0f;
  if (!buffer || length < 4) return;
  const int16_t *samples = reinterpret_cast<const int16_t *>(buffer);
  const size_t frames = length / (sizeof(int16_t) * 2U);
  if (!frames) return;
  double leftSum = 0.0;
  double rightSum = 0.0;
  for (size_t index = 0; index < frames; ++index) {
    const float leftSample = samples[index * 2] / 32768.0f;
    const float rightSample = samples[index * 2 + 1] / 32768.0f;
    leftSum += leftSample * leftSample;
    rightSum += rightSample * rightSample;
  }
  left = sqrt(leftSum / frames);
  right = sqrt(rightSum / frames);
}

bool probeMicrophoneChannels() {
  double leftSquareSum = 0.0;
  double rightSquareSum = 0.0;
  size_t totalFrames = 0;

  for (uint8_t block = 0; block < kMicProbeBlocks; ++block) {
    const size_t count = dualEyeAudioRead(stereoMic, sizeof(stereoMic));
    if (count < 4) {
      delay(20);
      continue;
    }
    const int16_t *samples = reinterpret_cast<const int16_t *>(stereoMic);
    const size_t frames = count / (sizeof(int16_t) * 2U);
    for (size_t index = 0; index < frames; ++index) {
      const float left = samples[index * 2] / 32768.0f;
      const float right = samples[index * 2 + 1] / 32768.0f;
      leftSquareSum += left * left;
      rightSquareSum += right * right;
    }
    totalFrames += frames;
    delay(8);
  }

  if (!totalFrames) {
    micProbeLeftRms = 0.0f;
    micProbeRightRms = 0.0f;
    srInputFormat = "MM";
    activeMicChannel = 0;
    emitLocalVoiceStatus("mic_channel_probe_no_samples",
                         "ESP-SR will try both stereo slots");
    return false;
  }

  micProbeLeftRms = sqrt(leftSquareSum / totalFrames);
  micProbeRightRms = sqrt(rightSquareSum / totalFrames);

  if (micProbeLeftRms < kMicProbeFloor && micProbeRightRms < kMicProbeFloor) {
    srInputFormat = "MM";
    activeMicChannel = micProbeRightRms > micProbeLeftRms ? 1 : 0;
  } else if (micProbeRightRms > micProbeLeftRms * 1.6f) {
    srInputFormat = "NM";
    activeMicChannel = 1;
  } else if (micProbeLeftRms > micProbeRightRms * 1.6f) {
    srInputFormat = "MN";
    activeMicChannel = 0;
  } else {
    srInputFormat = "MM";
    activeMicChannel = micProbeRightRms > micProbeLeftRms ? 1 : 0;
  }

  emitLocalVoiceStatus("mic_channel_probe_complete",
                       "adaptive ES7210 channel mapping selected");
  return true;
}

void pauseLocalRecognition() {
  if (srReady && !srPaused) {
    srPaused = ESP_SR.pause();
  }
}

void resumeLocalRecognition() {
  if (!srReady || !srPaused || complexCaptureArmed || dualEyeAudioBusy()) return;
  if (ESP_SR.resume()) {
    srPaused = false;
    ESP_SR.setMode(SR_MODE_COMMAND);
  }
}

void showLocalSpeakingEyes() {
  clearDisplayModes();
  clearOverlay();
  setKoalagotchiEyeStyle("cyber", "#A54BFF", "#32FF71", "blink", 100);
  drawKoalagotchiModeScreen("killerkoala", "calm", 85, 92);
}

bool playLocalResponse(LocalVoiceCategory category, bool resumeAfter = true) {
  pauseLocalRecognition();
  showLocalSpeakingEyes();
  const char *selectedText = "";
  const bool played = localVoicePlayResponse(category, &selectedText);

  StaticJsonDocument<768> doc;
  doc["type"] = "local_ai_response";
  doc["device"] = "esp32-s3-dualeye";
  doc["category"] = categoryName(category);
  doc["message"] = selectedText;
  doc["handled_on_device"] = true;
  doc["audio_source"] = "embedded_en_au_mulaw";
  doc["speaker_owner"] = "esp32-s3";
  doc["speaker_backend"] = "es8311";
  doc["route_to_pi"] = false;
  doc["played"] = played;
  sendPayload(doc);

  showIdleEyes();
  if (resumeAfter) {
    srResumeAt = millis() + 100;
  }
  return played;
}

void emitPiCommand(const char *commandId, const char *phrase) {
  StaticJsonDocument<768> doc;
  doc["type"] = "voice_command";
  doc["request_id"] = esp_random();
  doc["phrase"] = phrase;
  doc["command_id"] = commandId;
  doc["source"] = "esp32_s3_multinet_local";
  doc["wake_word"] = WAKE_WORD;
  doc["wake_word_detected"] = true;
  doc["local_response_handled"] = false;
  doc["route_to_pi"] = true;
  doc["execution_owner"] = "raspberry-pi";
  doc["response_speaker_owner"] = "raspberry-pi";
  doc["pi_pcm_to_esp32"] = false;
  sendPayload(doc);

  clearOverlay();
  setKoalagotchiEyeStyle("cyber", "#A54BFF", "#32FF71", "scan", 100);
  drawKoalagotchiModeScreen("killerkoala", "thinking", 85, 92);
}

void armComplexCapture() {
  playLocalResponse(LocalVoiceCategory::Escalate, false);
  complexCaptureArmed = true;
  complexCaptureArmMs = millis();
  cleanMicrophoneReadyAt = complexCaptureArmMs;
  cleanVoiceHotFrames = 0;
  utteranceActive = false;
  pauseLocalRecognition();
  emitLocalVoiceStatus("complex_capture_armed",
                       "next utterance routes to Raspberry Pi STT and LLM");
}

void emitDetectedCommand(int commandId, int phraseId) {
  StaticJsonDocument<640> doc;
  doc["type"] = "local_voice_detected";
  doc["device"] = "esp32-s3-dualeye";
  doc["command_id"] = commandId;
  doc["command"] = commandName(commandId);
  doc["phrase_id"] = phraseId;
  doc["input_format"] = srInputFormat;
  doc["active_mic_channel"] = activeMicChannel;
  doc["handled_on_device"] = commandId <= kCmdLocalBanter;
  sendPayload(doc);
}

void processLocalCommand(int commandId, int phraseId) {
  emitDetectedCommand(commandId, phraseId);
  switch (commandId) {
    case kCmdWake:
      playLocalResponse(LocalVoiceCategory::Wake);
      break;
    case kCmdLocalStatus:
      playLocalResponse(LocalVoiceCategory::Status);
      break;
    case kCmdLocalHelp:
      playLocalResponse(LocalVoiceCategory::Help);
      break;
    case kCmdLocalGreeting:
      playLocalResponse(LocalVoiceCategory::Greeting);
      break;
    case kCmdLocalThanks:
      playLocalResponse(LocalVoiceCategory::Thanks);
      break;
    case kCmdLocalBanter:
      playLocalResponse(LocalVoiceCategory::Banter);
      break;
    case kCmdComplexAi:
      armComplexCapture();
      break;
    case kCmdBluezStatus:
      emitPiCommand("bluez_status", "killerkoala suss the bluetooth stack");
      break;
    case kCmdBluezInventory:
      emitPiCommand("bluez_inventory", "killerkoala gear check");
      break;
    case kCmdBluezScan:
      emitPiCommand("bluez_scan", "killerkoala sweep the air");
      break;
    case kCmdBluezAllSafe:
      emitPiCommand("bluez_all_safe", "killerkoala run all safe");
      break;
    case kCmdBluezMonitor:
      emitPiCommand("bluez_monitor", "killerkoala monitor bluetooth");
      break;
    case kCmdKoalaKapture:
      emitPiCommand("koala_kapture", "killerkoala koala kapture");
      break;
    case kCmdKoalaKry:
      emitPiCommand("koala_kry", "killerkoala koala kry");
      break;
    case kCmdKoalaByteLab:
      emitPiCommand("koalabyte_lab", "killerkoala koalabyte lab");
      break;
    case kCmdReport:
      emitPiCommand("report", "killerkoala write report");
      break;
    case kCmdShutdown:
      emitPiCommand("shutdown", "killerkoala shutdown");
      break;
    default:
      emitLocalVoiceStatus("unknown_local_command");
      break;
  }
  if (!complexCaptureArmed) {
    ESP_SR.setMode(SR_MODE_COMMAND);
  }
}

void onSrEvent(sr_event_t event, int commandId, int phraseId) {
  switch (event) {
    case SR_EVENT_WAKEWORD:
    case SR_EVENT_WAKEWORD_CHANNEL:
      pendingSrPhrase = phraseId;
      pendingSrCommand = kCmdWake;
      break;
    case SR_EVENT_COMMAND:
      pendingSrPhrase = phraseId;
      pendingSrCommand = commandId;
      break;
    case SR_EVENT_TIMEOUT:
      ++pendingSrTimeoutCount;
      ESP_SR.setMode(SR_MODE_COMMAND);
      break;
    default:
      break;
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
  ESP_SR.onEvent(onSrEvent);
  srReady = ESP_SR.begin(
      dualEyeAudioBus(), kLocalSpeechCommands,
      sizeof(kLocalSpeechCommands) / sizeof(kLocalSpeechCommands[0]),
      SR_CHANNELS_STEREO, SR_MODE_COMMAND, srInputFormat);
  if (srReady) {
    lastSrHeartbeatAt = now;
    emitLocalVoiceStatus(
        "local_multinet_ready",
        "say Killer Koala slowly and clearly; basic replies stay on the ESP32");
  } else {
    srNextInitAt = now + kSrRetryMs;
    emitLocalVoiceStatus(
        "local_multinet_failed",
        "retry scheduled; check model partition, microphone and free heap");
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
    emitLocalVoiceStatus("local_multinet_listening",
                         "wake and basic command recognition active");
  }
}

void cleanBeginUtterance(float rms) {
  utteranceActive = true;
  menuWasVisibleBeforeUtterance = menuVisible;
  utteranceId = esp_random();
  utteranceSequence = 0;
  utteranceStartMs = lastSpeechMs = millis();

  StaticJsonDocument<640> doc;
  doc["type"] = "audio_utterance_start";
  doc["request_id"] = utteranceId;
  doc["sample_rate"] = AUDIO_INPUT_SAMPLE_RATE;
  doc["channels"] = 1;
  doc["sample_width"] = 2;
  doc["rms"] = rms;
  doc["source_channel"] = activeMicChannel;
  doc["menu_was_visible"] = menuWasVisibleBeforeUtterance;
  doc["execution_owner"] = "raspberry-pi";
  doc["response_speaker_owner"] = "raspberry-pi";
  doc["wake_already_confirmed"] = true;
  doc["phrase_prefix"] = "killerkoala";
  doc["capture_purpose"] = "complex_ai";
  doc["display_policy"] = "eyes_only";
  doc["local_audio_cue"] = false;
  sendPayload(doc);
}

void cleanEndUtterance(const char *reason) {
  if (!utteranceActive) return;
  StaticJsonDocument<448> doc;
  doc["type"] = "audio_utterance_end";
  doc["request_id"] = utteranceId;
  doc["chunks"] = utteranceSequence;
  doc["reason"] = reason;
  doc["menu_was_visible"] = menuWasVisibleBeforeUtterance;
  doc["wake_already_confirmed"] = true;
  doc["capture_purpose"] = "complex_ai";
  doc["response_speaker_owner"] = "raspberry-pi";
  sendPayload(doc);

  utteranceActive = false;
  complexCaptureArmed = false;
  cleanVoiceHotFrames = 0;
  srResumeAt = millis() + 150;
}

void cancelComplexCapture(const char *reason) {
  complexCaptureArmed = false;
  utteranceActive = false;
  cleanVoiceHotFrames = 0;
  emitLocalVoiceStatus("complex_capture_cancelled", reason);
  showIdleEyes();
  srResumeAt = millis() + 100;
}

void cleanPollMicrophone() {
  if (!complexCaptureArmed || !dualEyeMicrophoneReady() || dualEyeAudioBusy()) {
    return;
  }
  if (!utteranceActive &&
      millis() - complexCaptureArmMs >= kComplexCaptureArmTimeoutMs) {
    cancelComplexCapture("no follow-up speech detected");
    return;
  }

  const size_t count = dualEyeAudioRead(stereoMic, sizeof(stereoMic));
  if (count < 4) return;
  if (millis() - cleanMicrophoneReadyAt < kComplexCaptureWarmupMs) return;

  float leftRms = 0.0f;
  float rightRms = 0.0f;
  calculateStereoRms(stereoMic, count, leftRms, rightRms);
  const float rms = activeMicChannel ? rightRms : leftRms;
  const int16_t *stereo = reinterpret_cast<const int16_t *>(stereoMic);
  int16_t *mono = reinterpret_cast<int16_t *>(monoMic);
  const size_t frames = min(count / 4, sizeof(monoMic) / 2);
  for (size_t index = 0; index < frames; ++index) {
    mono[index] = stereo[index * 2 + activeMicChannel];
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
    doc["source_channel"] = activeMicChannel;
    sendPayload(doc);
  }

  if (millis() - utteranceStartMs >= MIC_UTTERANCE_MAX_MS) {
    cleanEndUtterance("max_duration");
  } else if (millis() - lastSpeechMs >= MIC_UTTERANCE_SILENCE_MS) {
    cleanEndUtterance("silence");
  }
}

LocalVoiceCategory categoryFromName(const char *name) {
  if (!name) return LocalVoiceCategory::Wake;
  if (!strcmp(name, "status")) return LocalVoiceCategory::Status;
  if (!strcmp(name, "help")) return LocalVoiceCategory::Help;
  if (!strcmp(name, "greeting")) return LocalVoiceCategory::Greeting;
  if (!strcmp(name, "thanks")) return LocalVoiceCategory::Thanks;
  if (!strcmp(name, "banter")) return LocalVoiceCategory::Banter;
  if (!strcmp(name, "escalate")) return LocalVoiceCategory::Escalate;
  return LocalVoiceCategory::Wake;
}

void pollSerial() {
  while (Serial.available()) {
    const char value = static_cast<char>(Serial.read());
    if (value == '\n') {
      const String line = serialLine;
      serialLine = "";
      StaticJsonDocument<640> doc;
      if (!deserializeJson(doc, line)) {
        const char *type = doc["type"] | "";
        if (!strcmp(type, "local_voice_test")) {
          playLocalResponse(categoryFromName(doc["category"] | "wake"));
          continue;
        }
        if (!strcmp(type, "local_voice_status_request")) {
          emitLocalVoiceStatus(srReady ? "local_multinet_listening"
                                       : "local_multinet_not_ready");
          continue;
        }
      }
      handleCommand(line);
    } else if (value != '\r') {
      serialLine += value;
      if (serialLine.length() > 12288) serialLine = "";
    }
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
