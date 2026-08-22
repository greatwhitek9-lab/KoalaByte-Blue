from __future__ import annotations

import hashlib
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

from .bounded_log import append_jsonl
from .esp32_dualeye_speech_synced_bridge import (
    ESP32DualEyeVoiceBridge as _SpeechSyncedBridge,
    ESP32DualEyeVoiceEvent,
    default_esp32_port,
)
from .killerkoala_error_dig import generate_error_dig

SURVEY_EVENT_TYPES = {
    "wifi_ap_seen",
    "ble_seen",
    "ble_adv_seen",
    "ble_role_status",
}


class ESP32DualEyeVoiceBridge(_SpeechSyncedBridge):
    """Canonical speech-synced bridge with bounded audio and error digs.

    The service is also the exclusive ESP32 serial owner. Passive node survey
    events are written to a bounded privacy-preserving ledger so other runtime
    features never reopen the tty.
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
        self._audio_session_started: dict[str, float] = {}
        self._max_audio_sessions = max(
            1, min(int(os.getenv("KOALABYTE_MAX_AUDIO_SESSIONS", "2")), 4)
        )
        self._audio_session_max_age = max(
            10.0,
            min(float(os.getenv("KOALABYTE_AUDIO_SESSION_MAX_AGE", "45")), 120.0),
        )
        self._node_events_path = Path(
            os.getenv(
                "KOALABYTE_NODE_EVENTS_PATH",
                "logs/runtime/node_events.jsonl",
            )
        )
        self._raw_node_addresses = os.getenv(
            "KOALABYTE_NODE_LOG_RAW_ADDRESSES", "0"
        ).strip().lower() in {"1", "true", "yes", "on"}

    def _log_event(self, event: ESP32DualEyeVoiceEvent) -> None:
        append_jsonl(self.events_path, asdict(event))

    @staticmethod
    def _address_fingerprint(value: str) -> str:
        clean = str(value or "").strip().lower()
        if not clean:
            return ""
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()[:16]

    def _record_survey_payload(self, payload: Dict[str, Any]) -> None:
        clean = dict(payload)
        clean["received_at"] = time.time()
        clean["serial_owner"] = "koalabyte-dualeye-voice-bridge"
        clean["passive_observation"] = True
        clean["raw_addresses_logged"] = self._raw_node_addresses
        for key in ("bssid", "addr", "address"):
            value = str(clean.get(key) or "")
            if not value:
                continue
            clean[f"{key}_fingerprint"] = self._address_fingerprint(value)
            if not self._raw_node_addresses:
                clean[key] = "redacted"
        append_jsonl(self._node_events_path, clean)

    def _drop_audio_session(self, request_id: str, reason: str) -> None:
        existed = request_id in self._audio or request_id in self._audio_meta
        self._audio.pop(request_id, None)
        self._audio_meta.pop(request_id, None)
        self._audio_session_started.pop(request_id, None)
        if existed:
            self._write_json(
                {
                    "type": "voice_rejected",
                    "request_id": request_id,
                    "reason": reason,
                    "resume_menu": False,
                }
            )

    def _prune_audio_sessions(self) -> None:
        now = time.monotonic()
        for request_id, started in list(self._audio_session_started.items()):
            if now - started > self._audio_session_max_age:
                self._drop_audio_session(request_id, "audio_session_timeout")
        while len(self._audio_session_started) > self._max_audio_sessions:
            oldest = min(self._audio_session_started, key=self._audio_session_started.get)
            self._drop_audio_session(oldest, "audio_session_capacity")

    def handle_payload(
        self, payload: Dict[str, Any]
    ) -> Optional[ESP32DualEyeVoiceEvent]:
        payload_type = str(payload.get("type") or "")
        request_id = str(payload.get("request_id") or "")
        if payload_type in SURVEY_EVENT_TYPES:
            self._record_survey_payload(payload)
        if payload_type.startswith("audio_"):
            self._prune_audio_sessions()
        if payload_type == "audio_utterance_start":
            if request_id not in self._audio_session_started:
                while len(self._audio_session_started) >= self._max_audio_sessions:
                    oldest = min(
                        self._audio_session_started,
                        key=self._audio_session_started.get,
                    )
                    self._drop_audio_session(oldest, "audio_session_capacity")
                self._audio_session_started[request_id] = time.monotonic()
        try:
            return super().handle_payload(payload)
        finally:
            if payload_type == "audio_utterance_end":
                self._audio_session_started.pop(request_id, None)

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
        try:
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
            routed_phrase = self._route_confirmed_transcript(
                transcript, meta, payload
            )
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
        finally:
            audio_sessions = getattr(self, "_audio_session_started", None)
            if audio_sessions is not None:
                audio_sessions.pop(request_id, None)

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
