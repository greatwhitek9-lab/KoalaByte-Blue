from __future__ import annotations

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
    streamed back while both displays animate according to response tone/subject.
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
    def _merge_expression(payload: Dict[str, Any], expression: KillerKoalaExpression) -> Dict[str, Any]:
        payload.update(expression.to_payload())
        payload["expression_source"] = "pi_tone_subject_classifier"
        payload["eyes_visible"] = True
        payload["mouth_visible"] = True
        payload["speech_animation"] = True
        return payload

    def _fanout_face(
        self, state: str, message: str = "", duration_ms: int = 5000
    ) -> None:
        expression = self._expression(state, message)
        payload = self._merge_expression(
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
        self._write_json(payload)
        try:
            _, heltec_port = _resolve_ports()
            _serial_write(heltec_port, self.baud, payload)
        except Exception:
            pass

    def _heltec_speech(
        self, active: bool, message: str = "", channel: str = "pi-ai"
    ) -> None:
        expression = self._expression("speaking" if active else "idle", message, channel=channel)
        payload = self._merge_expression(
            {
                "type": "killerkoala_speech",
                "active": bool(active),
                "message": " ".join(str(message).split())[:48] if active else "",
                "channel": " ".join(str(channel or "pi-ai").split())[:20].lower(),
                "target_display": "heltec-t114",
                "source": "pi-companion",
            },
            expression,
        )
        try:
            _, heltec_port = _resolve_ports()
            _serial_write(heltec_port, self.baud, payload)
        except Exception:
            pass

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
            channel = str(payload.get("channel") or "esp32-local").strip()
            category = str(payload.get("category") or "").strip().lower()
            message = str(
                payload.get("message")
                or category
                or "KillerKoala local response"
            ).strip()
            expression = expression_for_local_category(category, message)
            local_payload = self._merge_expression(
                {
                    "type": "killerkoala_speech",
                    "active": active,
                    "message": message[:48] if active else "",
                    "channel": channel or "esp32-local",
                    "target_display": "heltec-t114",
                    "source": "esp32-s3-dualeye",
                    "local_vocabulary_owner": "waveshare-esp32-s3",
                    "requires_pi_response": False,
                },
                expression,
            )
            try:
                _, heltec_port = _resolve_ports()
                _serial_write(heltec_port, self.baud, local_payload)
            except Exception:
                pass
            return None
        return super().handle_payload(payload)


__all__ = [
    "ESP32DualEyeVoiceBridge",
    "ESP32DualEyeVoiceEvent",
    "default_esp32_port",
]
