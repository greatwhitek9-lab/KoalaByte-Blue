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
#define setup koalaLegacySetup
#define loop koalaLegacyLoop
#include "integrated_main.cpp"
#undef loop
#undef setup
#undef pollMicrophone
#undef endUtterance
#undef beginUtterance

#include <ESP_SR.h>
#include "local_voice_responses.h"

namespace {
constexpr uint8_t kVoiceStartConsecutiveFrames = 4;
constexpr uint32_t kComplexCaptureWarmupMs = 350;
constexpr uint32_t kComplexCaptureArmTimeoutMs = 9000;

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
bool srInitAttempted = false;
bool srReady = false;
bool srPaused = false;
bool complexCaptureArmed = false;
uint32_t complexCaptureArmMs = 0;
uint32_t srResumeAt = 0;
uint8_t cleanVoiceHotFrames = 0;
uint32_t cleanMicrophoneReadyAt = 0;

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

void emitLocalVoiceStatus(const char *status, const char *detail = "") {
  StaticJsonDocument<512> doc;
  doc["type"] = "local_voice_status";
  doc["device"] = "esp32-s3-dualeye";
  doc["status"] = status;
  doc["detail"] = detail;
  doc["recognizer"] = "arduino-esp-sr-multinet-english";
  doc["wake_phrase"] = "killer koala";
  doc["basic_response_owner"] = "esp32-s3";
  doc["complex_response_owner"] = "raspberry-pi";
  doc["ambient_pcm_forwarding"] = false;
  sendPayload(doc);
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

  StaticJsonDocument<640> doc;
  doc["type"] = "local_ai_response";
  doc["device"] = "esp32-s3-dualeye";
  doc["category"] = categoryName(category);
  doc["message"] = selectedText;
  doc["handled_on_device"] = true;
  doc["audio_source"] = "embedded_en_au_mulaw";
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
  StaticJsonDocument<640> doc;
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

void processLocalCommand(int commandId) {
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
  (void)phraseId;
  switch (event) {
    case SR_EVENT_WAKEWORD:
    case SR_EVENT_WAKEWORD_CHANNEL:
      pendingSrCommand = kCmdWake;
      break;
    case SR_EVENT_COMMAND:
      pendingSrCommand = commandId;
      break;
    case SR_EVENT_TIMEOUT:
      ESP_SR.setMode(SR_MODE_COMMAND);
      break;
    default:
      break;
  }
}

void setupLocalRecognition() {
  if (srInitAttempted || !dualEyeMicrophoneReady() || !dualEyeSpeakerReady()) {
    return;
  }
  srInitAttempted = true;
  ESP_SR.onEvent(onSrEvent);
  srReady = ESP_SR.begin(
      dualEyeAudioBus(), kLocalSpeechCommands,
      sizeof(kLocalSpeechCommands) / sizeof(kLocalSpeechCommands[0]),
      SR_CHANNELS_STEREO, SR_MODE_COMMAND, "MN");
  if (srReady) {
    emitLocalVoiceStatus("local_multinet_ready",
                         "basic responses stay local; fixed actions and complex AI route to Pi");
  } else {
    emitLocalVoiceStatus("local_multinet_failed",
                         "check ESP-SR model partition and srmodels.bin");
  }
}

void serviceLocalRecognition() {
  setupLocalRecognition();
  if (!srReady) return;

  if (dualEyeAudioBusy()) {
    pauseLocalRecognition();
  } else if (srResumeAt && static_cast<int32_t>(millis() - srResumeAt) >= 0) {
    srResumeAt = 0;
    resumeLocalRecognition();
  } else if (!complexCaptureArmed) {
    resumeLocalRecognition();
  }

  const int command = pendingSrCommand;
  if (command >= 0) {
    pendingSrCommand = -1;
    processLocalCommand(command);
  }
}

void cleanBeginUtterance(float rms) {
  utteranceActive = true;
  menuWasVisibleBeforeUtterance = menuVisible;
  utteranceId = esp_random();
  utteranceSequence = 0;
  utteranceStartMs = lastSpeechMs = millis();

  StaticJsonDocument<512> doc;
  doc["type"] = "audio_utterance_start";
  doc["request_id"] = utteranceId;
  doc["sample_rate"] = AUDIO_INPUT_SAMPLE_RATE;
  doc["channels"] = 1;
  doc["sample_width"] = 2;
  doc["rms"] = rms;
  doc["menu_was_visible"] = menuWasVisibleBeforeUtterance;
  doc["execution_owner"] = "raspberry-pi";
  doc["wake_already_confirmed"] = true;
  doc["phrase_prefix"] = "killerkoala";
  doc["capture_purpose"] = "complex_ai";
  doc["display_policy"] = "eyes_only";
  doc["local_audio_cue"] = false;
  sendPayload(doc);
}

void cleanEndUtterance(const char *reason) {
  if (!utteranceActive) return;
  StaticJsonDocument<384> doc;
  doc["type"] = "audio_utterance_end";
  doc["request_id"] = utteranceId;
  doc["chunks"] = utteranceSequence;
  doc["reason"] = reason;
  doc["menu_was_visible"] = menuWasVisibleBeforeUtterance;
  doc["wake_already_confirmed"] = true;
  doc["capture_purpose"] = "complex_ai";
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

  size_t count = dualEyeAudioRead(stereoMic, sizeof(stereoMic));
  if (count < 4) return;
  if (millis() - cleanMicrophoneReadyAt < kComplexCaptureWarmupMs) return;

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
  serviceLocalRecognition();
  cleanPollMicrophone();
  updateDisplayTimeouts();
  heartbeat();
  delay(1);
}
