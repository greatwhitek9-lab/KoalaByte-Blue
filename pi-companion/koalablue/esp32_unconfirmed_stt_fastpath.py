from __future__ import annotations

import math
import os
import struct
import time
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

_DEFAULT_GATE_RMS = 0.0135
_DEFAULT_MIN_VOICED_MS = 60
_DEFAULT_PRE_ROLL_MS = 240
_DEFAULT_POST_ROLL_MS = 520


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)).strip())
    except (TypeError, ValueError):
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except (TypeError, ValueError):
        return default


def _prepare_command_pcm(
    pcm: bytes,
    sample_rate: int,
    sample_width: int,
) -> tuple[bytes, dict[str, Any]]:
    """Cheaply reject noise-floor captures and trim silence before PocketSphinx.

    The ESP32 intentionally has a sensitive 0.010 RMS wake threshold. On the
    physical DualEye that can open long ambient sessions at roughly 0.010-0.012
    RMS. Scanning 20 ms PCM blocks on the Pi is far cheaper than asking
    PocketSphinx to decode the full 4-6.5 second capture. Real speech keeps a
    short pre/post roll so wake consonants and final syllables are preserved.
    """

    metrics: dict[str, Any] = {
        "input_pcm_bytes": len(pcm),
        "prepared_pcm_bytes": 0,
        "gate_rms": _float_env("KOALABYTE_UNCONFIRMED_RMS_GATE", _DEFAULT_GATE_RMS),
        "peak_block_rms": 0.0,
        "voiced_blocks": 0,
        "total_blocks": 0,
        "trimmed": False,
        "gate_passed": False,
    }
    if not pcm or sample_rate != 16000 or sample_width != 2:
        return b"", metrics

    block_samples = max(1, sample_rate // 50)  # 20 ms
    block_bytes = block_samples * sample_width
    gate_rms = float(metrics["gate_rms"])
    min_voiced_blocks = max(
        1,
        math.ceil(_int_env("KOALABYTE_UNCONFIRMED_MIN_VOICED_MS", _DEFAULT_MIN_VOICED_MS) / 20.0),
    )
    pre_blocks = max(
        0,
        math.ceil(_int_env("KOALABYTE_UNCONFIRMED_PRE_ROLL_MS", _DEFAULT_PRE_ROLL_MS) / 20.0),
    )
    post_blocks = max(
        0,
        math.ceil(_int_env("KOALABYTE_UNCONFIRMED_POST_ROLL_MS", _DEFAULT_POST_ROLL_MS) / 20.0),
    )

    voiced: list[int] = []
    peak = 0.0
    block_index = 0
    for offset in range(0, len(pcm) - 1, block_bytes):
        chunk = pcm[offset : min(len(pcm), offset + block_bytes)]
        sample_count = len(chunk) // 2
        if sample_count <= 0:
            continue
        values = struct.unpack_from(f"<{sample_count}h", chunk)
        mean_square = sum(sample * sample for sample in values) / float(sample_count)
        rms = math.sqrt(mean_square) / 32768.0
        peak = max(peak, rms)
        if rms >= gate_rms:
            voiced.append(block_index)
        block_index += 1

    metrics["peak_block_rms"] = round(peak, 6)
    metrics["voiced_blocks"] = len(voiced)
    metrics["total_blocks"] = block_index
    if len(voiced) < min_voiced_blocks:
        return b"", metrics

    first = max(0, voiced[0] - pre_blocks)
    last = min(max(0, block_index - 1), voiced[-1] + post_blocks)
    start = first * block_bytes
    end = min(len(pcm), (last + 1) * block_bytes)
    prepared = pcm[start:end]
    metrics["prepared_pcm_bytes"] = len(prepared)
    metrics["trimmed"] = start > 0 or end < len(pcm)
    metrics["gate_passed"] = True
    metrics["trim_start_ms"] = first * 20
    metrics["trim_end_ms"] = (last + 1) * 20
    return prepared, metrics


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

    Unconfirmed physical captures are energy-gated, silence-trimmed, then sent to
    one reusable JSGF command decoder. Grammar misses never load Whisper/general
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

        prepared_pcm, pcm_metrics = _prepare_command_pcm(pcm, sample_rate, sample_width)
        phrase = ""
        if prepared_pcm:
            phrase = _cached_command_transcript(
                self,
                prepared_pcm,
                sample_rate,
                sample_width,
            )

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
                scope="unconfirmed_command_energy_gated_cached",
                **pcm_metrics,
            )

        if not prepared_pcm:
            self._write_json(
                {
                    "type": "voice_rejected",
                    "request_id": request_id,
                    "reason": "ambient_below_command_energy_gate",
                    "resume_menu": resume_menu,
                }
            )
            return None

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

        completed_at = time.time()
        self._fanout_face("thinking", "", 1800)
        event = ESP32DualEyeVoiceEvent(
            type="voice_command",
            phrase=phrase,
            source="esp32_s3_es7210_pi_wake_stt",
            request_id=request_id,
            payload={
                "transcript": phrase,
                "wake_already_confirmed": False,
                "pi_stt_completed_at": completed_at,
                "pcm_gate": pcm_metrics,
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


__all__ = [
    "_prepare_command_pcm",
    "install_esp32_unconfirmed_stt_fastpath",
]
