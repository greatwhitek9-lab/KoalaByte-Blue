#!/usr/bin/env python3
from __future__ import annotations

import time

from koalablue.esp32_audio_end_watchdog import install_esp32_audio_end_watchdog


class FakeBridge:
    def __init__(self) -> None:
        self._stt_sessions = {}
        self.handled = []
        self.diags = []
        self._audio_end_grace_seconds = 1.2
        self._audio_end_min_pcm_bytes = 16000

    def _diag(self, event: str, **payload):
        self.diags.append((event, payload))

    def handle_payload(self, payload):
        self.handled.append(dict(payload))
        if payload.get("type") == "audio_utterance_end":
            self._stt_sessions.pop(str(payload.get("request_id") or ""), None)
            return {"event": "voice_command", "request_id": payload.get("request_id")}
        return None

    def read_once(self):
        return None


install_esp32_audio_end_watchdog(FakeBridge)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    now = time.monotonic()

    bridge = FakeBridge()
    bridge._stt_sessions["stale"] = {
        "packets": 50,
        "pcm_bytes": 64000,
        "started": now - 4.0,
        "last_pcm_at": now - 2.0,
    }
    event = bridge.read_once()
    require(event is not None, "quiet buffered utterance was not recovered")
    require(
        any(
            item.get("type") == "audio_utterance_end"
            and item.get("request_id") == "stale"
            and item.get("reason") == "pi_inferred_silence"
            for item in bridge.handled
        ),
        "watchdog did not synthesize the expected utterance-end payload",
    )
    require(
        any(name == "utterance_end_inferred" for name, _payload in bridge.diags),
        "watchdog recovery was not diagnosed",
    )

    recent = FakeBridge()
    recent._stt_sessions["recent"] = {
        "packets": 50,
        "pcm_bytes": 64000,
        "started": now - 2.0,
        "last_pcm_at": time.monotonic(),
    }
    require(recent.read_once() is None, "active PCM session was closed too early")
    require(not recent.handled, "active PCM session generated a false end marker")

    short = FakeBridge()
    short._stt_sessions["short"] = {
        "packets": 4,
        "pcm_bytes": 5120,
        "started": now - 4.0,
        "last_pcm_at": now - 2.0,
    }
    require(short.read_once() is None, "tiny noise capture was incorrectly finalized")
    require(not short.handled, "tiny noise capture generated a false end marker")

    print("ESP32 DualEye audio-end watchdog check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
