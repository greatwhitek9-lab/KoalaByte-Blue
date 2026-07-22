Import("env")

from pathlib import Path

project = Path(env.subst("$PROJECT_DIR"))
source_path = project / "src" / "integrated_main_clean_voice.cpp"
output_path = project / "src" / "integrated_main_wake_session.cpp"
text = source_path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"wake-session source generation expected exactly one {label} anchor, found {count}"
        )
    text = text.replace(old, new, 1)


replace_once(
    """#define beginUtterance koalaLegacyBeginUtterance
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
""",
    """#define handleCommand koalaLegacyHandleCommand
#define pollUdp koalaLegacyPollUdp
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
#undef pollUdp
#undef handleCommand
""",
    "legacy routing block",
)

replace_once(
    "constexpr uint32_t kSrHeartbeatMs = 15000;\n",
    "constexpr uint32_t kSrHeartbeatMs = 15000;\nconstexpr uint32_t kWakeSessionMs = 10000;\n",
    "wake-session timeout constant",
)

replace_once(
    """    {kCmdWake, "Killer Koala"},
    {kCmdWake, "Hey Killer Koala"},
    {kCmdLocalStatus, "Killer Koala status"},
    {kCmdLocalHelp, "Killer Koala help"},
    {kCmdLocalGreeting, "Killer Koala good day"},
    {kCmdLocalThanks, "Killer Koala thank you"},
    {kCmdLocalBanter, "Killer Koala say something funny"},
    {kCmdComplexAi, "Killer Koala ask the AI"},
""",
    """    {kCmdWake, "Killer Koala"},
    {kCmdWake, "Hey Killer Koala"},
    {kCmdLocalStatus, "Status"},
    {kCmdLocalHelp, "Help"},
    {kCmdLocalGreeting, "Good day"},
    {kCmdLocalThanks, "Thank you"},
    {kCmdLocalBanter, "Say something funny"},
    {kCmdComplexAi, "Ask the AI"},
""",
    "base command phrases",
)

replace_once(
    """bool complexCaptureArmed = false;
bool generatedMenuActive = false;
uint32_t complexCaptureArmMs = 0;
""",
    """bool complexCaptureArmed = false;
bool generatedMenuActive = false;
bool wakeSessionActive = false;
uint32_t wakeSessionDeadlineMs = 0;
char wakeSessionReason[48] = "boot";
uint32_t complexCaptureArmMs = 0;
""",
    "wake-session state",
)

replace_once(
    """  doc["sr_ready"] = srReady;
  doc["sr_timeouts"] = pendingSrTimeoutCount;
  doc["mic_ready"] = dualEyeMicrophoneReady();
""",
    """  doc["sr_ready"] = srReady;
  doc["sr_timeouts"] = pendingSrTimeoutCount;
  const uint32_t wakeNow = millis();
  const uint32_t wakeRemaining =
      wakeSessionActive && static_cast<int32_t>(wakeSessionDeadlineMs - wakeNow) > 0
          ? wakeSessionDeadlineMs - wakeNow
          : 0;
  doc["wake_session_active"] = wakeSessionActive;
  doc["wake_session_timeout_ms"] = kWakeSessionMs;
  doc["wake_session_remaining_ms"] = wakeRemaining;
  doc["wake_session_reason"] = wakeSessionReason;
  doc["wake_gate"] = "killerkoala_then_10_second_session";
  doc["ambient_voice_commands_while_sleeping"] = false;
  doc["trusted_pi_input_wakes_session"] = true;
  doc["mic_ready"] = dualEyeMicrophoneReady();
""",
    "voice status diagnostics",
)

replace_once(
    """  sendPayload(doc);
}

void calculateStereoRms(const uint8_t *buffer, size_t length, float &left,
""",
    """  sendPayload(doc);
}

void setWakeSessionReason(const char *reason) {
  copyText(wakeSessionReason, sizeof(wakeSessionReason), reason, "activity");
}

void refreshWakeSession(const char *reason, bool announce = true) {
  wakeSessionActive = true;
  wakeSessionDeadlineMs = millis() + kWakeSessionMs;
  setWakeSessionReason(reason);
  if (announce) {
    emitLocalVoiceStatus("wake_session_active", reason ? reason : "activity");
  }
}

void closeWakeSession(const char *reason) {
  const bool wasActive = wakeSessionActive || generatedMenuActive || menuVisible;
  wakeSessionActive = false;
  wakeSessionDeadlineMs = 0;
  generatedMenuActive = false;
  setWakeSessionReason(reason);
  if (!actionStatusVisible && !dualEyeAudioBusy() && !complexCaptureArmed) {
    showIdleEyes();
  }
  if (wasActive) {
    emitLocalVoiceStatus("wake_session_closed", reason ? reason : "closed");
  }
}

void serviceWakeSessionTimeout() {
  if (!wakeSessionActive) return;
  const uint32_t now = millis();
  if (static_cast<int32_t>(now - wakeSessionDeadlineMs) >= 0) {
    closeWakeSession("ten_second_inactivity_timeout");
  }
}

bool trustedPiMenuActivity(JsonDocument &doc) {
  const char *type = doc["type"] | "";
  const char *source = doc["source"] | "";
  if (strcmp(type, "menu_sync") || strcmp(source, "koalabyte-blue-pi")) {
    return false;
  }
  const char *eventType = doc["event_type"] | "state";
  return strcmp(eventType, "state") && strcmp(eventType, "idle_timeout");
}

void calculateStereoRms(const uint8_t *buffer, size_t length, float &left,
""",
    "wake-session helper insertion",
)

