from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Optional

from .esp32_dualeye_voice_bridge import (
    ESP32DualEyeVoiceEvent,
    _wake_detected,
)


def install_esp32_unconfirmed_stt_fastpath(bridge_cls: type[Any]) -> type[Any]:
    """Keep ambient/unconfirmed captures out of the expensive STT fallback stack.

    For one-shot physical commands where the ESP32 has not independently
    confirmed the wake word, only the bounded JSGF command grammar is allowed.
    A grammar miss is rejected immediately instead of falling through Whisper
    and the general PocketSphinx language model, both of which can block the
    bridge loop long enough to delay K1-K6 display commands.

    Independently confirmed wake sessions retain the original full recognizer
    pipeline so open questions and conversational follow-ups still work.
    """

    if getattr(bridge_cls, "_koalabyte_unconfirmed_stt_fastpath_installed", False):
        return bridge_cls

    original_finish_audio: Callable[..., Optional[Any]] = bridge_cls._finish_audio

    def _finish_audio(self: Any, payload: dict[str, Any]) -> Optional[Any]:
        request_id = str(payload.get("request_id", ""))
        meta = dict(getattr(self, "_audio_meta", {}).get(request_id, {}) or {})
        wake_already_confirmed = bool(
            meta.get(
                "wake_already_confirmed",
                payload.get("wake_already_confirmed", False),
            )
        )

        if wake_already_confirmed:
            return original_finish_audio(self, payload)

        pcm = bytes(getattr(self, "_audio", {}).pop(request_id, b""))
        getattr(self, "_audio_meta", {}).pop(request_id, None)
        sample_rate = int(meta.get("sample_rate", 16000))
        sample_width = int(meta.get("sample_width", 2))
        resume_menu = bool(
            meta.get("menu_was_visible", payload.get("menu_was_visible", False))
        )

        grammar_transcriber = getattr(self, "_transcribe_with_command_grammar", None)
        phrase = ""
        if callable(grammar_transcriber):
            phrase = str(grammar_transcriber(pcm, sample_rate, sample_width) or "").strip()

        # Preserve observed-bridge recognizer metadata without invoking the full
        # _transcribe_pcm fallback chain.
        self._last_stt_search = "jsgf_commands"
        self._last_stt_transcript = phrase
        diag = getattr(self, "_diag", None)
        if callable(diag):
            diag(
                "recognizer_decision",
                request_id=request_id,
                pcm_bytes=len(pcm),
                search="jsgf_commands",
                transcript=phrase,
                scope="unconfirmed_command_only",
            )

        if not phrase:
            self._write_json(
                {
                    "type": "voice_rejected",
                    "request_id": request_id,
                    "reason": "unconfirmed_command_grammar_no_match",
                    "resume_menu": resume_menu,
                }
            )
            return None

        if not _wake_detected(phrase):
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

        self._fanout_face("thinking", "", 1800)
        event = ESP32DualEyeVoiceEvent(
            type="voice_command",
            phrase=phrase,
            source="esp32_s3_es7210_pi_wake_stt",
            request_id=request_id,
            payload={
                "transcript": phrase,
                "wake_already_confirmed": False,
                **meta,
                **payload,
            },
        )
        self.events.put(event)
        self._log_event(event)
        return event

    bridge_cls._finish_audio = _finish_audio
    bridge_cls._koalabyte_unconfirmed_stt_fastpath_installed = True
    return bridge_cls


__all__ = ["install_esp32_unconfirmed_stt_fastpath"]
