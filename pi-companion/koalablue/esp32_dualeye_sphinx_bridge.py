from __future__ import annotations

import json
import os
import socket
import struct
from pathlib import Path
from typing import Any, Dict, Optional

from .esp32_dualeye_error_dig_bridge import (
    ESP32DualEyeVoiceBridge as _ErrorDigBridge,
    ESP32DualEyeVoiceEvent,
    default_esp32_port,
)
from .pocketsphinx_command_grammar import CommandGrammar, build_command_grammar


DEFAULT_DISTRO_SPHINX_ROOT = Path("/usr/share/pocketsphinx/model/en-us")
PCM_BINARY_MAGIC = b"KPCM"
PCM_BINARY_VERSION = 1
PCM_BINARY_HEADER = struct.Struct("<4sBBBBIIHH")
_COMMAND_GRAMMAR_CACHE: dict[str, CommandGrammar] = {}


def _decode_binary_pcm_packet(data: bytes) -> Optional[Dict[str, Any]]:
    if len(data) < PCM_BINARY_HEADER.size or not data.startswith(PCM_BINARY_MAGIC):
        return None
    try:
        (
            magic,
            version,
            batch_frames,
            source_channel,
            _reserved,
            request_id,
            sequence,
            pcm_bytes,
            rms_q15,
        ) = PCM_BINARY_HEADER.unpack_from(data)
    except struct.error:
        return None
    if magic != PCM_BINARY_MAGIC or version != PCM_BINARY_VERSION:
        return None
    if batch_frames < 1 or batch_frames > 2:
        return None
    if source_channel not in (0, 1):
        return None
    if pcm_bytes <= 0 or pcm_bytes > 1280:
        return None
    end = PCM_BINARY_HEADER.size + pcm_bytes
    if len(data) != end:
        return None
    return {
        "type": "audio_pcm_chunk",
        "request_id": str(request_id),
        "sequence": int(sequence),
        "batch_frames": int(batch_frames),
        "source_channel": int(source_channel),
        "rms": float(rms_q15) / 32768.0,
        "pcm_bytes": int(pcm_bytes),
        "pcm_transport": "binary_udp_v1",
        "_pcm_s16le_mono": data[PCM_BINARY_HEADER.size:end],
    }


def _valid_model_root(root: Path) -> bool:
    required = (
        root / "en-us" / "mdef",
        root / "en-us.lm.bin",
        root / "cmudict-en-us.dict",
    )
    return all(path.is_file() and path.stat().st_size > 0 for path in required)


def resolve_pocketsphinx_model() -> Path | None:
    configured = os.getenv("KOALABYTE_POCKETSPHINX_MODEL_ROOT", "").strip()
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.append(DEFAULT_DISTRO_SPHINX_ROOT)

    try:
        import pocketsphinx  # type: ignore

        candidates.append(Path(pocketsphinx.get_model_path()) / "en-us")
    except Exception:
        pass

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        try:
            if _valid_model_root(candidate):
                return candidate
        except OSError:
            continue
    return None


