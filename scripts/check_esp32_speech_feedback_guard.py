#!/usr/bin/env python3
from __future__ import annotations

from koalablue.esp32_speech_feedback_guard import install_esp32_speech_feedback_guard


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


class FakeBridge:
    def __init__(self) -> None:
        self.delivered: list[dict] = []
        self.diagnostics: list[tuple[str, dict]] = []

    def _diag(self, event: str, **payload) -> None:
        self.diagnostics.append((event, payload))

    def handle_payload(self, payload: dict):
        self.delivered.append(dict(payload))
        return payload

    def _play_response(self, text: str, channel: str) -> None:
        # Simulate the ESP32 microphone hearing the Pi speaker while William talks.
        self.handle_payload({"type": "audio_utterance_start", "request_id": "echo-1"})
        self.handle_payload(
            {
                "type": "audio_pcm_chunk",
                "request_id": "echo-1",
                "_pcm_s16le_mono": b"\x00\x00" * 640,
            }
        )
        self.handle_payload({"type": "audio_utterance_end", "request_id": "echo-1"})


def main() -> int:
    install_esp32_speech_feedback_guard(FakeBridge)
    bridge = FakeBridge()

    bridge._play_response("Test William response", "pi-test")
    require(not bridge.delivered, "speaker feedback reached the underlying STT path")
    require(
        any(event == "audio_feedback_suppressed" for event, _ in bridge.diagnostics),
        "speaker feedback suppression was not diagnosed",
    )

    # A new request during the post-speech tail must also be suppressed.
    bridge.handle_payload({"type": "audio_utterance_start", "request_id": "echo-2"})
    require(not bridge.delivered, "post-speech cooldown failed to suppress microphone input")

    # After the explicit cooldown boundary, normal microphone traffic resumes.
    bridge._koalabyte_pi_speech_cooldown_until = 0.0
    bridge.handle_payload({"type": "audio_utterance_start", "request_id": "real-1"})
    require(
        bridge.delivered and bridge.delivered[-1].get("request_id") == "real-1",
        "normal microphone traffic did not resume after speech cooldown",
    )

    print("ESP32 speech feedback guard check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
