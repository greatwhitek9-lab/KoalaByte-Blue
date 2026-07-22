from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

from .esp32_dualeye_speech_synced_bridge import (
    ESP32DualEyeVoiceBridge as _SpeechSyncedBridge,
    ESP32DualEyeVoiceEvent,
    default_esp32_port,
)
from .killerkoala_error_dig import generate_error_dig


class ESP32DualEyeVoiceBridge(_SpeechSyncedBridge):
    """Canonical speech-synced bridge with generated error digs.

    The parent bridge owns alarm lifecycle, display fanout, mouth recovery, and
    Pi-speaker playback. This subclass also accepts complex follow-up audio from
    an ESP32 wake session without requiring the operator to repeat KillerKoala.
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

    @staticmethod
    def _wake_confirmed(meta: Dict[str, Any], payload: Dict[str, Any]) -> bool:
        return bool(
            meta.get("wake_already_confirmed")
            or payload.get("wake_already_confirmed")
            or meta.get("capture_purpose") == "complex_ai"
        )

    @staticmethod
    def _route_confirmed_transcript(
        transcript: str, meta: Dict[str, Any], payload: Dict[str, Any]
    ) -> str:
        clean = " ".join(str(transcript or "").split())
        normalized = clean.lower().replace("killer koala", "killerkoala")
        if normalized.startswith("killerkoala") or normalized.startswith(
            "hey killerkoala"
        ):
            return clean
        prefix = " ".join(
            str(
                meta.get("phrase_prefix")
                or payload.get("phrase_prefix")
                or "killerkoala"
            ).split()
        )
        return f"{prefix} {clean}".strip()

    def _finish_audio(
        self, payload: Dict[str, Any]
    ) -> Optional[ESP32DualEyeVoiceEvent]:
        request_id = str(payload.get("request_id", ""))
        meta_preview = dict(self._audio_meta.get(request_id, {}))
        if not self._wake_confirmed(meta_preview, payload):
            return super()._finish_audio(payload)

        pcm = bytes(self._audio.pop(request_id, b""))
        meta = self._audio_meta.pop(request_id, {})
        transcript = self._transcribe_pcm(
            pcm,
            int(meta.get("sample_rate", 16000)),
            int(meta.get("sample_width", 2)),
        )
        resume_menu = bool(
            meta.get("menu_was_visible", payload.get("menu_was_visible", False))
        )
        if not transcript:
            self._write_json(
                {
                    "type": "voice_rejected",
                    "request_id": request_id,
                    "reason": "speech_not_understood",
                    "wake_already_confirmed": True,
                    "resume_menu": resume_menu,
                }
            )
            return None

        routed_phrase = self._route_confirmed_transcript(transcript, meta, payload)
        self._fanout_face("wake", "wake session confirmed", 1200)
        event_payload: Dict[str, Any] = {
            **meta,
            **payload,
            "transcript": transcript,
            "routed_phrase": routed_phrase,
            "wake_already_confirmed": True,
            "wake_word_injected_for_routing": routed_phrase != transcript,
        }
        event = ESP32DualEyeVoiceEvent(
            type="voice_command",
            phrase=routed_phrase,
            source="esp32_s3_es7210_confirmed_wake_followup",
            request_id=request_id,
            payload=event_payload,
        )
        self.events.put(event)
        self._log_event(event)
        return event

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
