from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .bounded_log import append_jsonl
from .esp32_dualeye_sphinx_bridge import (
    ESP32DualEyeVoiceBridge as _SphinxBridge,
    ESP32DualEyeVoiceEvent,
    default_esp32_port,
)


DEFAULT_STT_DIAGNOSTICS_PATH = Path(
    os.getenv(
        "KOALABYTE_STT_DIAGNOSTICS_PATH",
        "logs/killerkoala/esp32_dualeye_stt_diagnostics.jsonl",
    )
)


class ESP32DualEyeVoiceBridge(_SphinxBridge):
    """Production DualEye bridge with bounded recognizer decision diagnostics."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._stt_diagnostics_path = DEFAULT_STT_DIAGNOSTICS_PATH
        self._stt_sessions: dict[str, dict[str, Any]] = {}
        self._active_stt_request_id = ""
        self._last_stt_transcript = ""
        self._last_stt_search = "none"

    def _diag(self, event: str, **payload: Any) -> None:
        append_jsonl(
            self._stt_diagnostics_path,
            {
                "event": event,
                "timestamp": time.time(),
                **payload,
            },
            max_bytes=1024 * 1024,
            backups=2,
        )

    def handle_payload(
        self, payload: Dict[str, Any]
    ) -> Optional[ESP32DualEyeVoiceEvent]:
        payload_type = str(payload.get("type") or "")
        request_id = str(payload.get("request_id") or "")

        if payload_type == "audio_utterance_start":
            self._stt_sessions[request_id] = {
                "packets": 0,
                "pcm_bytes": 0,
                "last_sequence": None,
                "sequence_gaps": [],
                "started": time.monotonic(),
            }
            self._diag(
                "utterance_start",
                request_id=request_id,
                rms=payload.get("rms"),
                sample_rate=payload.get("sample_rate", 16000),
                sample_width=payload.get("sample_width", 2),
            )

        elif (
            payload_type == "audio_pcm_chunk"
            and isinstance(payload.get("_pcm_s16le_mono"), (bytes, bytearray))
        ):
            state = self._stt_sessions.get(request_id)
            if state is not None:
                sequence = int(payload.get("sequence", -1))
                previous = state.get("last_sequence")
                if previous is not None and sequence != int(previous) + 1:
                    state["sequence_gaps"].append([int(previous), sequence])
                state["last_sequence"] = sequence
                state["packets"] += 1
                state["pcm_bytes"] += len(payload.get("_pcm_s16le_mono") or b"")

        if payload_type == "audio_utterance_end":
            self._active_stt_request_id = request_id
            self._last_stt_transcript = ""
            self._last_stt_search = "none"
            try:
                event = super().handle_payload(payload)
            finally:
                self._active_stt_request_id = ""

            state = self._stt_sessions.pop(request_id, {})
            wall_seconds = 0.0
            if state.get("started") is not None:
                wall_seconds = max(0.0, time.monotonic() - float(state["started"]))
            pcm_bytes = int(state.get("pcm_bytes", 0))
            self._diag(
                "utterance_end",
                request_id=request_id,
                reason=payload.get("reason"),
                packets=int(state.get("packets", 0)),
                pcm_bytes=pcm_bytes,
                audio_seconds=round(pcm_bytes / 32000.0, 3),
                wall_seconds=round(wall_seconds, 3),
                sequence_gaps=state.get("sequence_gaps", []),
                recognizer=self._last_stt_search,
                transcript=self._last_stt_transcript,
                accepted=event is not None,
                rejection=(
                    ""
                    if event is not None
                    else (
                        "speech_not_understood"
                        if not self._last_stt_transcript
                        else "wake_phrase_not_detected"
                    )
                ),
            )
            return event

        return super().handle_payload(payload)

    def _transcribe_pcm(self, pcm: bytes, sample_rate: int, sample_width: int) -> str:
        request_id = self._active_stt_request_id
        if not pcm:
            self._last_stt_search = "none"
            self._last_stt_transcript = ""
            self._diag(
                "recognizer_decision",
                request_id=request_id,
                pcm_bytes=0,
                search="none",
                transcript="",
            )
            return ""

        grammar = self._transcribe_with_command_grammar(pcm, sample_rate, sample_width)
        if grammar:
            self._last_stt_search = "jsgf_commands"
            self._last_stt_transcript = grammar
            self._diag(
                "recognizer_decision",
                request_id=request_id,
                pcm_bytes=len(pcm),
                search="jsgf_commands",
                transcript=grammar,
            )
            return grammar

        whisper = self._transcribe_with_whisper(pcm, sample_rate, sample_width)
        if whisper:
            self._last_stt_search = "whisper"
            self._last_stt_transcript = whisper
            self._diag(
                "recognizer_decision",
                request_id=request_id,
                pcm_bytes=len(pcm),
                search="whisper",
                transcript=whisper,
            )
            return whisper

        general = self._transcribe_with_pocketsphinx(pcm, sample_rate, sample_width)
        if general:
            self._last_stt_search = "general_lm"
            self._last_stt_transcript = general
            self._diag(
                "recognizer_decision",
                request_id=request_id,
                pcm_bytes=len(pcm),
                search="general_lm",
                transcript=general,
            )
            return general

        transcript = ""
        if os.getenv("KOALABYTE_ALLOW_ONLINE_STT", "0").strip().lower() in {
            "1",
            "true",
            "yes",
        }:
            try:
                import speech_recognition as sr  # type: ignore

                recognizer = sr.Recognizer()
                audio = sr.AudioData(pcm, sample_rate, sample_width)
                transcript = str(recognizer.recognize_google(audio)).strip()
            except Exception:
                transcript = ""

        self._last_stt_search = "online" if transcript else "none"
        self._last_stt_transcript = transcript
        self._diag(
            "recognizer_decision",
            request_id=request_id,
            pcm_bytes=len(pcm),
            search=self._last_stt_search,
            transcript=transcript,
        )
        return transcript

    def route_event(self, event: ESP32DualEyeVoiceEvent) -> Dict[str, Any]:
        result = super().route_event(event)
        result_data = result.get("result", {}) if isinstance(result, dict) else {}
        self._diag(
            "route_result",
            request_id=event.request_id,
            phrase=event.phrase,
            status=(result_data.get("status") if isinstance(result_data, dict) else ""),
            module_key=(
                result_data.get("module_key") if isinstance(result_data, dict) else ""
            ),
        )
        return result


__all__ = [
    "ESP32DualEyeVoiceBridge",
    "ESP32DualEyeVoiceEvent",
    "DEFAULT_STT_DIAGNOSTICS_PATH",
    "default_esp32_port",
]
