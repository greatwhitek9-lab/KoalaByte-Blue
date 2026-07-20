#pragma once
#include <Arduino.h>

enum class LocalVoiceCategory : uint8_t {
  Wake = 0,
  Status,
  Help,
  Greeting,
  Thanks,
  Banter,
  Escalate,
  Count
};

// Plays one rotating embedded response entirely on the ESP32-S3 speaker.
// Audio is generated into the firmware at build time and requires no Pi or network.
bool localVoicePlayResponse(LocalVoiceCategory category,
                            const char **selectedText = nullptr);
size_t localVoiceResponseCount(LocalVoiceCategory category);
