from __future__ import annotations

import json
import os
import queue
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from .killerkoala_voice_control import DEFAULT_OUTPUT_DIR, DEFAULT_XP_PATH
from .killerkoala_voice_router import route_voice_phrase

DEFAULT_BAUD = 115200
DEFAULT_STATUS_PATH = Path("logs/killerkoala/esp32_dualeye_mic_status.json")
DEFAULT_EVENTS_PATH = Path("logs/killerkoala/esp32_dualeye_voice_events.jsonl")


@dataclass
class ESP32DualEyeVoiceEvent:
    type: str
    phrase: str
    source: str
    wake_word: str = "killerkoala"
    mic: str = "esp32_s3_dualeye_builtin_mic"
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


class ESP32DualEyeVoiceBridge:
    """Bridge ESP32-S3 DualEye built-in mic events into KillerKoala voice commands.

    The DualEye firmware owns the board microphone front-end and emits JSON over
    USB CDC serial. The Pi listens for ``voice_wake`` and ``voice_command``
    messages, then routes phrases through the combined KillerKoala voice router.
    This includes both direct AI/voice modules and menu/submenu launch syntax:

        killerkoala run <menu item or command>
        killerkoala open <menu item or command>
    """

    def __init__(
        self,
        port: Optional[str] = None,
        baud: int = DEFAULT_BAUD,
        status_path: str | Path = DEFAULT_STATUS_PATH,
        events_path: str | Path = DEFAULT_EVENTS_PATH,
        output_dir: str | Path = DEFAULT_OUTPUT_DIR,
        xp_path: str | Path = DEFAULT_XP_PATH,
        serial_timeout: float = 0.25,
    ) -> None:
        self.port = port or default_esp32_port()
        self.baud = baud
        self.status_path = Path(status_path)
        self.events_path = Path(events_path)
        self.output_dir = Path(output_dir)
        self.xp_path = Path(xp_path)
        self.serial_timeout = serial_timeout
        self._serial = None
        self.events: "queue.Queue[ESP32DualEyeVoiceEvent]" = queue.Queue()

    def open(self) -> None:
        try:
            import serial  # type: ignore
        except Exception as exc:  # pragma: no cover - runtime platform specific
            raise RuntimeError("pyserial is required for ESP32-S3 DualEye mic bridge") from exc
        self._serial = serial.Serial(self.port, self.baud, timeout=self.serial_timeout)
        time.sleep(0.2)
        self.request_mic_status()

    def close(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            finally:
                self._serial = None

    def _write_json(self, payload: Dict[str, Any]) -> None:
        if self._serial is None:
            raise RuntimeError("ESP32 serial bridge is not open")
        self._serial.write((json.dumps(payload, sort_keys=True) + "\n").encode("utf-8"))
        self._serial.flush()

    def request_mic_status(self) -> None:
        self._write_json({"type": "mic_status", "request": "esp32_s3_dualeye_builtin_mic"})

    def simulate_voice_command(self, phrase: str = "killerkoala voice commands") -> None:
        self._write_json({"type": "simulate_voice_command", "phrase": phrase})

    def _write_status(self, payload: Dict[str, Any]) -> None:
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        self.status_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _log_event(self, event: ESP32DualEyeVoiceEvent) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(event), sort_keys=True) + "\n")

    def _normalize_voice_phrase(self, payload: Dict[str, Any]) -> str:
        phrase = str(payload.get("phrase") or "").strip()
        wake_word = str(payload.get("wake_word") or "killerkoala").strip() or "killerkoala"
        if not phrase:
            phrase = f"{wake_word} voice commands"
        if phrase.strip().lower() == wake_word.lower():
            phrase = f"{wake_word} voice commands"
        return phrase

    def handle_payload(self, payload: Dict[str, Any]) -> Optional[ESP32DualEyeVoiceEvent]:
        payload_type = str(payload.get("type", ""))
        if payload_type in {"voice_backend", "voice_backend_heartbeat", "voice_stack", "boot"}:
            status = ESP32DualEyeMicStatus(
                status=str(payload.get("status") or payload.get("mic_status") or "reported"),
                ready=bool(payload.get("ready", payload.get("mic_ready", False))),
                port=self.port,
                reason=str(payload.get("reason", "")),
                builtin_mic_present=bool(payload.get("builtin_mic_present", True)),
                pins_configured=payload.get("pins_configured") if "pins_configured" in payload else None,
                payload=payload,
            )
            self._write_status(asdict(status))
            return None

        if payload_type not in {"voice_wake", "voice_command"}:
            return None

        phrase = self._normalize_voice_phrase(payload)
        event = ESP32DualEyeVoiceEvent(
            type=payload_type,
            phrase=phrase,
            source=str(payload.get("source") or "esp32_s3_dualeye_builtin_mic"),
            wake_word=str(payload.get("wake_word") or "killerkoala"),
            mic=str(payload.get("mic") or "esp32_s3_dualeye_builtin_mic"),
            payload=payload,
        )
        self.events.put(event)
        self._log_event(event)
        return event

    def read_once(self) -> Optional[ESP32DualEyeVoiceEvent]:
        if self._serial is None:
            raise RuntimeError("ESP32 serial bridge is not open")
        line = self._serial.readline().decode("utf-8", errors="ignore").strip()
        if not line:
            return None
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return self.handle_payload(payload)

    def route_event(self, event: ESP32DualEyeVoiceEvent) -> Dict[str, Any]:
        result = route_voice_phrase(event.phrase, require_wake_word=True, output_dir=self.output_dir, xp_path=self.xp_path)
        return {"event": asdict(event), "result": asdict(result)}

    def run(self, seconds: Optional[float] = None, once: bool = False) -> Dict[str, Any]:
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
        finally:
            self.close()
        payload = {"status": "ESP32_DUALEYE_VOICE_BRIDGE_COMPLETE", "port": self.port, "routed_count": len(routed), "routed": routed, "updated_at": time.time()}
        self._write_status(payload)
        return payload
