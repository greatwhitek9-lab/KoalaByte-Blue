from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .esp32_dualeye_error_dig_bridge import (
    ESP32DualEyeVoiceBridge as _ErrorDigBridge,
    ESP32DualEyeVoiceEvent,
    default_esp32_port,
)


DEFAULT_DISTRO_SPHINX_ROOT = Path("/usr/share/pocketsphinx/model/en-us")


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
    }


class ESP32DualEyeVoiceBridge(_ErrorDigBridge):
    """DualEye bridge with a validated offline PocketSphinx model fallback."""

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
    "default_esp32_port",
    "resolve_pocketsphinx_model",
    "validate_pocketsphinx_decoder",
]
