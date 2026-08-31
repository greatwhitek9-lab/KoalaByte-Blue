from __future__ import annotations

from pathlib import Path


def apply_udp_pcm_transport(source: Path) -> None:
    text = source.read_text(encoding="utf-8")

    service_anchor = "void servicePiWakeSttFallback() {"
    if service_anchor not in text:
        raise RuntimeError("UDP PCM transport patch could not find Pi wake/STT fallback service")

    helper = r'''void sendPcmPayload(JsonDocument &doc) {
  String payload;
  serializeJson(doc, payload);
  if (wifiReady && piAddress != INADDR_NONE && piPort) {
    udp.beginPacket(piAddress, piPort);
    udp.write(reinterpret_cast<const uint8_t *>(payload.c_str()), payload.length());
    udp.endPacket();
  } else {
    // USB serial remains a fallback when LAN transport is unavailable, but it
    // cannot sustain 16 kHz PCM once Base64/JSON framing is applied.
    Serial.println(payload);
  }
}

'''

    if "void sendPcmPayload(JsonDocument &doc)" not in text:
        text = text.replace(service_anchor, helper + service_anchor, 1)

    old = '''    doc["source_channel"] = activeChannel;
    sendPayload(doc);
'''
    new = '''    doc["source_channel"] = activeChannel;
    sendPcmPayload(doc);
'''
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"UDP PCM transport patch expected one audio chunk transport anchor, found {count}"
        )
    text = text.replace(old, new, 1)

    required = (
        "void sendPcmPayload(JsonDocument &doc)",
        "udp.beginPacket(piAddress, piPort);",
        "Serial.println(payload);",
        'doc["type"] = "audio_pcm_chunk";',
        "sendPcmPayload(doc);",
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise RuntimeError(f"UDP PCM transport output missing markers: {missing}")

    source.write_text(text, encoding="utf-8")
    print(
        "Patched DualEye PCM stream to use UDP without 115200-baud serial mirroring; "
        "serial retained as offline fallback"
    )


try:
    Import("env")  # type: ignore[name-defined]  # noqa: F821
    _platformio_env = env  # type: ignore[name-defined]  # noqa: F821
except NameError:
    _platformio_env = None


if _platformio_env is not None:
    project = Path(_platformio_env.subst("$PROJECT_DIR"))
    apply_udp_pcm_transport(project / "src" / "integrated_main_wake_session.cpp")
elif __name__ == "__main__":
    project = Path(__file__).resolve().parents[1]
    apply_udp_pcm_transport(project / "src" / "integrated_main_wake_session.cpp")
