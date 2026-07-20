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
            f"two-stage grammar patch expected exactly one {label} anchor, found {count}"
        )
    text = text.replace(old, new, 1)


replace_once(
    """static sr_cmd_t kAllSpeechCommands[kAllSpeechCommandCount];

volatile int pendingSrCommand = -1;
""",
    """static sr_cmd_t kAllSpeechCommands[kAllSpeechCommandCount];

// MultiNet is substantially more reliable when the sleeping recognizer is not
// forced to discriminate the wake phrase from the entire generated menu catalog.
// The full command grammar is loaded only for an active ten-second session.
static const sr_cmd_t kWakeOnlySpeechCommands[] = {
    {kCmdWake, "Killer Koala"},
    {kCmdWake, "Hey Killer Koala"},
};
constexpr size_t kWakeOnlySpeechCommandCount =
    sizeof(kWakeOnlySpeechCommands) / sizeof(kWakeOnlySpeechCommands[0]);

enum class RecognitionGrammar : uint8_t {
  WakeOnly,
  FullSession,
};

RecognitionGrammar activeRecognitionGrammar = RecognitionGrammar::WakeOnly;
RecognitionGrammar requestedRecognitionGrammar = RecognitionGrammar::WakeOnly;
bool recognitionGrammarSwitchPending = false;
void onSrEvent(sr_event_t event, int commandId, int phraseId);

volatile int pendingSrCommand = -1;
""",
    "wake-only command table",
)

replace_once(
    """  doc["multinet_command_count"] = kAllSpeechCommandCount;
  doc["generated_voice_routes"] = kGeneratedVoiceRouteCount;
""",
    """  doc["recognition_grammar"] =
      activeRecognitionGrammar == RecognitionGrammar::WakeOnly
          ? "wake_only"
          : "full_session";
  doc["active_multinet_command_count"] =
      activeRecognitionGrammar == RecognitionGrammar::WakeOnly
          ? kWakeOnlySpeechCommandCount
          : kAllSpeechCommandCount;
  doc["multinet_command_count"] = kAllSpeechCommandCount;
  doc["full_multinet_command_count"] = kAllSpeechCommandCount;
  doc["wake_only_command_count"] = kWakeOnlySpeechCommandCount;
  doc["generated_voice_routes"] = kGeneratedVoiceRouteCount;
""",
    "grammar status diagnostics",
)

replace_once(
    """void refreshWakeSession(const char *reason, bool announce = true) {
  wakeSessionActive = true;
  wakeSessionDeadlineMs = millis() + kWakeSessionMs;
""",
    """void refreshWakeSession(const char *reason, bool announce = true) {
  wakeSessionActive = true;
  wakeSessionDeadlineMs = millis() + kWakeSessionMs;
  requestedRecognitionGrammar = RecognitionGrammar::FullSession;
  if (activeRecognitionGrammar != requestedRecognitionGrammar) {
    recognitionGrammarSwitchPending = true;
  }
""",
    "full-session grammar request",
)

replace_once(
    """  wakeSessionActive = false;
  wakeSessionDeadlineMs = 0;
  generatedMenuActive = false;
""",
    """  wakeSessionActive = false;
  wakeSessionDeadlineMs = 0;
  generatedMenuActive = false;
  requestedRecognitionGrammar = RecognitionGrammar::WakeOnly;
  if (activeRecognitionGrammar != requestedRecognitionGrammar) {
    recognitionGrammarSwitchPending = true;
  }
""",
    "wake-only grammar request",
)

