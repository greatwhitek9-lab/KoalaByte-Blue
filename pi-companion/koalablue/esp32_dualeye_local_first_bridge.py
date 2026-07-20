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


_MENU_NAVIGATION_IDS = {
    "k1_main_menu",
    "k2_back",
    "k3_select",
    "k4_forward",
    "k5_up",
    "k6_down",
}


class ESP32DualEyeVoiceBridge(_IntegratedVoiceBridge):
    """Pi bridge for the ESP32 local-first voice architecture.

    Basic wake/status/help/greeting/thanks/banter replies are handled and spoken
    entirely by the ESP32-S3. K1-K8 and full generated menu labels arrive with
    exact catalog command IDs, so Pi execution does not depend on re-parsing the
    speech transcript. Complex utterances remain the only PCM/STT path.
    """

    def _play_response(self, text: str, channel: str) -> None:
        """Play Pi-owned TTS on the Raspberry Pi speaker only."""

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

    def _route_exact_catalog_command(
        self, event: ESP32DualEyeVoiceEvent
    ) -> Optional[Dict[str, Any]]:
        command_id = str(event.payload.get("command_id") or "").strip()
        if not command_id:
            return None

        label = str(event.payload.get("menu_label") or command_id).strip()
        group = str(event.payload.get("menu_group") or "System / Companion").strip()
        menu_name = str(event.payload.get("menu_name") or "main").strip()

        if command_id in _MENU_NAVIGATION_IDS or command_id.startswith("submenu:"):
            result_data: Dict[str, Any] = {
                "status": "success",
                "command_id": command_id,
                "menu_label": label,
                "menu_name": menu_name,
                "navigation_only": True,
                "handled_on_esp32": True,
            }
            self._write_json(
                {
                    "type": "menu_control_ack",
                    "request_id": event.request_id,
                    "status": "success",
                    "command_id": command_id,
                    "menu_label": label,
                    "menu_name": menu_name,
                    "handled_on_esp32": True,
                }
            )
            self._fanout_face("menu", label, 2200)
            return {"event": asdict(event), "result": result_data}

        # K7/K8 are translated by the ESP32 to the exact protected menu rows.
        from .menu_action_runner import run_automated_menu_action

        self._fanout_face("action", label, 8000)
        try:
            result = run_automated_menu_action(command_id, label, group)
            result_data = dict(result) if isinstance(result, dict) else {
                "status": "success",
                "result": result,
            }
        except Exception as exc:
            result_data = {"status": "error", "error": str(exc)}

        status = str(result_data.get("status", "error"))
        success = not any(
            token in status.upper() for token in ("ERROR", "FAILED", "BLOCKED")
        )
        message = str(
            result_data.get("companion_line")
            or result_data.get("message")
            or result_data.get("error")
            or (f"{label} complete" if success else f"{label} hit a snag")
        )
        result_payload = {
            "type": "pi_execution_result",
            "request_id": event.request_id,
            "status": "success" if success else status,
            "message": message,
            "action": label,
            "voice_request": True,
            "command_id": command_id,
            "menu_name": menu_name,
            "result": result_data,
        }
        self._write_json(result_payload)
        self._fanout_face("success" if success else "error", message, 6500)
        self._play_response(message, "pi-execution")
        return {"event": asdict(event), "result": result_data}

    def _route_phrase(self, event: ESP32DualEyeVoiceEvent) -> Dict[str, Any]:
        exact = self._route_exact_catalog_command(event)
        if exact is not None:
            return exact
        return super()._route_phrase(event)

    def handle_payload(
        self, payload: Dict[str, Any]
    ) -> Optional[ESP32DualEyeVoiceEvent]:
        if str(payload.get("type") or "") == "menu_control":
            event = ESP32DualEyeVoiceEvent(
                type="menu_control",
                phrase=str(payload.get("menu_label") or payload.get("control") or ""),
                source=str(payload.get("source") or "esp32_s3_multinet_local"),
                request_id=str(payload.get("request_id") or ""),
                payload=dict(payload),
            )
            self.events.put(event)
            self._log_event(event)
            return event
        return super().handle_payload(payload)

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
