from __future__ import annotations

import base64
import json
import os
import queue
import socket
import tempfile
import time
import wave
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .dualeye_tts import synthesize_pcm16_mono_16k
from .killerkoala_hybrid_companion import companion_response
from .killerkoala_voice_control import DEFAULT_OUTPUT_DIR, DEFAULT_XP_PATH, parse_voice_command
from .killerkoala_voice_router import route_voice_phrase

DEFAULT_BAUD = 115200
DEFAULT_UDP_PORT = int(os.getenv("KOALABYTE_ESP32_UDP_PORT", "42110"))
DEFAULT_STATUS_PATH = Path("logs/killerkoala/esp32_dualeye_mic_status.json")
DEFAULT_EVENTS_PATH = Path("logs/killerkoala/esp32_dualeye_voice_events.jsonl")
WAKE_FORMS = ("killerkoala", "hey killerkoala")
LOCAL_AI_FALLBACKS = (
    "Righto, mate. I heard you, but that one is outside the current command deck.",
    "Copy that. No matching module yet, so I am keeping the claws off the controls.",
    "Got the request. The local deck has no safe route for it yet.",
    "Crikey, that command is new territory. I have left the system unchanged.",
    "Message received. Nothing in the current canopy maps cleanly to that request.",
    "I caught that, mate. The action catalogue does not have a matching branch yet.",
)


@dataclass
class ESP32DualEyeVoiceEvent:
    type: str
    phrase: str
    source: str
    wake_word: str = "killerkoala"
    mic: str = "esp32_s3_dualeye_builtin_mic"
    request_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ESP32DualEyeMicStatus:
    status: str
    ready: bool
    port: str
    reason: str = ""
    builtin_mic_present: bool = True
    pins_configured: Optional[bool] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)


def default_esp32_port() -> str:
    return (
        os.getenv("KOALABYTE_ESP32_MIC_PORT")
        or os.getenv("KOALABYTE_ESP32_FACE_PORT")
        or os.getenv("ESP32_PORT")
        or "/dev/koalabyte-esp32-dualeye"
    )


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _normalize_wake(text: str) -> str:
    normalized = " ".join(
        str(text or "").lower().replace("killer koala", "killerkoala").split()
    )
    return normalized.strip(" ,.!?;:")


def _wake_detected(text: str) -> bool:
    normalized = _normalize_wake(text)
    return normalized.startswith("killerkoala") or normalized.startswith("hey killerkoala")


