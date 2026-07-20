from __future__ import annotations

import audioop
import base64
import json
import os
import queue
import shutil
import socket
import subprocess
import tempfile
import time
import wave
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .killerkoala_hybrid_companion import companion_response
from .killerkoala_voice_control import DEFAULT_OUTPUT_DIR, DEFAULT_XP_PATH, parse_voice_command
from .killerkoala_voice_router import route_voice_phrase

DEFAULT_BAUD = 115200
DEFAULT_UDP_PORT = int(os.getenv("KOALABYTE_ESP32_UDP_PORT", "42110"))
DEFAULT_STATUS_PATH = Path("logs/killerkoala/esp32_dualeye_mic_status.json")
DEFAULT_EVENTS_PATH = Path("logs/killerkoala/esp32_dualeye_voice_events.jsonl")
WAKE_FORMS = ("killerkoala", "hey killerkoala")


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
    return os.getenv("KOALABYTE_ESP32_MIC_PORT") or os.getenv("KOALABYTE_ESP32_FACE_PORT") or os.getenv("ESP32_PORT") or "/dev/koalabyte-esp32-dualeye"


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
    normalized = " ".join(str(text or "").lower().replace("killer koala", "killerkoala").split())
    return normalized.strip(" ,.!?;:")


def _wake_detected(text: str) -> bool:
    normalized = _normalize_wake(text)
    return normalized.startswith("killerkoala") or normalized.startswith("hey killerkoala")