def _command_grammar_enabled() -> bool:
    return os.getenv("KOALABYTE_POCKETSPHINX_COMMAND_GRAMMAR", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _command_grammar_for_root(root: Path) -> CommandGrammar:
    key = str(root.resolve())
    grammar = _COMMAND_GRAMMAR_CACHE.get(key)
    if (
        grammar is None
        or not grammar.path.exists()
        or not grammar.dictionary_path.exists()
    ):
        grammar = build_command_grammar(root)
        _COMMAND_GRAMMAR_CACHE[key] = grammar
    return grammar


def validate_pocketsphinx_decoder() -> dict[str, Any]:
    root = resolve_pocketsphinx_model()
    if root is None:
        return {
            "ready": False,
            "reason": "no_nonempty_pocketsphinx_model",
            "model_root": None,
        }
    try:
        from pocketsphinx import Decoder  # type: ignore

        Decoder(
            hmm=str(root / "en-us"),
            lm=str(root / "en-us.lm.bin"),
            dict=str(root / "cmudict-en-us.dict"),
            loglevel="ERROR",
        )
        grammar = _command_grammar_for_root(root)
        Decoder(
            hmm=str(root / "en-us"),
            jsgf=str(grammar.path),
            dict=str(grammar.dictionary_path),
            samprate=16000,
            loglevel="ERROR",
        )
    except Exception as exc:
        return {
            "ready": False,
            "reason": f"decoder_init_failed:{type(exc).__name__}:{exc}",
            "model_root": str(root),
        }
    return {
        "ready": True,
        "reason": "",
        "model_root": str(root),
        "command_grammar_enabled": _command_grammar_enabled(),
        "command_grammar_path": str(grammar.path),
        "command_dictionary_path": str(grammar.dictionary_path),
        "command_dictionary_custom_words": len(grammar.custom_dictionary_words),
        "command_grammar_phrases": len(grammar.phrases),
        "command_grammar_rejected_phrases": len(grammar.rejected_phrases),
    }


class ESP32DualEyeVoiceBridge(_ErrorDigBridge):
    """DualEye bridge with JSGF commands, PocketSphinx fallback, and binary PCM UDP."""

    def _read_udp(self) -> Optional[Dict[str, Any]]:
        if self._udp is None:
            return None
        try:
            data, peer = self._udp.recvfrom(12288)
        except BlockingIOError:
            return None
        self._udp_peer = peer
        self._last_transport = "udp"

        binary_pcm = _decode_binary_pcm_packet(data)
        if binary_pcm is not None:
            return binary_pcm

        try:
            payload = json.loads(data.decode("utf-8", errors="ignore"))
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            return None

    def handle_payload(
        self, payload: Dict[str, Any]
    ) -> Optional[ESP32DualEyeVoiceEvent]:
        if (
            str(payload.get("type") or "") == "audio_pcm_chunk"
            and isinstance(payload.get("_pcm_s16le_mono"), (bytes, bytearray))
        ):
            if self._is_duplicate(payload):
                return None
            self._prune_audio_sessions()
            request_id = str(payload.get("request_id") or "")
            raw_pcm = bytes(payload.get("_pcm_s16le_mono") or b"")
            if (
                request_id in self._audio
                and raw_pcm
                and len(self._audio[request_id]) < 512000
            ):
                remaining = max(0, 512000 - len(self._audio[request_id]))
                self._audio[request_id].extend(raw_pcm[:remaining])
            return None
        return super().handle_payload(payload)

    def _transcribe_with_command_grammar(
        self, pcm: bytes, sample_rate: int, sample_width: int
    ) -> str:
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

            grammar = _command_grammar_for_root(root)
            decoder = Decoder(
                hmm=str(root / "en-us"),
                jsgf=str(grammar.path),
                dict=str(grammar.dictionary_path),
                samprate=sample_rate,
                loglevel="ERROR",
            )
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
            return ""

    def _transcribe_with_pocketsphinx(
        self, pcm: bytes, sample_rate: int, sample_width: int
    ) -> str:
        if not pcm or sample_rate != 16000 or sample_width != 2:
            return ""
        root = resolve_pocketsphinx_model()
        if root is None:
            return ""
        try:
            from pocketsphinx import Decoder  # type: ignore

            decoder = Decoder(
                hmm=str(root / "en-us"),
                lm=str(root / "en-us.lm.bin"),
                dict=str(root / "cmudict-en-us.dict"),
                samprate=sample_rate,
                loglevel="ERROR",
            )
            decoder.start_utt()
            decoder.process_raw(pcm, False, True)
            decoder.end_utt()
            hypothesis = decoder.hyp()
            return str(hypothesis.hypstr).strip() if hypothesis is not None else ""
        except Exception:
            return ""

    def _transcribe_pcm(self, pcm: bytes, sample_rate: int, sample_width: int) -> str:
        if not pcm:
            return ""

        transcript = self._transcribe_with_command_grammar(
            pcm, sample_rate, sample_width
        )
        if transcript:
            return transcript

        transcript = self._transcribe_with_whisper(pcm, sample_rate, sample_width)
        if transcript:
            return transcript
        transcript = self._transcribe_with_pocketsphinx(
            pcm, sample_rate, sample_width
        )
        if transcript:
            return transcript
        if os.getenv("KOALABYTE_ALLOW_ONLINE_STT", "0").strip().lower() not in {
            "1",
            "true",
            "yes",
        }:
            return ""
        try:
            import speech_recognition as sr  # type: ignore

            recognizer = sr.Recognizer()
            audio = sr.AudioData(pcm, sample_rate, sample_width)
            return str(recognizer.recognize_google(audio)).strip()
        except Exception:
            return ""


__all__ = [
    "ESP32DualEyeVoiceBridge",
    "ESP32DualEyeVoiceEvent",
    "PCM_BINARY_HEADER",
    "PCM_BINARY_MAGIC",
    "PCM_BINARY_VERSION",
    "_command_grammar_for_root",
    "_decode_binary_pcm_packet",
    "default_esp32_port",
    "resolve_pocketsphinx_model",
    "validate_pocketsphinx_decoder",
]
