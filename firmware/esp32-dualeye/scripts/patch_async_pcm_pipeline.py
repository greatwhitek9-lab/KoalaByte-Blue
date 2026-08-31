from __future__ import annotations

from pathlib import Path


ASYNC_MARKER = "freertos_capture_queue_batch6_udp"


def _function_span(text: str, signature: str) -> tuple[int, int]:
    start = text.find(signature)
    if start < 0:
        raise RuntimeError(f"async PCM patch could not find function: {signature}")
    brace = text.find("{", start)
    if brace < 0:
        raise RuntimeError(f"async PCM patch could not find opening brace: {signature}")

    depth = 0
    for index in range(brace, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return start, index + 1
    raise RuntimeError(f"async PCM patch could not find closing brace: {signature}")


def apply_async_pcm_pipeline(source: Path) -> None:
    text = source.read_text(encoding="utf-8")

    if ASYNC_MARKER in text:
        if text.count(ASYNC_MARKER) < 1:
            raise RuntimeError("async PCM pipeline marker validation failed")
        print("DualEye async PCM capture/UDP batching pipeline already patched")
        return

    includes = (
        "#include <freertos/FreeRTOS.h>\n"
        "#include <freertos/queue.h>\n"
        "#include <freertos/task.h>\n"
    )
    if "#include <freertos/queue.h>" not in text:
        text = includes + text

    send_start, send_end = _function_span(text, "void sendPcmPayload(JsonDocument &doc)")
    service_start, service_end = _function_span(text, "void servicePiWakeSttFallback()")
    if send_end > service_start:
        raise RuntimeError("async PCM patch found unexpected helper/function ordering")

    replacement = r'''constexpr uint8_t kVoiceBatchFrames = 6;
constexpr uint8_t kVoiceQueueFrames = 36;
constexpr uint32_t kVoicePipelineStatusMs = 5000;
constexpr size_t kVoiceBatchPcmBytes =
    static_cast<size_t>(MIC_PCM_CHUNK_BYTES) * kVoiceBatchFrames;
constexpr size_t kVoiceBatchBase64Bytes =
    ((kVoiceBatchPcmBytes + 2U) / 3U) * 4U + 1U;

struct VoicePcmFrame {
  uint16_t bytes;
  float rms;
  uint8_t sourceChannel;
  uint32_t capturedAtMs;
  uint8_t pcm[MIC_PCM_CHUNK_BYTES];
};

QueueHandle_t voicePcmQueue = nullptr;
TaskHandle_t voiceCaptureTaskHandle = nullptr;
volatile uint32_t voiceCaptureFrames = 0;
volatile uint32_t voiceQueueDrops = 0;
uint32_t voiceEncodeFailures = 0;
uint32_t voiceUdpFailures = 0;
uint8_t voiceBatchPcm[kVoiceBatchPcmBytes] = {};
char voiceBatchBase64[kVoiceBatchBase64Bytes] = {};
size_t voiceBatchBytes = 0;
uint8_t voiceBatchFrameCount = 0;
float voiceBatchPeakRms = 0.0f;
uint8_t voiceBatchSourceChannel = 0;
uint32_t lastVoicePipelineStatusAt = 0;

void voiceCaptureTask(void *) {
  uint8_t stereo[MIC_PCM_CHUNK_BYTES * 2] = {};
  VoicePcmFrame frame = {};

  for (;;) {
    if (!dualEyeMicrophoneReady() || dualEyeAudioBusy()) {
      vTaskDelay(pdMS_TO_TICKS(5));
      continue;
    }

    const size_t count = dualEyeAudioRead(stereo, sizeof(stereo));
    if (count < 4) {
      vTaskDelay(pdMS_TO_TICKS(1));
      continue;
    }

    const int16_t *samples = reinterpret_cast<const int16_t *>(stereo);
    const size_t frames = min(count / 4, sizeof(frame.pcm) / sizeof(int16_t));
    if (!frames) continue;

    double leftSquareSum = 0.0;
    double rightSquareSum = 0.0;
    for (size_t index = 0; index < frames; ++index) {
      const float left = samples[index * 2] / 32768.0f;
      const float right = samples[index * 2 + 1] / 32768.0f;
      leftSquareSum += left * left;
      rightSquareSum += right * right;
    }

    const float leftRms = sqrt(leftSquareSum / frames);
    const float rightRms = sqrt(rightSquareSum / frames);
    frame.sourceChannel = rightRms > leftRms ? 1 : 0;
    frame.rms = frame.sourceChannel ? rightRms : leftRms;
    frame.capturedAtMs = millis();
    frame.bytes = static_cast<uint16_t>(frames * sizeof(int16_t));

    int16_t *mono = reinterpret_cast<int16_t *>(frame.pcm);
    for (size_t index = 0; index < frames; ++index) {
      mono[index] = samples[index * 2 + frame.sourceChannel];
    }

    if (voicePcmQueue) {
      if (xQueueSend(voicePcmQueue, &frame, 0) != pdTRUE) {
        VoicePcmFrame discarded = {};
        if (xQueueReceive(voicePcmQueue, &discarded, 0) == pdTRUE) {
          ++voiceQueueDrops;
        }
        if (xQueueSend(voicePcmQueue, &frame, 0) != pdTRUE) {
          ++voiceQueueDrops;
        }
      }
      ++voiceCaptureFrames;
    }
  }
}

bool ensureVoicePcmPipeline() {
  if (!voicePcmQueue) {
    voicePcmQueue = xQueueCreate(kVoiceQueueFrames, sizeof(VoicePcmFrame));
    if (!voicePcmQueue) return false;
  }

  if (!voiceCaptureTaskHandle) {
    const BaseType_t created = xTaskCreatePinnedToCore(
        voiceCaptureTask, "DualEyePcmCapture", 6144, nullptr, 3,
        &voiceCaptureTaskHandle, 1);
    if (created != pdPASS) {
      voiceCaptureTaskHandle = nullptr;
      vQueueDelete(voicePcmQueue);
      voicePcmQueue = nullptr;
      return false;
    }
  }
  return true;
}

void writeVoicePcmJson(Print &out, uint32_t requestId, uint32_t sequence,
                       size_t encodedLength, float rms, uint8_t sourceChannel,
                       uint8_t batchFrames, size_t pcmBytes) {
  out.print(F("{\"type\":\"audio_pcm_chunk\",\"request_id\":"));
  out.print(requestId);
  out.print(F(",\"sequence\":"));
  out.print(sequence);
  out.print(F(",\"pcm_s16le_mono_b64\":\""));
  out.write(reinterpret_cast<const uint8_t *>(voiceBatchBase64), encodedLength);
  out.print(F("\",\"rms\":"));
  out.print(rms, 6);
  out.print(F(",\"source_channel\":"));
  out.print(sourceChannel);
  out.print(F(",\"batch_frames\":"));
  out.print(batchFrames);
  out.print(F(",\"pcm_bytes\":"));
  out.print(pcmBytes);
  out.print(F(",\"pcm_pipeline\":\"freertos_capture_queue_batch6_udp\"}"));
}

bool sendVoicePcmBatch() {
  if (!voiceBatchBytes || !voiceBatchFrameCount || !utteranceActive) return true;

  size_t encodedLength = 0;
  const int encoded = mbedtls_base64_encode(
      reinterpret_cast<unsigned char *>(voiceBatchBase64),
      sizeof(voiceBatchBase64) - 1, &encodedLength, voiceBatchPcm,
      voiceBatchBytes);
  if (encoded != 0) {
    ++voiceEncodeFailures;
    return false;
  }
  voiceBatchBase64[encodedLength] = 0;

  const uint32_t sequence = utteranceSequence++;
  bool sent = true;
  if (wifiReady && piAddress != INADDR_NONE && piPort) {
    if (!udp.beginPacket(piAddress, piPort)) {
      sent = false;
    } else {
      writeVoicePcmJson(udp, utteranceId, sequence, encodedLength,
                        voiceBatchPeakRms, voiceBatchSourceChannel,
                        voiceBatchFrameCount, voiceBatchBytes);
      sent = udp.endPacket() == 1;
    }
    if (!sent) ++voiceUdpFailures;
  } else {
    // Best-effort USB fallback. Continuous 16 kHz voice requires the UDP path;
    // serial remains useful for diagnostics and low-rate control traffic.
    writeVoicePcmJson(Serial, utteranceId, sequence, encodedLength,
                      voiceBatchPeakRms, voiceBatchSourceChannel,
                      voiceBatchFrameCount, voiceBatchBytes);
    Serial.println();
  }
  return sent;
}

void resetVoicePcmBatch() {
  voiceBatchBytes = 0;
  voiceBatchFrameCount = 0;
  voiceBatchPeakRms = 0.0f;
  voiceBatchSourceChannel = 0;
}

void flushVoicePcmBatch() {
  if (voiceBatchBytes && utteranceActive) sendVoicePcmBatch();
  resetVoicePcmBatch();
}

void appendVoicePcmFrame(const VoicePcmFrame &frame) {
  if (!frame.bytes || frame.bytes > MIC_PCM_CHUNK_BYTES) return;
  if (voiceBatchBytes + frame.bytes > sizeof(voiceBatchPcm)) flushVoicePcmBatch();
  if (voiceBatchBytes + frame.bytes > sizeof(voiceBatchPcm)) return;

  memcpy(voiceBatchPcm + voiceBatchBytes, frame.pcm, frame.bytes);
  voiceBatchBytes += frame.bytes;
  ++voiceBatchFrameCount;
  if (frame.rms >= voiceBatchPeakRms) {
    voiceBatchPeakRms = frame.rms;
    voiceBatchSourceChannel = frame.sourceChannel;
  }
  if (voiceBatchFrameCount >= kVoiceBatchFrames) flushVoicePcmBatch();
}

void servicePiWakeSttFallback() {
  static bool announced = false;
  static uint32_t lastMicLevelStatusAt = 0;
  static float latestRms = 0.0f;
  static uint8_t latestChannel = 0;

  const uint32_t now = millis();
  if (!dualEyeMicrophoneReady()) return;

  if (!ensureVoicePcmPipeline()) {
    if (now - lastVoicePipelineStatusAt >= kVoicePipelineStatusMs) {
      lastVoicePipelineStatusAt = now;
      StaticJsonDocument<512> doc;
      doc["type"] = "mic_capture_probe";
      doc["device"] = "esp32-s3-dualeye";
      doc["fw"] = KOALABLUE_FW_VERSION;
      doc["status"] = "async_pcm_pipeline_alloc_failed";
      doc["pcm_pipeline"] = "freertos_capture_queue_batch6_udp";
      doc["free_heap"] = ESP.getFreeHeap();
      sendPayload(doc);
    }
    return;
  }

  if (!announced) {
    announced = true;
    StaticJsonDocument<1024> doc;
    doc["type"] = "local_voice_status";
    doc["device"] = "esp32-s3-dualeye";
    doc["status"] = "pi_wake_stt_fallback_ready";
    doc["detail"] =
        "ESP-SR quarantined; continuous ES7210 capture queued independently from batched UDP STT transport";
    doc["recognizer"] = "raspberry-pi-stt";
    doc["wake_phrase"] = "killer koala";
    doc["alternate_wake_phrase"] = "hey killer koala";
    doc["sr_ready"] = false;
    doc["mic_ready"] = true;
    doc["speaker_ready"] = dualEyeSpeakerReady();
    doc["audio_status"] = dualEyeAudioStatus();
    doc["pi_wake_stt_fallback"] = true;
    doc["pcm_pipeline"] = "freertos_capture_queue_batch6_udp";
    doc["pcm_batch_frames"] = kVoiceBatchFrames;
    doc["pcm_queue_frames"] = kVoiceQueueFrames;
    doc["free_heap"] = ESP.getFreeHeap();
    sendPayload(doc);
  }

  if (dualEyeAudioBusy()) {
    resetVoicePcmBatch();
    if (voicePcmQueue) xQueueReset(voicePcmQueue);
    return;
  }

  VoicePcmFrame frame = {};
  uint8_t processed = 0;
  while (processed < 24 && xQueueReceive(voicePcmQueue, &frame, 0) == pdTRUE) {
    ++processed;
    latestRms = frame.rms;
    latestChannel = frame.sourceChannel;

    if (!utteranceActive && frame.rms >= MIC_WAKE_RMS_THRESHOLD) {
      resetVoicePcmBatch();
      koalaLegacyBeginUtterance(frame.rms);
    }

    if (!utteranceActive) continue;

    if (frame.rms >= MIC_WAKE_RMS_THRESHOLD * 0.55f) {
      lastSpeechMs = millis();
    }
    appendVoicePcmFrame(frame);

    if (millis() - utteranceStartMs >= MIC_UTTERANCE_MAX_MS) {
      flushVoicePcmBatch();
      koalaLegacyEndUtterance("max_duration");
    } else if (millis() - lastSpeechMs >= MIC_UTTERANCE_SILENCE_MS) {
      flushVoicePcmBatch();
      koalaLegacyEndUtterance("silence");
    }
  }

  if (utteranceActive) {
    if (millis() - utteranceStartMs >= MIC_UTTERANCE_MAX_MS) {
      flushVoicePcmBatch();
      koalaLegacyEndUtterance("max_duration");
    } else if (millis() - lastSpeechMs >= MIC_UTTERANCE_SILENCE_MS) {
      flushVoicePcmBatch();
      koalaLegacyEndUtterance("silence");
    }
  }

  if (!utteranceActive && now - lastMicLevelStatusAt >= MIC_STATUS_INTERVAL_MS) {
    lastMicLevelStatusAt = now;
    StaticJsonDocument<640> doc;
    doc["type"] = "mic_level_status";
    doc["device"] = "esp32-s3-dualeye";
    doc["fw"] = KOALABLUE_FW_VERSION;
    doc["active_mic_channel"] = latestChannel;
    doc["trigger_rms"] = latestRms;
    doc["threshold"] = MIC_WAKE_RMS_THRESHOLD;
    doc["audio_busy"] = false;
    doc["pcm_pipeline"] = "freertos_capture_queue_batch6_udp";
    doc["pcm_queue_depth"] =
        voicePcmQueue ? static_cast<uint32_t>(uxQueueMessagesWaiting(voicePcmQueue)) : 0;
    doc["pcm_queue_drops"] = static_cast<uint32_t>(voiceQueueDrops);
    sendPayload(doc);
  }

  if (now - lastVoicePipelineStatusAt >= kVoicePipelineStatusMs) {
    lastVoicePipelineStatusAt = now;
    StaticJsonDocument<768> doc;
    doc["type"] = "fallback_entry_probe";
    doc["device"] = "esp32-s3-dualeye";
    doc["fw"] = KOALABLUE_FW_VERSION;
    doc["mic_ready"] = dualEyeMicrophoneReady();
    doc["speaker_ready"] = dualEyeSpeakerReady();
    doc["audio_busy"] = dualEyeAudioBusy();
    doc["audio_status"] = dualEyeAudioStatus();
    doc["audio_read_attempts"] = dualEyeAudioReadAttempts();
    doc["audio_last_read_state"] = dualEyeAudioLastReadState();
    doc["audio_last_read_bytes"] = dualEyeAudioLastReadBytes();
    doc["audio_last_raw_read_bytes"] = dualEyeAudioLastRawReadBytes();
    doc["audio_input_slots"] = dualEyeAudioInputSlots();
    doc["audio_last_read_duration_ms"] = dualEyeAudioLastReadDurationMs();
    doc["pcm_pipeline"] = "freertos_capture_queue_batch6_udp";
    doc["pcm_batch_frames"] = kVoiceBatchFrames;
    doc["pcm_queue_depth"] =
        voicePcmQueue ? static_cast<uint32_t>(uxQueueMessagesWaiting(voicePcmQueue)) : 0;
    doc["pcm_queue_drops"] = static_cast<uint32_t>(voiceQueueDrops);
    doc["pcm_capture_frames"] = static_cast<uint32_t>(voiceCaptureFrames);
    doc["pcm_encode_failures"] = voiceEncodeFailures;
    doc["pcm_udp_failures"] = voiceUdpFailures;
    doc["free_heap"] = ESP.getFreeHeap();
    sendPayload(doc);
  }
}
'''

    text = text[:send_start] + replacement + text[service_end:]

    required = (
        ASYNC_MARKER,
        "xTaskCreatePinnedToCore(",
        "xQueueCreate(kVoiceQueueFrames",
        "kVoiceBatchFrames = 6",
        "appendVoicePcmFrame(frame);",
        'doc["pcm_queue_drops"]',
        "servicePiWakeSttFallback()",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise RuntimeError(f"async PCM pipeline output missing markers: {missing}")
    if "void sendPcmPayload(JsonDocument &doc)" in text:
        raise RuntimeError("legacy synchronous PCM helper remains after async patch")

    source.write_text(text, encoding="utf-8")
    print(
        "Patched DualEye voice PCM with continuous FreeRTOS capture queue and "
        "six-frame batched UDP transport"
    )


try:
    Import("env")  # type: ignore[name-defined]  # noqa: F821
    _platformio_env = env  # type: ignore[name-defined]  # noqa: F821
except NameError:
    _platformio_env = None


if _platformio_env is not None:
    project = Path(_platformio_env.subst("$PROJECT_DIR"))
    apply_async_pcm_pipeline(project / "src" / "integrated_main_wake_session.cpp")
elif __name__ == "__main__":
    project = Path(__file__).resolve().parents[1]
    apply_async_pcm_pipeline(project / "src" / "integrated_main_wake_session.cpp")
