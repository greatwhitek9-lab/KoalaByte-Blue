#!/usr/bin/env python3
from __future__ import annotations

import queue

from koalablue.esp32_unconfirmed_stt_fastpath import (
    install_esp32_unconfirmed_stt_fastpath,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


class DummyBridge:
    def __init__(self) -> None:
        self._audio = {}
        self._audio_meta = {}
        self._last_stt_search = "none"
        self._last_stt_transcript = ""
        self.events = queue.Queue()
        self.grammar_calls = 0
        self.full_calls = 0
        self.writes = []
        self.logged = []
        self.diags = []
        self.grammar_result = ""

    def _finish_audio(self, payload):
        self.full_calls += 1
        return "full-recognizer-path"

    def _transcribe_with_command_grammar(self, pcm, sample_rate, sample_width):
        self.grammar_calls += 1
        return self.grammar_result

    def _write_json(self, payload):
        self.writes.append(dict(payload))

    def _fanout_face(self, *_args, **_kwargs):
        return None

    def _log_event(self, event):
        self.logged.append(event)

    def _diag(self, event, **payload):
        self.diags.append({"event": event, **payload})


def seed(bridge: DummyBridge, request_id: str, *, confirmed: bool) -> None:
    bridge._audio[request_id] = bytearray(b"\x00\x00" * 16000)
    bridge._audio_meta[request_id] = {
        "sample_rate": 16000,
        "sample_width": 2,
        "wake_already_confirmed": confirmed,
    }


def main() -> int:
    install_esp32_unconfirmed_stt_fastpath(DummyBridge)

    bridge = DummyBridge()
    bridge.grammar_result = "killer koala menu"
    seed(bridge, "one", confirmed=False)
    event = bridge._finish_audio({"request_id": "one", "reason": "silence"})
    require(event is not None, "valid unconfirmed JSGF command was rejected")
    require(bridge.grammar_calls == 1, "unconfirmed command did not use JSGF")
    require(bridge.full_calls == 0, "unconfirmed command entered full STT stack")
    require(event.phrase == "killer koala menu", f"wrong routed phrase: {event.phrase}")

    bridge.grammar_result = ""
    seed(bridge, "two", confirmed=False)
    event = bridge._finish_audio({"request_id": "two", "reason": "silence"})
    require(event is None, "ambient grammar miss should be rejected")
    require(bridge.full_calls == 0, "ambient grammar miss entered full STT stack")
    require(
        bridge.writes[-1].get("reason") == "unconfirmed_command_grammar_no_match",
        "ambient miss did not record fast rejection",
    )

    seed(bridge, "three", confirmed=True)
    result = bridge._finish_audio({"request_id": "three", "reason": "silence"})
    require(result == "full-recognizer-path", "confirmed wake lost full STT path")
    require(bridge.full_calls == 1, "confirmed wake did not use full STT stack")

    print("ESP32 unconfirmed STT fastpath check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