class ESP32DualEyeVoiceBridge:
    """Pi execution/AI bridge for the non-touch ESP32-S3 DualEye.

    The ESP32 owns microphone capture, response playback, the animated eyes and
    menu rendering. The Pi owns STT, every menu/submenu execution and all
    requests outside the local response scope. The same canonical face state is
    sent independently to the ESP32 and Heltec; BLE is not a face-sync link.
    """

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
        self.events: "queue.Queue[ESP32DualEyeVoiceEvent]" = queue.Queue()

    def open(self) -> None:
        try:
            import serial  # type: ignore
        except Exception as exc:
            raise RuntimeError("pyserial is required for ESP32-S3 DualEye bridge") from exc
        self._serial = serial.Serial(self.port, self.baud, timeout=self.serial_timeout)
        self._serial.dtr = False
        self._serial.rts = False
        self._udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._udp.bind(("0.0.0.0", self.udp_port))
        self._udp.setblocking(False)
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
        self._udp.sendto(json.dumps(payload, separators=(",", ":")).encode("utf-8"), self._udp_peer)
        return True

    def _write_json(self, payload: Dict[str, Any], *, prefer_udp: bool = True) -> None:
        if not (prefer_udp and self._udp_write_json(payload)):
            self._serial_write_json(payload)

    def request_status(self) -> None:
        self._write_json({"type": "node_status", "request": "integrated_runtime"}, prefer_udp=False)

    def provision_wifi(self, ssid: str, password: str, pi_host: str, pi_port: int = DEFAULT_UDP_PORT) -> None:
        self._serial_write_json({"type": "wifi_config", "ssid": ssid, "password": password, "pi_host": pi_host, "pi_port": int(pi_port)})

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
        self.status_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _log_event(self, event: ESP32DualEyeVoiceEvent) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(event), sort_keys=True) + "\n")

    def _dedupe_key(self, payload: Dict[str, Any]) -> str:
        return ":".join(str(payload.get(key, "")) for key in ("type", "request_id", "sequence", "status", "message"))

    def _is_duplicate(self, payload: Dict[str, Any]) -> bool:
        now = time.time()
        self._dedupe = {key: stamp for key, stamp in self._dedupe.items() if now - stamp < 20.0}
        key = self._dedupe_key(payload)
        if key in self._dedupe:
            return True
        self._dedupe[key] = now
        return False

    def _fanout_face(self, state: str, message: str = "", duration_ms: int = 5000) -> None:
        payload = {
            "type": "killerkoala_face", "enabled": True, "state": state,
            "message": " ".join(str(message).split())[:68], "duration_ms": duration_ms,
            "left_eye": "#A54BFF", "right_eye": "#32FF71", "brightness": 100,
            "source": "pi-companion", "transport": "pi-fanout",
        }
        self._write_json(payload)
        try:
            from .killerkoala_face_bridge import _resolve_ports, _serial_write
            _, heltec_port = _resolve_ports()
            _serial_write(heltec_port, self.baud, payload)
        except Exception:
            pass

    def _heltec_speech(self, active: bool, message: str = "", channel: str = "pi-ai") -> None:
        try:
            from .killerkoala_face_bridge import _resolve_ports, _serial_write, build_speech_payload
            _, heltec_port = _resolve_ports()
            _serial_write(heltec_port, self.baud, build_speech_payload(active, message, channel))
        except Exception:
            pass

    def _transcribe_pcm(self, pcm: bytes, sample_rate: int, sample_width: int) -> str:
        if not pcm:
            return ""
        try:
            import speech_recognition as sr  # type: ignore
            recognizer = sr.Recognizer()
            audio = sr.AudioData(pcm, sample_rate, sample_width)
            try:
                return str(recognizer.recognize_google(audio)).strip()
            except Exception:
                try:
                    return str(recognizer.recognize_sphinx(audio)).strip()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            from faster_whisper import WhisperModel  # type: ignore
            with tempfile.TemporaryDirectory(prefix="dualeye-stt-") as temp:
                wav_path = Path(temp) / "utterance.wav"
                with wave.open(str(wav_path), "wb") as wav:
                    wav.setnchannels(1); wav.setsampwidth(sample_width); wav.setframerate(sample_rate); wav.writeframes(pcm)
                model = WhisperModel(os.getenv("KOALABYTE_WHISPER_MODEL", "tiny.en"), device="cpu", compute_type="int8")
                segments, _ = model.transcribe(str(wav_path), beam_size=1)
                return " ".join(segment.text.strip() for segment in segments).strip()
        except Exception:
            return ""

    def _tts_pcm(self, text: str) -> bytes:
        executable = shutil.which("espeak-ng") or shutil.which("espeak")
        if not executable or not text.strip():
            return b""
        try:
            result = subprocess.run([executable, "--stdout", "-v", os.getenv("KILLERKOALA_ESPEAK_VOICE", "en-au"), text], capture_output=True, timeout=20, check=True)
            with wave.open(Path(tempfile.mkstemp(suffix=".wav")[1]).as_posix(), "wb"):
                pass
            import io
            with wave.open(io.BytesIO(result.stdout), "rb") as wav:
                data = wav.readframes(wav.getnframes())
                if wav.getnchannels() > 1:
                    data = audioop.tomono(data, wav.getsampwidth(), 0.5, 0.5)
                if wav.getsampwidth() != 2:
                    data = audioop.lin2lin(data, wav.getsampwidth(), 2)
                if wav.getframerate() != 16000:
                    data, _ = audioop.ratecv(data, 2, 1, wav.getframerate(), 16000, None)
                return data
        except Exception:
            return b""

    def _play_response(self, text: str, channel: str) -> None:
        pcm = self._tts_pcm(text)
        self._heltec_speech(True, text, channel)
        if pcm:
            self._fanout_face("speaking", text, 8000)
            for offset in range(0, len(pcm), 1024):
                chunk = pcm[offset: offset + 1024]
                self._write_json({"type": "audio_pcm", "pcm_s16le_mono_b64": base64.b64encode(chunk).decode("ascii"), "message": text[:48], "end": offset + len(chunk) >= len(pcm)})
        else:
            self._write_json({"type": "pi_execution_result", "status": "success", "message": text, "audio_available": False})
        self._heltec_speech(False, "", channel)

    def _menu_preview(self, phrase: str) -> Optional[dict[str, Any]]:
        parsed = parse_voice_command(phrase, require_wake_word=True)
        action = parsed.menu_action
        if action is None:
            return None
        payload = {
            "type": "menu_sync", "event_type": "select", "selected_position": 1, "total_items": 1,
            "selected_label": action.label, "selected_command": action.command, "selected_group": action.group,
            "source": "pi-companion", "execution_owner": "raspberry-pi",
        }
        self._write_json(payload)
        self._fanout_face("action", action.label, 8000)
        return payload

    def _route_phrase(self, event: ESP32DualEyeVoiceEvent) -> Dict[str, Any]:
        self._fanout_face("thinking", event.phrase, 8000)
        menu_preview = self._menu_preview(event.phrase)
        result = route_voice_phrase(event.phrase, require_wake_word=True, output_dir=self.output_dir, xp_path=self.xp_path)
        result_data = _jsonable(result)
        status = str(result_data.get("status", "error"))
        error = str(result_data.get("error") or "")
        channel = "pi-execution"
        if status == "blocked" and "no supported module or menu action" in error.lower():
            ai = companion_response("banter", user_text=event.phrase, context={"status": "ai_fallback"}, flexible=True)
            message = ai.text
            status = "ai_response"
            channel = "pi-ai"
            result_data = {"status": status, "phrase": event.phrase, "companion_line": message, "ai": asdict(ai)}
        else:
            message = str(result_data.get("companion_line") or result_data.get("error") or status)
        success = status in {"success", "ai_response"}
        self._write_json({"type": "pi_execution_result", "request_id": event.request_id, "status": "success" if success else status, "message": message, "menu_preview": menu_preview, "result": result_data})
        self._fanout_face("success" if success else "error", message, 5200)
        self._play_response(message, channel)
        return {"event": asdict(event), "result": result_data}

    def _finish_audio(self, payload: Dict[str, Any]) -> Optional[ESP32DualEyeVoiceEvent]:
        request_id = str(payload.get("request_id", ""))
        pcm = bytes(self._audio.pop(request_id, b""))
        meta = self._audio_meta.pop(request_id, {})
        phrase = self._transcribe_pcm(pcm, int(meta.get("sample_rate", 16000)), int(meta.get("sample_width", 2)))
        if not phrase:
            self._write_json({"type": "pi_execution_result", "request_id": request_id, "status": "error", "message": "I couldn't make out that command."})
            self._fanout_face("error", "voice not understood", 3200)
            return None
        if not _wake_detected(phrase):
            self._write_json({"type": "pi_execution_result", "request_id": request_id, "status": "ignored", "message": "wake phrase not detected", "transcript": phrase})
            self._fanout_face("idle", "calm", 1200)
            return None
        event = ESP32DualEyeVoiceEvent(type="voice_command", phrase=phrase, source="esp32_s3_es7210_stt", request_id=request_id, payload={"transcript": phrase, **payload})
        self.events.put(event); self._log_event(event); return event

    def handle_payload(self, payload: Dict[str, Any]) -> Optional[ESP32DualEyeVoiceEvent]:
        if self._is_duplicate(payload):
            return None
        payload_type = str(payload.get("type", ""))
        if payload_type in {"node_status", "voice_backend", "voice_backend_heartbeat", "voice_stack", "boot"}:
            status = ESP32DualEyeMicStatus(status=str(payload.get("audio_status") or payload.get("status") or "reported"), ready=bool(payload.get("mic_ready", payload.get("ready", False))), port=self.port, reason=str(payload.get("reason", "")), builtin_mic_present=bool(payload.get("builtin_mic_present", True)), pins_configured=payload.get("pins_configured"), payload=payload)
            self._write_status(asdict(status)); return None
        if payload_type == "audio_utterance_start":
            request_id = str(payload.get("request_id", "")); self._audio[request_id] = bytearray(); self._audio_meta[request_id] = dict(payload)
            self._fanout_face("listening", "listening", 8000); return None
        if payload_type == "audio_pcm_chunk":
            request_id = str(payload.get("request_id", "")); encoded = str(payload.get("pcm_s16le_mono_b64", ""))
            if request_id in self._audio and encoded and len(self._audio[request_id]) < 512000:
                self._audio[request_id].extend(base64.b64decode(encoded, validate=False))
            return None
        if payload_type == "audio_utterance_end":
            return self._finish_audio(payload)
        if payload_type not in {"voice_wake", "voice_command", "pi_execute_request", "pi_ai_request"}:
            return None
        phrase = str(payload.get("phrase") or "").strip()
        if not phrase:
            return None
        event = ESP32DualEyeVoiceEvent(type="voice_command", phrase=phrase, source=str(payload.get("source") or "esp32_s3_dualeye"), wake_word=str(payload.get("wake_word") or "killerkoala"), request_id=str(payload.get("request_id") or ""), payload=payload)
        self.events.put(event); self._log_event(event); return event

    def _read_udp(self) -> Optional[Dict[str, Any]]:
        if self._udp is None:
            return None
        try:
            data, peer = self._udp.recvfrom(8192)
        except BlockingIOError:
            return None
        self._udp_peer = peer; self._last_transport = "udp"
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

    def run(self, seconds: Optional[float] = None, once: bool = False) -> Dict[str, Any]:
        self.open(); routed: list[Dict[str, Any]] = []; started = time.time()
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
        payload = {"status": "ESP32_DUALEYE_INTEGRATED_BRIDGE_COMPLETE", "port": self.port, "udp_port": self.udp_port, "routed_count": len(routed), "routed": routed, "updated_at": time.time()}
        self._write_status(payload); return payload
