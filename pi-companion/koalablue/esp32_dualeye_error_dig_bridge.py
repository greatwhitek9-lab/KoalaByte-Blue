from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .esp32_dualeye_speech_synced_bridge import (
    ESP32DualEyeVoiceBridge as _SpeechSyncedBridge,
    ESP32DualEyeVoiceEvent,
    default_esp32_port,
)
from .killerkoala_error_dig import error_details, generate_error_dig, is_error_result


class ESP32DualEyeVoiceBridge(_SpeechSyncedBridge):
    """Speech-synced bridge with a bounded alarm, Pi dig, and display recovery.

    User-triggered failures first show synchronized cyber purple/green alarm
    expressions. The raw exception is not spoken. Instead the Pi generates one
    short, playful dig about the failed command, clears the alarm, speaks the dig
    through the Pi speaker, animates the Heltec mouth, then returns both displays
    to their normal idle states.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._pending_error_message = ""
        self._pending_error_action = ""
        self._alarm_started_at = 0.0
        self._error_sequence_active = False
        self._suppress_error_faces_until = 0.0
        self._error_dig_log = Path("logs/killerkoala_error_dig/bridge_events.jsonl")
        self._minimum_alarm_seconds = max(
            0.6,
            min(float(os.getenv("KOALABYTE_ERROR_ALARM_SECONDS", "2.2")), 8.0),
        )

    @staticmethod
    def _clean(value: Any, limit: int = 180) -> str:
        return " ".join(str(value or "").split())[:limit]

    def _remember_error(self, state: str, message: str) -> None:
        if not self._alarm_started_at:
            self._alarm_started_at = time.monotonic()
        self._pending_error_message = self._clean(message) or self._clean(state)

    def _fanout_face(
        self, state: str, message: str = "", duration_ms: int = 5000
    ) -> None:
        normalized = self._clean(state, 32).lower()
        failure_state = normalized in {
            "error",
            "alarmed",
            "fault",
            "exception",
            "disappointed",
            "angry",
        }
        if failure_state and not self._error_sequence_active:
            if time.monotonic() < self._suppress_error_faces_until:
                return
            self._remember_error(normalized, message)
        super()._fanout_face(state, message, duration_ms)

    def _play_response(self, text: str, channel: str) -> None:
        # A failed Pi action must not read a raw stack trace or exception aloud.
        # The route wrapper below replaces it with one bounded KillerKoala dig.
        if (
            not self._error_sequence_active
            and str(channel or "").startswith("pi-")
            and (self._pending_error_message or getattr(self, "_active_error", False))
        ):
            if not self._pending_error_message:
                self._pending_error_message = self._clean(text)
            return
        super()._play_response(text, channel)

    @staticmethod
    def _result_payload(routed: Any) -> Dict[str, Any]:
        if not isinstance(routed, dict):
            return {}
        result = routed.get("result", {})
        return dict(result) if isinstance(result, dict) else {}

    def _action_label(self, event: ESP32DualEyeVoiceEvent) -> str:
        return self._clean(
            event.payload.get("menu_label")
            or event.payload.get("action")
            or event.payload.get("command_id")
            or event.phrase
            or "KoalaByte action",
            80,
        )

    def _append_error_event(self, payload: Dict[str, Any]) -> None:
        self._error_dig_log.parent.mkdir(parents=True, exist_ok=True)
        with self._error_dig_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def _run_error_dig_sequence(
        self,
        *,
        action: str,
        error: str,
        request_id: str = "",
    ) -> str:
        action_text = self._clean(action, 80) or "KoalaByte action"
        error_text = self._clean(error, 180) or "action failed"

        if not self._alarm_started_at:
            self._alarm_started_at = time.monotonic()
            super()._fanout_face("alarmed", error_text, 30000)
        elif not getattr(self, "_active_error", False):
            super()._fanout_face("alarmed", error_text, 30000)

        dig = generate_error_dig(action_text, error_text)
        remaining = self._minimum_alarm_seconds - (
            time.monotonic() - self._alarm_started_at
        )
        if remaining > 0:
            time.sleep(remaining)

        self._error_sequence_active = True
        try:
            # The Heltec lifecycle clears its alarm latch and restores the mouth.
            # The subsequent speaking state immediately animates that mouth while
            # the Pi speaker delivers the generated line.
            self.clear_koalagotchi_error("alarm acknowledged")
            self._active_expression = None
            super()._play_response(dig, "pi-error-dig")
            super()._fanout_face("idle", "", 800)
        finally:
            self._error_sequence_active = False
            self._pending_error_message = ""
            self._pending_error_action = ""
            self._alarm_started_at = 0.0
            self._suppress_error_faces_until = time.monotonic() + 1.5

        event = {
            "type": "killerkoala_error_dig_sequence",
            "request_id": request_id,
            "action": action_text,
            "error": error_text,
            "dig": dig,
            "minimum_alarm_seconds": self._minimum_alarm_seconds,
            "speaker_owner": "raspberry-pi",
            "esp32_audio_streamed": False,
            "heltec_final_display": "killerkoala_mouth",
            "esp32_final_display": "idle_eyes",
            "completed_at": time.time(),
        }
        self._append_error_event(event)
        return dig

    def _route_phrase(self, event: ESP32DualEyeVoiceEvent) -> Dict[str, Any]:
        self._pending_error_message = ""
        self._pending_error_action = self._action_label(event)
        self._alarm_started_at = 0.0

        routed = super()._route_phrase(event)
        result = self._result_payload(routed)
        if is_error_result(result):
            raw_error = self._pending_error_message or error_details(result)
            dig = self._run_error_dig_sequence(
                action=self._pending_error_action,
                error=raw_error,
                request_id=event.request_id,
            )
            if isinstance(routed, dict):
                routed["error_dig"] = dig
                routed["error_alert_sequence"] = {
                    "heltec": "purple_green_alarm_then_speaking_mouth_then_idle_mouth",
                    "esp32": "purple_green_angry_eyes_then_speaking_then_idle_eyes",
                    "speaker_owner": "raspberry-pi",
                }
        else:
            self._pending_error_message = ""
            self._pending_error_action = ""
            self._alarm_started_at = 0.0
        return routed


__all__ = [
    "ESP32DualEyeVoiceBridge",
    "ESP32DualEyeVoiceEvent",
    "default_esp32_port",
]