replace_once(
    """void setupLocalRecognition() {
  const uint32_t now = millis();
""",
    """const char *recognitionGrammarName(RecognitionGrammar grammar) {
  return grammar == RecognitionGrammar::WakeOnly ? "wake_only" : "full_session";
}

bool restartRecognitionGrammar(RecognitionGrammar grammar, const char *reason) {
  if (dualEyeAudioBusy() || complexCaptureArmed) return false;

  if (srReady) {
    ESP_SR.end();
    srReady = false;
    srPaused = false;
    delay(30);
  }

  pendingSrCommand = -1;
  pendingSrPhrase = -1;
  const sr_cmd_t *commands = grammar == RecognitionGrammar::WakeOnly
                                 ? kWakeOnlySpeechCommands
                                 : kAllSpeechCommands;
  const size_t commandCount = grammar == RecognitionGrammar::WakeOnly
                                  ? kWakeOnlySpeechCommandCount
                                  : kAllSpeechCommandCount;

  ESP_SR.onEvent(onSrEvent);
  const bool started = ESP_SR.begin(dualEyeAudioBus(), commands, commandCount,
                                    SR_CHANNELS_STEREO, SR_MODE_COMMAND,
                                    srInputFormat);
  if (!started) {
    srNextInitAt = millis() + kSrRetryMs;
    recognitionGrammarSwitchPending = true;
    emitLocalVoiceStatus("local_multinet_grammar_switch_failed",
                         reason ? reason : recognitionGrammarName(grammar));
    return false;
  }

  srReady = true;
  srPaused = false;
  activeRecognitionGrammar = grammar;
  requestedRecognitionGrammar = grammar;
  recognitionGrammarSwitchPending = false;
  lastSrHeartbeatAt = millis();
  emitLocalVoiceStatus(
      grammar == RecognitionGrammar::WakeOnly
          ? "local_multinet_wake_only"
          : "local_multinet_full_session",
      reason ? reason : recognitionGrammarName(grammar));
  return true;
}

void setupLocalRecognition() {
  const uint32_t now = millis();
""",
    "grammar restart helper",
)

replace_once(
    """  prepareSpeechCommandTable();
  ESP_SR.onEvent(onSrEvent);
  srReady = ESP_SR.begin(dualEyeAudioBus(), kAllSpeechCommands,
                         kAllSpeechCommandCount, SR_CHANNELS_STEREO,
                         SR_MODE_COMMAND, srInputFormat);
  if (srReady) {
    lastSrHeartbeatAt = now;
    emitLocalVoiceStatus(
        "local_multinet_ready",
        "William, K1-K8 and generated menu label recognition are active");
  } else {
""",
    """  prepareSpeechCommandTable();
  const sr_cmd_t *commands =
      requestedRecognitionGrammar == RecognitionGrammar::WakeOnly
          ? kWakeOnlySpeechCommands
          : kAllSpeechCommands;
  const size_t commandCount =
      requestedRecognitionGrammar == RecognitionGrammar::WakeOnly
          ? kWakeOnlySpeechCommandCount
          : kAllSpeechCommandCount;
  ESP_SR.onEvent(onSrEvent);
  srReady = ESP_SR.begin(dualEyeAudioBus(), commands, commandCount,
                         SR_CHANNELS_STEREO, SR_MODE_COMMAND, srInputFormat);
  if (srReady) {
    activeRecognitionGrammar = requestedRecognitionGrammar;
    recognitionGrammarSwitchPending = false;
    lastSrHeartbeatAt = now;
    emitLocalVoiceStatus(
        activeRecognitionGrammar == RecognitionGrammar::WakeOnly
            ? "local_multinet_wake_only"
            : "local_multinet_full_session",
        activeRecognitionGrammar == RecognitionGrammar::WakeOnly
            ? "two wake phrases loaded while sleeping"
            : "post-wake K1-K8 and generated menu grammar loaded");
  } else {
""",
    "initial grammar selection",
)

replace_once(
    """void serviceLocalRecognition() {
  setupLocalRecognition();
  if (!srReady) return;

  const uint32_t now = millis();
""",
    """void serviceLocalRecognition() {
  setupLocalRecognition();
  if (!srReady) return;

  const uint32_t now = millis();
  const bool resumeGuardActive =
      srResumeAt && static_cast<int32_t>(srResumeAt - now) > 0;
  if (recognitionGrammarSwitchPending && !dualEyeAudioBusy() &&
      !complexCaptureArmed && !resumeGuardActive) {
    if (!restartRecognitionGrammar(requestedRecognitionGrammar,
                                   wakeSessionActive
                                       ? "wake_session_grammar_enabled"
                                       : "sleeping_wake_only_grammar_enabled")) {
      return;
    }
  }
""",
    "grammar switch service",
)

banner = """// TWO-STAGE MULTINET GRAMMAR PATCHED AT BUILD TIME.
// Sleeping: only Killer Koala / Hey Killer Koala are loaded.
// Awake: full post-wake menu grammar is loaded for the active session.

"""
path.write_text(banner + text, encoding="utf-8")
print(f"Patched two-stage wake/full MultiNet grammar: {path}")
