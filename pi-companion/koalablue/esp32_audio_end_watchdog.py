from __future__ import annotations

import os
import time
from typing import Any, Callable, Optional


DEFAULT_AUDIO_END_GRACE_SECONDS = max(
    1.1,
    min(float(os.getenv("KOALABYTE_AUDIO_END_GRACE_SECONDS", "1.6")), 3.0),
)
DEFAULT_AUDIO_END_MIN_PCM_BYTES = max(
    6400,
    min(int(os.getenv("KOALABYTE_AUDIO_END_MIN_PCM_BYTES", "16000")), 64000),
)


def install_esp32_audio_end_watchdog(bridge_cls: type[Any]) -> type[Any]:
    """Infer a missing utterance-end marker after buffered PCM goes quiet.

    Normal ESP32 ``audio_utterance_end`` control packets remain authoritative.
    This watchdog only closes an observed session when enough PCM has already
    arrived and no further PCM/control traffic for that request has appeared for
    a short grace period. It lets the Pi process a command even if the ESP32's
    final control packet is lost while leaving ordinary recognition untouched.
    """

    if getattr(bridge_cls, "_koalabyte_audio_end_watchdog_installed", False):
        return bridge_cls

    original_handle_payload: Callable[..., Optional[Any]] = bridge_cls.handle_payload
    original_read_once: Callable[..., Optional[Any]] = bridge_cls.read_once

    def handle_payload(self: Any, payload: dict[str, Any]) -> Optional[Any]:
        result = original_handle_payload(self, payload)
        payload_type = str(payload.get("type") or "")
        request_id = str(payload.get("request_id") or "")
        if payload_type in {"audio_utterance_start", "audio_pcm_chunk"} and request_id:
            sessions = getattr(self, "_stt_sessions", {})
            state = sessions.get(request_id)
            if isinstance(state, dict):
                state["last_pcm_at"] = time.monotonic()
        return result

    def recover_missing_end(self: Any) -> Optional[Any]:
        sessions = getattr(self, "_stt_sessions", {})
        if not isinstance(sessions, dict) or not sessions:
            return None

        now = time.monotonic()
        grace = float(
            getattr(self, "_audio_end_grace_seconds", DEFAULT_AUDIO_END_GRACE_SECONDS)
        )
        minimum = int(
            getattr(self, "_audio_end_min_pcm_bytes", DEFAULT_AUDIO_END_MIN_PCM_BYTES)
        )

        for request_id, state in list(sessions.items()):
            if not isinstance(state, dict):
                continue
            pcm_bytes = int(state.get("pcm_bytes", 0))
            if pcm_bytes < minimum:
                continue
            last_activity = float(
                state.get("last_pcm_at", state.get("started", now))
            )
            quiet_seconds = max(0.0, now - last_activity)
            if quiet_seconds < grace:
                continue

            diag = getattr(self, "_diag", None)
            if callable(diag):
                diag(
                    "utterance_end_inferred",
                    request_id=request_id,
                    packets=int(state.get("packets", 0)),
                    pcm_bytes=pcm_bytes,
                    quiet_seconds=round(quiet_seconds, 3),
                    reason="pi_pcm_inactivity_watchdog",
                )

            return self.handle_payload(
                {
                    "type": "audio_utterance_end",
                    "request_id": request_id,
                    "chunks": int(state.get("packets", 0)),
                    "reason": "pi_inferred_silence",
                    "inferred_by": "raspberry-pi",
                }
            )
        return None

    def read_once(self: Any) -> Optional[Any]:
        event = original_read_once(self)
        if event is not None:
            return event
        return recover_missing_end(self)

    bridge_cls.handle_payload = handle_payload
    bridge_cls.read_once = read_once
    bridge_cls._recover_missing_audio_end = recover_missing_end
    bridge_cls._audio_end_grace_seconds = DEFAULT_AUDIO_END_GRACE_SECONDS
    bridge_cls._audio_end_min_pcm_bytes = DEFAULT_AUDIO_END_MIN_PCM_BYTES
    bridge_cls._koalabyte_audio_end_watchdog_installed = True
    return bridge_cls


__all__ = [
    "DEFAULT_AUDIO_END_GRACE_SECONDS",
    "DEFAULT_AUDIO_END_MIN_PCM_BYTES",
    "install_esp32_audio_end_watchdog",
]
