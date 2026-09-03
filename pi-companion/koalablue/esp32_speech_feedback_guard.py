from __future__ import annotations

import os
import time
from typing import Any, Callable, Optional


DEFAULT_SPEECH_FEEDBACK_COOLDOWN_SECONDS = max(
    0.5,
    min(float(os.getenv("KOALABYTE_SPEECH_FEEDBACK_COOLDOWN_SECONDS", "1.8")), 5.0),
)
DEFAULT_SUPPRESSED_REQUEST_TTL_SECONDS = max(
    5.0,
    min(float(os.getenv("KOALABYTE_SUPPRESSED_AUDIO_REQUEST_TTL_SECONDS", "12.0")), 30.0),
)


def install_esp32_speech_feedback_guard(bridge_cls: type[Any]) -> type[Any]:
    """Suppress ESP32 mic captures while Pi-owned speech is audible.

    The DualEye microphone is physically close enough to the Pi speaker that a
    William TTS response can be captured as a fresh utterance. PocketSphinx may
    then force that audio into another command grammar match, creating a spoken
    feedback loop. This guard treats Pi speech plus a short tail cooldown as a
    microphone lockout window. Request IDs first seen in that window stay
    suppressed until their end marker (or a bounded TTL) so late PCM packets
    cannot resurrect the same capture after playback finishes.
    """

    if getattr(bridge_cls, "_koalabyte_speech_feedback_guard_installed", False):
        return bridge_cls

    original_play_response: Callable[..., Any] = bridge_cls._play_response
    original_handle_payload: Callable[..., Optional[Any]] = bridge_cls.handle_payload

    def _prune_suppressed(instance: Any) -> None:
        now = time.monotonic()
        suppressed = getattr(instance, "_koalabyte_suppressed_audio_requests", None)
        if not isinstance(suppressed, dict):
            suppressed = {}
            instance._koalabyte_suppressed_audio_requests = suppressed
        ttl = float(
            getattr(
                instance,
                "_koalabyte_suppressed_audio_request_ttl_seconds",
                DEFAULT_SUPPRESSED_REQUEST_TTL_SECONDS,
            )
        )
        for request_id, seen_at in list(suppressed.items()):
            if now - float(seen_at) > ttl:
                suppressed.pop(request_id, None)

    def _play_response(instance: Any, text: str, channel: str) -> Any:
        instance._koalabyte_pi_speech_active = True
        try:
            return original_play_response(instance, text, channel)
        finally:
            instance._koalabyte_pi_speech_active = False
            cooldown = float(
                getattr(
                    instance,
                    "_koalabyte_speech_feedback_cooldown_seconds",
                    DEFAULT_SPEECH_FEEDBACK_COOLDOWN_SECONDS,
                )
            )
            instance._koalabyte_pi_speech_cooldown_until = time.monotonic() + cooldown

    def _handle_payload(instance: Any, payload: dict[str, Any]) -> Optional[Any]:
        payload_type = str(payload.get("type") or "")
        if not payload_type.startswith("audio_"):
            return original_handle_payload(instance, payload)

        _prune_suppressed(instance)
        request_id = str(payload.get("request_id") or "")
        suppressed = getattr(instance, "_koalabyte_suppressed_audio_requests", {})
        now = time.monotonic()
        speech_active = bool(getattr(instance, "_koalabyte_pi_speech_active", False))
        cooldown_until = float(
            getattr(instance, "_koalabyte_pi_speech_cooldown_until", 0.0)
        )
        in_lockout = speech_active or now < cooldown_until

        if request_id and (in_lockout or request_id in suppressed):
            first_seen = request_id not in suppressed
            suppressed[request_id] = now
            instance._koalabyte_suppressed_audio_requests = suppressed

            if first_seen:
                diag = getattr(instance, "_diag", None)
                if callable(diag):
                    diag(
                        "audio_feedback_suppressed",
                        request_id=request_id,
                        payload_type=payload_type,
                        speech_active=speech_active,
                        cooldown_remaining=round(max(0.0, cooldown_until - now), 3),
                        reason="pi_speech_feedback_guard",
                    )

            if payload_type == "audio_utterance_end":
                suppressed.pop(request_id, None)
            return None

        return original_handle_payload(instance, payload)

    bridge_cls._play_response = _play_response
    bridge_cls.handle_payload = _handle_payload
    bridge_cls._koalabyte_pi_speech_active = False
    bridge_cls._koalabyte_pi_speech_cooldown_until = 0.0
    bridge_cls._koalabyte_suppressed_audio_requests = {}
    bridge_cls._koalabyte_speech_feedback_cooldown_seconds = (
        DEFAULT_SPEECH_FEEDBACK_COOLDOWN_SECONDS
    )
    bridge_cls._koalabyte_suppressed_audio_request_ttl_seconds = (
        DEFAULT_SUPPRESSED_REQUEST_TTL_SECONDS
    )
    bridge_cls._koalabyte_speech_feedback_guard_installed = True
    return bridge_cls


__all__ = [
    "DEFAULT_SPEECH_FEEDBACK_COOLDOWN_SECONDS",
    "DEFAULT_SUPPRESSED_REQUEST_TTL_SECONDS",
    "install_esp32_speech_feedback_guard",
]
