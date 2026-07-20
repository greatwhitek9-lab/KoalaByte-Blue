from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .esp32_dualeye_latched_koalagotchi_bridge import (
    ESP32DualEyeVoiceBridge as _LatchedKoalagotchiBridge,
    ESP32DualEyeVoiceEvent,
    default_esp32_port,
)
from .killerkoala_expression import (
    KillerKoalaExpression,
    classify_response_expression,
    expression_for_local_category,
)
from .killerkoala_face_bridge import _resolve_ports, _serial_write


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "active"}


class ESP32DualEyeVoiceBridge(_LatchedKoalagotchiBridge):
    """Local-vocabulary-first bridge with synchronized expressive speech.

    The Waveshare ESP32-S3 owns wake/basic vocabulary and embedded audio. The Pi
    mirrors those local speech lifecycle events to the Heltec mouth. Unmatched or
    open-ended requests fall through to TinyLlama, whose Australian male speech is
    played while both displays animate according to response tone and subject.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._active_expression: Optional[KillerKoalaExpression] = None

    def _expression(
        self,
        state: str,
        message: str,
        *,
        channel: str = "",
    ) -> KillerKoalaExpression:
        if self._active_expression is not None:
            return self._active_expression
        return classify_response_expression(
            message,
            status=state,
            event=channel or state,
            context={"display_state": state, "speech_channel": channel},
        )

    @staticmethod
    def _merge_expression(
        payload: Dict[str, Any], expression: KillerKoalaExpression
    ) -> Dict[str, Any]:
        payload.update(expression.to_payload())
        payload["expression_source"] = "pi_tone_subject_classifier"
        payload["eyes_visible"] = True
        payload["mouth_visible"] = True
        payload["speech_animation"] = True
        return payload

    @staticmethod
    def _fit_t114_line(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Keep compact USB-CDC JSON below the T114 256-byte input buffer."""

        fitted = dict(payload)
        for optional_key in ("message", "subject", "speech_motion"):
            if len(json.dumps(fitted, separators=(",", ":"))) < 255:
                return fitted
            if optional_key in fitted:
                fitted[optional_key] = ""
        if len(json.dumps(fitted, separators=(",", ":"))) >= 255:
            fitted.pop("message", None)
            fitted.pop("subject", None)
            fitted.pop("speech_motion", None)
        return fitted

    @classmethod
    def _compact_heltec_face(
        cls,
        state: str,
        message: str,
        duration_ms: int,
        expression: KillerKoalaExpression,
    ) -> Dict[str, Any]:
        # The T114 line buffer is 256 bytes including framing. Keep enough room
        # for the terminating newline while retaining the expression contract.
        return cls._fit_t114_line(
            {
                "type": "killerkoala_face",
                "state": str(state or "speaking")[:18],
                "message": " ".join(str(message).split())[:18],
                "duration_ms": max(250, min(int(duration_ms), 30000)),
                "tone": expression.tone[:14],
                "subject": expression.subject[:16],
                "mouth_expression": expression.mouth_expression[:16],
                "speech_motion": expression.speech_motion[:18],
                "intensity": expression.intensity,
            }
        )

    @classmethod
    def _compact_heltec_speech(
        cls,
        active: bool,
        message: str,
        expression: KillerKoalaExpression,
    ) -> Dict[str, Any]:
        return cls._fit_t114_line(
            {
                "type": "killerkoala_speech",
                "active": bool(active),
                "message": " ".join(str(message).split())[:28] if active else "",
                "tone": expression.tone[:14],
                "subject": expression.subject[:16],
                "mouth_expression": expression.mouth_expression[:16],
                "speech_motion": expression.speech_motion[:18],
                "intensity": expression.intensity,
            }
        )

    def _write_heltec(self, payload: Dict[str, Any]) -> None:
        try:
            _, heltec_port = _resolve_ports()
            _serial_write(heltec_port, self.baud, payload)
        except Exception:
            pass

    def _fanout_face(
        self, state: str, message: str = "", duration_ms: int = 5000
    ) -> None:
        expression = self._expression(state, message)
        esp32_payload = self._merge_expression(
            {
                "type": "killerkoala_face",
                "enabled": True,
                "state": state,
                "message": " ".join(str(message).split())[:68],
                "duration_ms": duration_ms,
                "left_eye": expression.left_eye,
                "right_eye": expression.right_eye,
                "brightness": expression.intensity,
                "source": "pi-companion",
                "transport": "pi-fanout",
            },
            expression,
        )
        self._write_json(esp32_payload)
        self._write_heltec(
            self._compact_heltec_face(state, message, duration_ms, expression)
        )

    def _heltec_speech(
        self, active: bool, message: str = "", channel: str = "pi-ai"
    ) -> None:
        expression = self._expression(
            "speaking" if active else "idle", message, channel=channel
        )
        self._write_heltec(
            self._compact_heltec_speech(active, message, expression)
        )

    def _play_response(self, text: str, channel: str) -> None:
        self._active_expression = classify_response_expression(
            text,
            status="speaking",
            event=channel,
            context={"speaker": "tinyllama_or_pi", "voice": "en-AU-WilliamNeural"},
        )
        try:
            super()._play_response(text, channel)
        finally:
            self._active_expression = None

    def _route_phrase(self, event: ESP32DualEyeVoiceEvent) -> Dict[str, Any]:
        routed = super()._route_phrase(event)
        result = routed.get("result", {}) if isinstance(routed, dict) else {}
        if isinstance(result, dict):
            message = str(
                result.get("companion_line")
                or result.get("message")
                or result.get("error")
                or ""
            )
            status = str(result.get("status") or "")
            expression = classify_response_expression(
                message,
                status=status,
                event="voice_result",
                context={"request_source": event.source},
            )
            routed["speech_expression"] = expression.to_payload()
        return routed

    def handle_payload(
        self, payload: Dict[str, Any]
    ) -> Optional[ESP32DualEyeVoiceEvent]:
        payload_type = str(payload.get("type") or "").strip().lower()
        if payload_type == "local_speech_state":
            active = _as_bool(payload.get("active"))
            category = str(payload.get("category") or "").strip().lower()
            message = str(
                payload.get("message")
                or category
                or "KillerKoala local response"
            ).strip()
            expression = expression_for_local_category(category, message)
            self._write_heltec(
                self._compact_heltec_speech(active, message, expression)
            )
            return None
        return super().handle_payload(payload)


__all__ = [
    "ESP32DualEyeVoiceBridge",
    "ESP32DualEyeVoiceEvent",
    "default_esp32_port",
]