class ESP32DualEyeVoiceBridge:
    """Pi STT, execution, AI, TTS and ESP32/Heltec expression coordinator."""

    def __init__(
        self,
        port: Optional[str] = None,
        baud: int = DEFAULT_BAUD,
        status_path: str | Path = DEFAULT_STATUS_PATH,
        events_path: str | Path = DEFAULT_EVENTS_PATH,
        output_dir: str | Path = DEFAULT_OUTPUT_DIR,
        xp_path: str | Path = DEFAULT_XP_PATH,
        serial_timeout: float = 0.05,
        udp_port: int = DEFAULT_UDP_PORT,
    ) -> None:
        self.port = port or default_esp32_port()
        self.baud = baud
        self.status_path = Path(status_path)
        self.events_path = Path(events_path)
        self.output_dir = Path(output_dir)
        self.xp_path = Path(xp_path)
        self.serial_timeout = serial_timeout
        self.udp_port = udp_port
        self._serial = None
        self._udp: Optional[socket.socket] = None
        self._udp_peer: Optional[tuple[str, int]] = None
        self._last_transport = "serial"
        self._audio: dict[str, bytearray] = {}
        self._audio_meta: dict[str, dict[str, Any]] = {}
        self._dedupe: dict[str, float] = {}
        self._whisper_model = None
        self._response_history: list[str] = []
        self.events: "queue.Queue[ESP32DualEyeVoiceEvent]" = queue.Queue()

    def open(self) -> None:
        try:
            import serial  # type: ignore
        except Exception as exc:
            raise RuntimeError("pyserial is required for ESP32-S3 DualEye bridge") from exc
        serial_port = serial.Serial()  # type: ignore[attr-defined]
        serial_port.port = self.port
        serial_port.baudrate = self.baud
        serial_port.timeout = self.serial_timeout
        serial_port.write_timeout = 1.0
        serial_port.dsrdtr = False
        serial_port.rtscts = False
        serial_port.dtr = False
        serial_port.rts = False
        serial_port.open()
        self._serial = serial_port
        try:
            self._udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._udp.bind(("0.0.0.0", self.udp_port))
            self._udp.setblocking(False)
        except OSError:
            if self._udp is not None:
                self._udp.close()
            self._udp = None
        time.sleep(0.2)
        self.request_status()
        self._provision_from_environment()

    def close(self) -> None:
        if self._udp is not None:
            self._udp.close()
            self._udp = None
        if self._serial is not None:
            try:
                self._serial.close()
            finally:
                self._serial = None

    def _serial_write_json(self, payload: Dict[str, Any]) -> None:
        if self._serial is None:
            return
        self._serial.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
        self._serial.flush()

    def _udp_write_json(self, payload: Dict[str, Any]) -> bool:
        if self._udp is None or self._udp_peer is None:
            return False
        self._udp.sendto(
            json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            self._udp_peer,
        )
        return True

    def _write_json(self, payload: Dict[str, Any], *, prefer_udp: bool = True) -> None:
        try:
            from .hdmi_display_state import publish_display_event

            publish_display_event(payload)
        except Exception:
            pass
        if not (prefer_udp and self._udp_write_json(payload)):
            self._serial_write_json(payload)

    def request_status(self) -> None:
        self._write_json(
            {"type": "node_status", "request": "integrated_runtime"},
            prefer_udp=False,
        )

    def provision_wifi(
        self,
        ssid: str,
        password: str,
        pi_host: str,
        pi_port: int = DEFAULT_UDP_PORT,
    ) -> None:
        self._serial_write_json(
            {
                "type": "wifi_config",
                "ssid": ssid,
                "password": password,
                "pi_host": pi_host,
                "pi_port": int(pi_port),
            }
        )

    def _provision_from_environment(self) -> None:
        ssid = os.getenv("KOALABYTE_WIFI_SSID", "").strip()
        password = os.getenv("KOALABYTE_WIFI_PASSWORD", "")
        host = os.getenv("KOALABYTE_PI_HOST", "").strip()
        if ssid and host:
            self.provision_wifi(ssid, password, host, self.udp_port)

    def simulate_voice_command(self, phrase: str = "killerkoala voice commands") -> None:
        self._write_json({"type": "simulate_voice_command", "phrase": phrase})

    def _write_status(self, payload: Dict[str, Any]) -> None:
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        self.status_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )

    def _log_event(self, event: ESP32DualEyeVoiceEvent) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), sort_keys=True) + "\n")

    def _dedupe_key(self, payload: Dict[str, Any]) -> str:
        return ":".join(
            str(payload.get(key, ""))
            for key in ("type", "request_id", "sequence", "status", "message")
        )

    def _is_duplicate(self, payload: Dict[str, Any]) -> bool:
        now = time.time()
        self._dedupe = {
            key: stamp for key, stamp in self._dedupe.items() if now - stamp < 20.0
        }
        key = self._dedupe_key(payload)
        if key in self._dedupe:
            return True
        self._dedupe[key] = now
        return False

    def _fanout_face(
        self, state: str, message: str = "", duration_ms: int = 5000
    ) -> None:
        payload = {
            "type": "killerkoala_face",
            "enabled": True,
            "state": state,
            "message": " ".join(str(message).split())[:68],
            "duration_ms": duration_ms,
            "left_eye": "#A54BFF",
            "right_eye": "#32FF71",
            "brightness": 100,
            "source": "pi-companion",
            "transport": "pi-fanout",
        }
        self._write_json(payload)
        try:
            from .killerkoala_face_bridge import _resolve_ports, _serial_write

            _, heltec_port = _resolve_ports()
            _serial_write(heltec_port, self.baud, payload)
        except Exception:
            pass

    def _heltec_speech(
        self, active: bool, message: str = "", channel: str = "pi-ai"
    ) -> None:
        try:
            from .killerkoala_face_bridge import (
                _resolve_ports,
                _serial_write,
                build_speech_payload,
            )

            _, heltec_port = _resolve_ports()
            speech_payload = build_speech_payload(active, message, channel)
            try:
                from .hdmi_display_state import publish_display_event

                publish_display_event(speech_payload)
            except Exception:
                pass
            _serial_write(
                heltec_port,
                self.baud,
                speech_payload,
            )
        except Exception:
            pass

    def _transcribe_with_whisper(
        self, pcm: bytes, sample_rate: int, sample_width: int
    ) -> str:
        try:
            from faster_whisper import WhisperModel  # type: ignore

            if self._whisper_model is None:
                self._whisper_model = WhisperModel(
                    os.getenv("KOALABYTE_WHISPER_MODEL", "tiny.en"),
                    device=os.getenv("KOALABYTE_WHISPER_DEVICE", "cpu"),
                    compute_type=os.getenv("KOALABYTE_WHISPER_COMPUTE", "int8"),
                )
            with tempfile.TemporaryDirectory(prefix="dualeye-stt-") as temp:
                wav_path = Path(temp) / "utterance.wav"
                with wave.open(str(wav_path), "wb") as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(sample_width)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(pcm)
                segments, _ = self._whisper_model.transcribe(
                    str(wav_path), beam_size=1, vad_filter=True
                )
                return " ".join(segment.text.strip() for segment in segments).strip()
        except Exception:
            return ""

    def _transcribe_pcm(self, pcm: bytes, sample_rate: int, sample_width: int) -> str:
        if not pcm:
            return ""
        transcript = self._transcribe_with_whisper(pcm, sample_rate, sample_width)
        if transcript:
            return transcript
        try:
            import speech_recognition as sr  # type: ignore

            recognizer = sr.Recognizer()
            audio = sr.AudioData(pcm, sample_rate, sample_width)
            try:
                transcript = str(recognizer.recognize_sphinx(audio)).strip()
            except Exception:
                transcript = ""
            if transcript:
                return transcript
            if os.getenv("KOALABYTE_ALLOW_ONLINE_STT", "0").strip().lower() in {
                "1",
                "true",
                "yes",
            }:
                return str(recognizer.recognize_google(audio)).strip()
        except Exception:
            pass
        return ""

    def _tts_pcm(self, text: str) -> bytes:
        return synthesize_pcm16_mono_16k(text)

    def _play_response(self, text: str, channel: str) -> None:
        pcm = self._tts_pcm(text)
        self._heltec_speech(True, text, channel)
        try:
            if not pcm:
                self._write_json(
                    {
                        "type": "audio_stop",
                        "message": text,
                        "audio_available": False,
                    }
                )
                return
            self._fanout_face("speaking", text, 12000)
            for offset in range(0, len(pcm), 1024):
                chunk = pcm[offset : offset + 1024]
                self._write_json(
                    {
                        "type": "audio_pcm",
                        "pcm_s16le_mono_b64": base64.b64encode(chunk).decode("ascii"),
                        "message": text[:48],
                        "end": offset + len(chunk) >= len(pcm),
                    }
                )
        finally:
            self._heltec_speech(False, "", channel)

    def _remember_response(self, text: str) -> str:
        clean = " ".join(str(text or "").split())
        if not clean:
            clean = LOCAL_AI_FALLBACKS[0]
        self._response_history.append(clean)
        self._response_history = self._response_history[-8:]
        return clean

    def _unique_local_ai_response(self, phrase: str) -> tuple[str, Dict[str, Any]]:
        recent = set(self._response_history[-5:])
        last_ai: Any = None
        for _ in range(3):
            ai = companion_response(
                "banter",
                user_text=phrase,
                context={"status": "ai_fallback", "avoid_lines": list(recent)},
                flexible=True,
            )
            last_ai = ai
            candidate = " ".join(str(ai.text or "").split())
            if candidate and candidate not in recent:
                return self._remember_response(candidate), asdict(ai)
        start = abs(hash(phrase)) % len(LOCAL_AI_FALLBACKS)
        for offset in range(len(LOCAL_AI_FALLBACKS)):
            candidate = LOCAL_AI_FALLBACKS[(start + offset) % len(LOCAL_AI_FALLBACKS)]
            if candidate not in recent:
                return self._remember_response(candidate), (
                    asdict(last_ai) if last_ai is not None else {}
                )
        candidate = f"{LOCAL_AI_FALLBACKS[start]} Request marker {int(time.time()) % 97}."
        return self._remember_response(candidate), (
            asdict(last_ai) if last_ai is not None else {}
        )

    def _menu_preview(self, phrase: str) -> Optional[dict[str, Any]]:
        parsed = parse_voice_command(phrase, require_wake_word=True)
        action = parsed.menu_action
        if action is None:
            return None
        payload = {
            "type": "menu_sync",
            "event_type": "select",
            "selected_position": 1,
            "total_items": 1,
            "selected_label": action.label,
            "selected_command": action.command,
            "selected_group": action.group,
            "selected_enabled": True,
            "visible_items": [
                {
                    "position": 1,
                    "label": action.label,
                    "selected": True,
                    "enabled": True,
                }
            ],
            "source": "pi-companion",
            "voice_request": True,
            "execution_owner": "raspberry-pi",
        }
        self._write_json(payload)
        self._fanout_face("action", action.label, 8000)
        return payload

    def _route_phrase(self, event: ESP32DualEyeVoiceEvent) -> Dict[str, Any]:
        self._fanout_face("thinking", event.phrase, 8000)
        menu_preview = self._menu_preview(event.phrase)
        result = route_voice_phrase(
            event.phrase,
            require_wake_word=True,
            output_dir=self.output_dir,
            xp_path=self.xp_path,
        )
        result_data = _jsonable(result)
        status = str(result_data.get("status", "error"))
        error = str(result_data.get("error") or "")
        channel = "pi-execution"
        if status == "blocked" and "no supported module or menu action" in error.lower():
            message, ai_data = self._unique_local_ai_response(event.phrase)
            status = "ai_response"
            channel = "pi-ai"
            result_data = {
                "status": status,
                "phrase": event.phrase,
                "companion_line": message,
                "ai": ai_data,
                "local": True,
                "non_repeating": True,
            }
        else:
            message = str(
                result_data.get("companion_line")
                or result_data.get("error")
                or status
            )
        success = status in {"success", "ai_response"}
        action_label = str(
            (menu_preview or {}).get("selected_label") or "KillerKoala voice request"
        )
        result_payload = {
            "type": "pi_execution_result",
            "request_id": event.request_id,
            "status": "success" if success else status,
            "message": message,
            "action": action_label,
            "voice_request": True,
            "menu_preview": menu_preview,
            "result": result_data,
        }
        self._write_json(result_payload)
        self._fanout_face("success" if success else "error", message, 6500)
        self._play_response(message, channel)
        self._fanout_face("success" if success else "error", message, 4200 if success else 7000)
        return {"event": asdict(event), "result": result_data}

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
        resume_menu = bool(meta.get("menu_was_visible", payload.get("menu_was_visible", False)))
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
        self._fanout_face("wake", "wake word heard", 1800)
        event = ESP32DualEyeVoiceEvent(
            type="voice_command",
            phrase=phrase,
            source="esp32_s3_es7210_local_stt",
            request_id=request_id,
            payload={"transcript": phrase, **meta, **payload},
        )
        self.events.put(event)
        self._log_event(event)
        return event

    def handle_payload(
        self, payload: Dict[str, Any]
    ) -> Optional[ESP32DualEyeVoiceEvent]:
        if self._is_duplicate(payload):
            return None
        payload_type = str(payload.get("type", ""))
        if payload_type in {
            "node_status",
            "voice_backend",
            "voice_backend_heartbeat",
            "voice_stack",
            "boot",
        }:
            status = ESP32DualEyeMicStatus(
                status=str(
                    payload.get("audio_status") or payload.get("status") or "reported"
                ),
                ready=bool(payload.get("mic_ready", payload.get("ready", False))),
                port=self.port,
                reason=str(payload.get("reason", "")),
                builtin_mic_present=bool(payload.get("builtin_mic_present", True)),
                pins_configured=payload.get("pins_configured"),
                payload=payload,
            )
            self._write_status(asdict(status))
            return None
        if payload_type in {"display_fault", "audio_fault"}:
            message = str(payload.get("reason") or payload.get("message") or payload_type)
            self._fanout_face("error", message, 7000)
            return None
        if payload_type == "status":
            message = str(payload.get("message") or "")
            if any(token in message.lower() for token in ("failed", "error", "fault")):
                self._fanout_face("error", message, 7000)
            return None
        if payload_type == "audio_utterance_start":
            request_id = str(payload.get("request_id", ""))
            self._audio[request_id] = bytearray()
            self._audio_meta[request_id] = dict(payload)
            return None
        if payload_type == "audio_pcm_chunk":
            request_id = str(payload.get("request_id", ""))
            encoded = str(payload.get("pcm_s16le_mono_b64", ""))
            if (
                request_id in self._audio
                and encoded
                and len(self._audio[request_id]) < 512000
            ):
                self._audio[request_id].extend(
                    base64.b64decode(encoded, validate=False)
                )
            return None
        if payload_type == "audio_utterance_end":
            return self._finish_audio(payload)
        if payload_type not in {
            "voice_wake",
            "voice_command",
            "pi_execute_request",
            "pi_ai_request",
        }:
            return None
        phrase = str(payload.get("phrase") or "").strip()
        if not phrase:
            return None
        event = ESP32DualEyeVoiceEvent(
            type="voice_command",
            phrase=phrase,
            source=str(payload.get("source") or "esp32_s3_dualeye"),
            wake_word=str(payload.get("wake_word") or "killerkoala"),
            request_id=str(payload.get("request_id") or ""),
            payload=payload,
        )
        self.events.put(event)
        self._log_event(event)
        return event

    def _read_udp(self) -> Optional[Dict[str, Any]]:
        if self._udp is None:
            return None
        try:
            data, peer = self._udp.recvfrom(12288)
        except BlockingIOError:
            return None
        self._udp_peer = peer
        self._last_transport = "udp"
        try:
            payload = json.loads(data.decode("utf-8", errors="ignore"))
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            return None

    def _read_serial(self) -> Optional[Dict[str, Any]]:
        if self._serial is None:
            return None
        line = self._serial.readline().decode("utf-8", errors="ignore").strip()
        if not line:
            return None
        self._last_transport = "serial"
        try:
            payload = json.loads(line)
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            return None

    def read_once(self) -> Optional[ESP32DualEyeVoiceEvent]:
        payload = self._read_udp() or self._read_serial()
        return self.handle_payload(payload) if payload else None

    def route_event(self, event: ESP32DualEyeVoiceEvent) -> Dict[str, Any]:
        return self._route_phrase(event)

    def run(
        self, seconds: Optional[float] = None, once: bool = False
    ) -> Dict[str, Any]:
        self.open()
        routed: list[Dict[str, Any]] = []
        started = time.time()
        try:
            while True:
                event = self.read_once()
                if event is not None:
                    routed.append(self.route_event(event))
                    if once:
                        break
                if seconds is not None and time.time() - started >= seconds:
                    break
                time.sleep(0.005)
        finally:
            self.close()
        payload = {
            "status": "ESP32_DUALEYE_INTEGRATED_BRIDGE_COMPLETE",
            "port": self.port,
            "udp_port": self.udp_port,
            "routed_count": len(routed),
            "routed": routed,
            "updated_at": time.time(),
        }
        self._write_status(payload)
        return payload
