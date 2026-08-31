from __future__ import annotations

from pathlib import Path


OLD_PIPELINE = "freertos_capture_queue_batch6_udp"
NEW_PIPELINE = "freertos_capture_queue_binary_udp_v1"


def _function_span(text: str, signature: str) -> tuple[int, int]:
    start = text.find(signature)
    if start < 0:
        raise RuntimeError(f"binary PCM patch could not find function: {signature}")
    brace = text.find("{", start)
    if brace < 0:
        raise RuntimeError(f"binary PCM patch could not find opening brace: {signature}")
    depth = 0
    for index in range(brace, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return start, index + 1
    raise RuntimeError(f"binary PCM patch could not find closing brace: {signature}")


def apply_binary_pcm_transport(source: Path) -> None:
    text = source.read_text(encoding="utf-8")

    if NEW_PIPELINE in text:
        required = (
            "kVoiceBatchFrames = 2",
            "kVoiceBinaryHeaderBytes = 20",
            "'K', 'P', 'C', 'M'",
            "binary_udp_v1",
        )
        missing = [marker for marker in required if marker not in text]
        if missing:
            raise RuntimeError(f"binary PCM transport marker present but output incomplete: {missing}")
        print("DualEye binary PCM UDP transport already patched")
        return

    if OLD_PIPELINE not in text:
        raise RuntimeError("binary PCM transport expected async PCM pipeline marker")

    count = text.count("constexpr uint8_t kVoiceBatchFrames = 6;")
    if count != 1:
        raise RuntimeError(f"binary PCM transport expected one six-frame batch constant, found {count}")
    text = text.replace(
        "constexpr uint8_t kVoiceBatchFrames = 6;",
        "constexpr uint8_t kVoiceBatchFrames = 2;",
        1,
    )

    base64_size = """constexpr size_t kVoiceBatchBase64Bytes =\n    ((kVoiceBatchPcmBytes + 2U) / 3U) * 4U + 1U;\n"""
    if base64_size not in text:
        raise RuntimeError("binary PCM transport could not find Base64 size buffer declaration")
    text = text.replace(base64_size, "", 1)

    base64_buffer = "char voiceBatchBase64[kVoiceBatchBase64Bytes] = {};\n"
    if base64_buffer not in text:
        raise RuntimeError("binary PCM transport could not find Base64 output buffer")
    text = text.replace(base64_buffer, "", 1)

    write_start, write_end = _function_span(text, "void writeVoicePcmJson(Print &out")
    send_start, send_end = _function_span(text, "bool sendVoicePcmBatch()")
    if write_end > send_start:
        raise RuntimeError("binary PCM transport found unexpected PCM helper ordering")

    replacement = r'''constexpr size_t kVoiceUdpPayloadLimit = 1460;
constexpr size_t kVoiceBinaryHeaderBytes = 20;
static_assert(kVoiceBinaryHeaderBytes + kVoiceBatchPcmBytes <= kVoiceUdpPayloadLimit,
              "binary PCM UDP packet must remain below NetworkUDP's 1460-byte TX buffer");

void putVoiceLe16(uint8_t *out, uint16_t value) {
  out[0] = static_cast<uint8_t>(value & 0xffU);
  out[1] = static_cast<uint8_t>((value >> 8) & 0xffU);
}

void putVoiceLe32(uint8_t *out, uint32_t value) {
  out[0] = static_cast<uint8_t>(value & 0xffU);
  out[1] = static_cast<uint8_t>((value >> 8) & 0xffU);
  out[2] = static_cast<uint8_t>((value >> 16) & 0xffU);
  out[3] = static_cast<uint8_t>((value >> 24) & 0xffU);
}

bool sendVoicePcmBatch() {
  if (!voiceBatchBytes || !voiceBatchFrameCount || !utteranceActive) return true;
  if (voiceBatchBytes > kVoiceBatchPcmBytes ||
      kVoiceBinaryHeaderBytes + voiceBatchBytes > kVoiceUdpPayloadLimit) {
    ++voiceUdpFailures;
    return false;
  }

  float boundedRms = voiceBatchPeakRms;
  if (boundedRms < 0.0f) boundedRms = 0.0f;
  if (boundedRms > 0.999969f) boundedRms = 0.999969f;
  const uint16_t rmsQ15 = static_cast<uint16_t>(boundedRms * 32768.0f);
  const uint32_t sequence = utteranceSequence++;

  uint8_t header[kVoiceBinaryHeaderBytes] = {
      'K', 'P', 'C', 'M',
      1,
      voiceBatchFrameCount,
      voiceBatchSourceChannel,
      0,
  };
  putVoiceLe32(header + 8, utteranceId);
  putVoiceLe32(header + 12, sequence);
  putVoiceLe16(header + 16, static_cast<uint16_t>(voiceBatchBytes));
  putVoiceLe16(header + 18, rmsQ15);

  if (!(wifiReady && piAddress != INADDR_NONE && piPort)) {
    ++voiceUdpFailures;
    return false;
  }

  if (!udp.beginPacket(piAddress, piPort)) {
    ++voiceUdpFailures;
    return false;
  }
  udp.write(header, sizeof(header));
  udp.write(voiceBatchPcm, voiceBatchBytes);
  const bool sent = udp.endPacket() == 1;
  if (!sent) ++voiceUdpFailures;
  return sent;
}
'''

    text = text[:write_start] + replacement + text[send_end:]
    text = text.replace(OLD_PIPELINE, NEW_PIPELINE)

    pipeline_status_anchor = 'doc["pcm_pipeline"] = "freertos_capture_queue_binary_udp_v1";'
    text = text.replace(
        pipeline_status_anchor,
        pipeline_status_anchor + '\n    doc["pcm_wire"] = "binary_udp_v1";',
    )

    required = (
        NEW_PIPELINE,
        "kVoiceBatchFrames = 2",
        "kVoiceBinaryHeaderBytes = 20",
        "kVoiceUdpPayloadLimit = 1460",
        "'K', 'P', 'C', 'M'",
        'doc["pcm_wire"] = "binary_udp_v1";',
        "udp.write(voiceBatchPcm, voiceBatchBytes);",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise RuntimeError(f"binary PCM transport output missing markers: {missing}")
    if "void writeVoicePcmJson(Print &out" in text:
        raise RuntimeError("legacy Base64 JSON PCM writer survived binary transport patch")
    if "mbedtls_base64_encode(\n      reinterpret_cast<unsigned char *>(voiceBatchBase64)" in text:
        raise RuntimeError("legacy async Base64 encoder survived binary transport patch")

    source.write_text(text, encoding="utf-8")
    print(
        "Patched DualEye PCM transport to two-frame 1300-byte binary UDP packets "
        "below NetworkUDP's 1460-byte TX limit"
    )


try:
    Import("env")  # type: ignore[name-defined]  # noqa: F821
    _platformio_env = env  # type: ignore[name-defined]  # noqa: F821
except NameError:
    _platformio_env = None


if _platformio_env is not None:
    project = Path(_platformio_env.subst("$PROJECT_DIR"))
    apply_binary_pcm_transport(project / "src" / "integrated_main_wake_session.cpp")
elif __name__ == "__main__":
    project = Path(__file__).resolve().parents[1]
    apply_binary_pcm_transport(project / "src" / "integrated_main_wake_session.cpp")