replace_once(
    """  String phrase = "killerkoala launch ";
  phrase += item->label;
""",
    """  String phrase = "launch ";
  phrase += item->label;
""",
    "post-wake launch phrase",
)

replace_once(
    """void processLocalCommand(int commandId, int phraseId) {
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
    default: {
      const GeneratedVoiceRoute *route = generatedVoiceRouteForId(commandId);
      if (route) {
        handleGeneratedVoiceRoute(*route);
      } else {
        emitLocalVoiceStatus("unknown_local_command");
      }
      break;
    }
  }
  if (!complexCaptureArmed) ESP_SR.setMode(SR_MODE_COMMAND);
}
""",
    """void processLocalCommand(int commandId, int phraseId) {
  if (commandId == kCmdWake) {
    refreshWakeSession("killerkoala_wake_phrase");
    emitDetectedCommand(commandId, phraseId);
    playLocalResponse(LocalVoiceCategory::Wake);
    wakeSessionDeadlineMs = millis() + kWakeSessionMs;
    if (!complexCaptureArmed) ESP_SR.setMode(SR_MODE_COMMAND);
    return;
  }

  if (!wakeSessionActive) {
    setWakeSessionReason("ambient_command_rejected_while_sleeping");
    emitLocalVoiceStatus("voice_command_ignored_sleeping", commandName(commandId));
    if (!complexCaptureArmed) ESP_SR.setMode(SR_MODE_COMMAND);
    return;
  }

  refreshWakeSession("accepted_voice_command", false);
  emitDetectedCommand(commandId, phraseId);
  switch (commandId) {
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
    default: {
      const GeneratedVoiceRoute *route = generatedVoiceRouteForId(commandId);
      if (route) {
        handleGeneratedVoiceRoute(*route);
      } else {
        emitLocalVoiceStatus("unknown_local_command");
      }
      break;
    }
  }
  if (wakeSessionActive) wakeSessionDeadlineMs = millis() + kWakeSessionMs;
  if (!complexCaptureArmed) ESP_SR.setMode(SR_MODE_COMMAND);
}
""",
    "voice command dispatcher",
)

replace_once(
    '"recognizer remains in always-on command mode"',
    '"recognizer rearmed; sleeping gate remains active until killerkoala"',
    "timeout status text",
)

replace_once(
    '"wake, K1-K8 and full catalog recognition active"',
    '"sleeping gate or active 10-second session; see wake_session_active"',
    "heartbeat status text",
)

replace_once(
    """void pollSerial() {
""",
    """void handleCommand(const String &line) {
  StaticJsonDocument<1024> gateDoc;
  if (!deserializeJson(gateDoc, line)) {
    const char *type = gateDoc["type"] | "";
    if (trustedPiMenuActivity(gateDoc)) {
      refreshWakeSession("trusted_pi_button_or_keyboard_input", false);
    } else if (!strcmp(type, "menu_sync") && !wakeSessionActive) {
      // A passive Pi state replay must never wake or expose the menu.
      return;
    } else if (!strcmp(type, "trusted_input_activity")) {
      const char *source = gateDoc["source"] | "";
      if (!strcmp(source, "gpio_buttons") || !strcmp(source, "external_keyboard") ||
          !strcmp(source, "koalabyte-blue-pi")) {
        refreshWakeSession(source, false);
      }
    }
  }
  koalaLegacyHandleCommand(line);
}

void pollUdp() {
  if (!wifiReady) return;
  const int packet = udp.parsePacket();
  if (packet <= 0) return;
  String line;
  line.reserve(packet + 1);
  while (udp.available()) line += static_cast<char>(udp.read());
  handleCommand(line);
}

void pollSerial() {
""",
    "trusted command wrapper",
)

replace_once(
    """        if (!strcmp(type, "local_menu_test")) {
          openGeneratedMenu(doc["menu_name"] | "main",
""",
    """        if (!strcmp(type, "local_menu_test")) {
          refreshWakeSession("serial_local_menu_test", false);
          openGeneratedMenu(doc["menu_name"] | "main",
""",
    "local menu test activity",
)

replace_once(
    """  serviceLocalRecognition();
  cleanPollMicrophone();
  updateDisplayTimeouts();
""",
    """  serviceLocalRecognition();
  cleanPollMicrophone();
  serviceWakeSessionTimeout();
  updateDisplayTimeouts();
""",
    "loop wake-session service",
)

banner = """// GENERATED FILE — DO NOT EDIT.
// Source: integrated_main_clean_voice.cpp plus strict KillerKoala wake-session policy.
// Policy: voice commands are discarded while sleeping; KillerKoala opens a
// 10-second session; accepted voice, K1-K8, and external-keyboard activity
// refresh that session; timeout restores animated koala eyes.

"""
output_path.write_text(banner + text, encoding="utf-8")
print(f"Generated strict wake-session source: {output_path}")
