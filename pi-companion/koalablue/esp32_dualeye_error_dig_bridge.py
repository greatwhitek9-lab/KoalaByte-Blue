from __future__ import annotations

import os
import time
from typing import Any

from .esp32_dualeye_speech_synced_bridge import (
    ESP32DualEyeVoiceBridge as _SpeechSyncedBridge,
    ESP32DualEyeVoiceEvent,
    default_esp32_port,
)
from .killerkoala_error_dig import generate_error_dig


class ESP32DualEyeVoiceBridge(_SpeechSyncedBridge):
    """Canonical speech-synced bridge with generated, non-abusive error digs.

    The parent bridge owns the asynchronous alarm lifecycle, Heltec/ESP32 fanout,
    explicit error clear, mouth recovery, and Pi-speaker playback. This subclass
    replaces its fixed error-line list with the local Pi companion generator and
    suppresses raw exception speech for every Pi-owned failure path.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._error_sequence_seconds = max(
            0.6,
            min(
                float(
                    os.getenv(
                        "KOALABYTE_ERROR_ALARM_SECONDS",
                        os.getenv("KILLERKOALA_ERROR_SEQUENCE_SECONDS", "2.2"),
                    )
                ),
                8.0,
            ),
        )
        self._pending_failure_face = False

    def _select_error_dig(self, action: str, message: str) -> str:
        dig = generate_error_dig(action, message)
        self._error_dig_history.append(dig)
        self._error_dig_history = self._error_dig_history[-8:]
        return dig

    def _fanout_face(
        self, state: str, message: str = "", duration_ms: int = 5000
    ) -> None:
        normalized = str(state or "").strip().lower()
        if normalized in {
            "error",
            "alarmed",
            "fault",
            "exception",
            "disappointed",
            "angry",
        }:
            self._pending_failure_face = True
            if not self._active_error:
                self._active_error = True
                self._error_alarm_until = time.time() + self._error_sequence_seconds
                self._pending_error_dig = self._select_error_dig(
                    "KillerKoala action",
                    message or normalized,
                )
        super()._fanout_face(state, message, duration_ms)

    def _play_response(self, text: str, channel: str) -> None:
        # Never read a raw exception, traceback, or failed command result aloud.
        # The canonical timed service clears the alarm and speaks the generated
        # dig through the Pi speaker on the dedicated pi-error-dig channel.
        if (
            str(channel or "").startswith("pi-")
            and channel != "pi-error-dig"
            and (self._active_error or self._pending_failure_face)
        ):
            return
        super()._play_response(text, channel)
        if channel == "pi-error-dig":
            self._pending_failure_face = False


__all__ = [
    "ESP32DualEyeVoiceBridge",
    "ESP32DualEyeVoiceEvent",
    "default_esp32_port",
]
