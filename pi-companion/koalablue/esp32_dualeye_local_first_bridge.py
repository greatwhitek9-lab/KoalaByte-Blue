from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import wave
from dataclasses import asdict
from pathlib import Path
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
    complex utterances are the only voice work routed here. Responses generated
    by the Raspberry Pi are played through the Pi's own ALSA/PulseAudio speaker;
    response PCM is never streamed back to the ESP32 speaker.
    """

    def _play_response(self, text: str, channel: str) -> None:
        """Play Pi-owned TTS on the Raspberry Pi speaker only.

        Face and mouth state still fan out to the ESP32 and Heltec, but the audio
        waveform remains local to the Pi. The method is fail-soft so a missing or
        misconfigured speaker never aborts a completed menu action or AI reply.
        """

        pcm = self._tts_pcm(text)
        wav_path: Optional[Path] = None
        backend = "none"
        status = "unavailable"
        detail = "tts_returned_empty_pcm" if not pcm else ""

        self._heltec_speech(True, text, channel)
        self._fanout_face("speaking", text, 12000)
        try:
            if not pcm:
                return

            with tempfile.NamedTemporaryFile(
                prefix="killerkoala-pi-response-",
                suffix=".wav",
                delete=False,
            ) as temporary:
                wav_path = Path(temporary.name)

            with wave.open(str(wav_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(pcm)

            command: Optional[list[str]] = None
            aplay = shutil.which("aplay")
            if aplay:
                backend = "alsa-aplay"
                command = [aplay, "-q"]
                device = os.getenv("KOALABYTE_PI_ALSA_DEVICE", "default").strip()
                if device:
                    command.extend(["-D", device])
                command.append(str(wav_path))
            else:
                paplay = shutil.which("paplay")
                if paplay:
                    backend = "pulse-paplay"
                    command = [paplay]
                    sink = os.getenv("KOALABYTE_PI_PULSE_SINK", "").strip()
                    if sink:
                        command.extend(["--device", sink])
                    command.append(str(wav_path))

            if command is None:
                detail = "neither aplay nor paplay is installed"
                return

            completed = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=False,
                timeout=90,
                text=True,
            )
            if completed.returncode == 0:
                status = "played"
                detail = ""
            else:
                status = "failed"
                detail = " ".join((completed.stderr or "").split())[:240]
        except subprocess.TimeoutExpired:
            status = "failed"
            detail = "Pi speaker playback timed out"
        except Exception as exc:
            status = "failed"
            detail = str(exc)[:240]
        finally:
            if wav_path is not None:
                try:
                    wav_path.unlink(missing_ok=True)
                except Exception:
                    pass
            self._write_json(
                {
                    "type": "pi_audio_status",
                    "status": status,
                    "backend": backend,
                    "channel": channel,
                    "speaker_owner": "raspberry-pi",
                    "esp32_audio_streamed": False,
                    "message": " ".join(str(text).split())[:96],
                    "detail": detail,
                }
            )
            self._heltec_speech(False, "", channel)

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
