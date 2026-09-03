from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Optional

from .esp32_dualeye_sphinx_bridge import (
    _command_grammar_enabled,
    _command_grammar_for_root,
    resolve_pocketsphinx_model,
)
from .esp32_dualeye_voice_bridge import (
    ESP32DualEyeVoiceEvent,
    _wake_detected,
)


def _cached_command_transcript(
    bridge: Any,
    pcm: bytes,
    sample_rate: int,
    sample_width: int,
) -> str:
    """Decode one command with a reusable JSGF decoder."""

    if (
        not pcm
        or sample_rate != 16000
        or sample_width != 2
        or not _command_grammar_enabled()
    ):
        return ""

    root = resolve_pocketsphinx_model()
    if root is None:
        return ""

    try:
        from pocketsphinx import Decoder  # type: ignore

        decoder = getattr(bridge, "_koalabyte_unconfirmed_command_decoder", None)
        if decoder is None:
            grammar = _command_grammar_for_root(root)
            decoder = Decoder(
                hmm=str(root / "en-us"),
                jsgf=str(grammar.path),
                dict=str(grammar.dictionary_path),
                samprate=sample_rate,
                loglevel="ERROR",
            )
            bridge._koalabyte_unconfirmed_command_decoder = decoder

        decoder.start_utt()
        decoder.process_raw(pcm, False, True)
        decoder.end_utt()
        hypothesis = decoder.hyp()
        if hypothesis is None:
            return ""
        phrase = " ".join(str(hypothesis.hypstr or "").lower().split())
        if not (
            phrase.startswith("killer koala ")
            or phrase.startswith("hey killer koala ")
        ):
            return ""
        return phrase
    except Exception:
        bridge._koalabyte_unconfirmed_command_decoder = None
        return ""


def install_esp32_unconfirmed_stt_fastpath(bridge_cls: type[Any]) -> type[Any]:
    """Keep ambient/unconfirmed captures out of the expensive STT fallback stack.

    Unconfirmed physical captures use one reusable JSGF command decoder only.
    Grammar misses are rejected immediately instead of loading Whisper/general
    language models. Confirmed wake sessions retain the full recognizer pipeline.
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

        phrase = _cached_command_transcript(self, pcm, sample_rate, sample_width)

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
                scope="unconfirmed_command_only_cached",
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
    bridge_cls._koalabyte_unconfirmed_command_decoder = None
    bridge_cls._koalabyte_unconfirmed_stt_fastpath_installed = True
    return bridge_cls


__all__ = ["install_esp32_unconfirmed_stt_fastpath"]
