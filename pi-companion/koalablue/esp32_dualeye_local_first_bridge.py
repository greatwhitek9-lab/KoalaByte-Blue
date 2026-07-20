from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

from .esp32_dualeye_voice_bridge import (
    ESP32DualEyeVoiceBridge as _IntegratedVoiceBridge,
    ESP32DualEyeVoiceEvent,
    _wake_detected,
    default_esp32_port,
)


class ESP32DualEyeVoiceBridge(_IntegratedVoiceBridge):
    """Pi bridge for the ESP32 local-first voice architecture.

    Basic wake/status/help/greeting/thanks/banter replies are handled and spoken
    entirely by the ESP32-S3. Fixed menu command IDs and explicitly escalated
    complex utterances are the only voice work routed here.
    """

    def _finish_audio(
        self, payload: Dict[str, Any]
    ) -> Optional[ESP32DualEyeVoiceEvent]:
        request_id = str(payload.get("request_id", ""))
        pcm = bytes(self._audio.pop(request_id, b""))
        meta = self._audio_meta.pop(request_id, {})
        phrase = self._transcribe_pcm(
            pcm,
            int(meta.get("sample_rate", 16000)),
            int(meta.get("sample_width", 2)),
        )
        resume_menu = bool(
            meta.get("menu_was_visible", payload.get("menu_was_visible", False))
        )
        wake_already_confirmed = bool(
            meta.get(
                "wake_already_confirmed",
                payload.get("wake_already_confirmed", False),
            )
        )
        if not phrase:
            self._write_json(
                {
                    "type": "voice_rejected",
                    "request_id": request_id,
                    "reason": "speech_not_understood",
                    "resume_menu": resume_menu,
                }
            )
            return None
        if not wake_already_confirmed and not _wake_detected(phrase):
            self._write_json(
                {
                    "type": "voice_rejected",
                    "request_id": request_id,
                    "reason": "wake_phrase_not_detected",
                    "transcript": phrase,
                    "resume_menu": resume_menu,
                }
            )
            return None

        routed_phrase = phrase
        if wake_already_confirmed and not _wake_detected(routed_phrase):
            prefix = str(meta.get("phrase_prefix") or "killerkoala").strip()
            routed_phrase = f"{prefix} {routed_phrase}".strip()

        self._fanout_face("thinking", "", 1800)
        event = ESP32DualEyeVoiceEvent(
            type="voice_command",
            phrase=routed_phrase,
            source=(
                "esp32_s3_local_wake_complex_capture"
                if wake_already_confirmed
                else "esp32_s3_es7210_pi_wake_stt"
            ),
            request_id=request_id,
            payload={
                "transcript": phrase,
                "wake_already_confirmed": wake_already_confirmed,
                **meta,
                **payload,
            },
        )
        self.events.put(event)
        self._log_event(event)
        return event


__all__ = [
    "ESP32DualEyeVoiceBridge",
    "ESP32DualEyeVoiceEvent",
    "default_esp32_port",
]
