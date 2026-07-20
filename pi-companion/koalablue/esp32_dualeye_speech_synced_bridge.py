from __future__ import annotations

from typing import Any, Dict, Optional

from .esp32_dualeye_latched_koalagotchi_bridge import (
    ESP32DualEyeVoiceBridge as _LatchedKoalagotchiBridge,
    ESP32DualEyeVoiceEvent,
    default_esp32_port,
)
from .killerkoala_face_bridge import emit_speech_state


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "active"}


class ESP32DualEyeVoiceBridge(_LatchedKoalagotchiBridge):
    """Latched Koalagotchi bridge with ESP32-local speech mouth sync.

    The ESP32 remains the owner and speaker for wake/basic responses. It emits a
    compact local_speech_state lifecycle event immediately before and after its
    embedded audio. The Pi only mirrors that lifecycle to the Heltec T114 mouth;
    it does not replay, replace, or reinterpret the local response.
    """

    def handle_payload(
        self, payload: Dict[str, Any]
    ) -> Optional[ESP32DualEyeVoiceEvent]:
        payload_type = str(payload.get("type") or "").strip().lower()
        if payload_type == "local_speech_state":
            active = _as_bool(payload.get("active"))
            channel = str(payload.get("channel") or "esp32-local").strip()
            message = str(
                payload.get("message")
                or payload.get("category")
                or "KillerKoala local response"
            ).strip()
            emit_speech_state(
                active,
                message if active else "",
                channel=channel or "esp32-local",
            )
            return None
        return super().handle_payload(payload)


__all__ = [
    "ESP32DualEyeVoiceBridge",
    "ESP32DualEyeVoiceEvent",
    "default_esp32_port",
]
