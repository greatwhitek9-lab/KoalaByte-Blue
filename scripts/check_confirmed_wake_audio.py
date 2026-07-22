#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
for path in (ROOT, PI_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from koalablue.esp32_dualeye_error_dig_bridge import (  # noqa: E402
    ESP32DualEyeVoiceBridge,
)


def make_bridge(transcript: str) -> tuple[ESP32DualEyeVoiceBridge, list[dict[str, Any]]]:
    bridge = ESP32DualEyeVoiceBridge(port="/dev/null")
    writes: list[dict[str, Any]] = []
    bridge._transcribe_pcm = (  # type: ignore[method-assign]
        lambda _pcm, _sample_rate, _sample_width: transcript
    )
    bridge._write_json = lambda payload, **_kwargs: writes.append(dict(payload))  # type: ignore[method-assign]
    bridge._fanout_face = lambda *_args, **_kwargs: None  # type: ignore[method-assign]
    bridge._log_event = lambda _event: None  # type: ignore[method-assign]
    return bridge, writes


def main() -> int:
    request_id = "confirmed-wake-regression"
    bridge, writes = make_bridge("what is the current system status")
    bridge._audio[request_id] = bytearray(b"\x00\x00" * 320)
    bridge._audio_meta[request_id] = {
        "sample_rate": 16000,
        "sample_width": 2,
        "wake_already_confirmed": True,
        "phrase_prefix": "killerkoala",
        "capture_purpose": "complex_ai",
        "menu_was_visible": False,
    }
    event = bridge._finish_audio(
        {
            "request_id": request_id,
            "wake_already_confirmed": True,
            "capture_purpose": "complex_ai",
        }
    )
    assert event is not None
    assert event.phrase == "killerkoala what is the current system status"
    assert event.payload["transcript"] == "what is the current system status"
    assert event.payload["wake_already_confirmed"] is True
    assert event.payload["wake_word_injected_for_routing"] is True
    assert not any(payload.get("type") == "voice_rejected" for payload in writes)

    repeated, repeated_writes = make_bridge("killerkoala run diagnostics")
    repeated_id = "already-prefixed"
    repeated._audio[repeated_id] = bytearray(b"\x00\x00" * 320)
    repeated._audio_meta[repeated_id] = {
        "sample_rate": 16000,
        "sample_width": 2,
        "wake_already_confirmed": True,
        "phrase_prefix": "killerkoala",
    }
    repeated_event = repeated._finish_audio(
        {"request_id": repeated_id, "wake_already_confirmed": True}
    )
    assert repeated_event is not None
    assert repeated_event.phrase == "killerkoala run diagnostics"
    assert repeated_event.payload["wake_word_injected_for_routing"] is False
    assert not repeated_writes

    payload = {
        "status": "CONFIRMED_WAKE_AUDIO_READY",
        "confirmed_followup_without_repeated_wake": True,
        "routing_prefix_injected_once": True,
        "already_prefixed_transcript_preserved": True,
        "hardware_accessed": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
