from __future__ import annotations

import glob
import json
import os
import time
from pathlib import Path
from typing import Optional

DEFAULT_LOG_DIR = Path("logs/killerkoala_face")
DEFAULT_BAUD = 115200
KOALAGOTCHI_DISPLAY_COMMANDS = {"eucalyptus_mode", "boomerang"}
NON_ACTION_COMMANDS = {"quit", "shutdown_confirm", "settings", "buttons", "level/status", "wake killerkoala"}
HELTEC_USB_PORT_HINTS = ("heltec", "t114", "ht-n5262", "nrf52840", "adafruit")
ESP32_USB_PORT_HINTS = ("esp32", "dualeye", "cp210", "ch340", "wchusbserial")


def _short(text: str, limit: int = 68) -> str:
    clean = " ".join(str(text or "").split())
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"


def build_face_payload(state: str, message: str = "", enabled: bool = True, duration_ms: int = 4500) -> dict:
    return {
        "type": "killerkoala_face",
        "enabled": enabled,
        "state": (state or "listening").strip().lower(),
        "message": _short(message),
        "duration_ms": max(250, int(duration_ms)),
        "left_eye": "#A54BFF",
        "right_eye": "#32FF71",
        "brightness": 100,
        "source": "pi-companion",
        "transport": "usb-cdc",
        "ts": time.time(),
    }


def select_koalagotchi_expression(health: int, mood: str = "") -> str:
    """Map the shared Koalagotchi health/mood state to a T114 mouth sequence."""

    score = max(0, min(100, int(health)))
    normalized = " ".join(str(mood or "").lower().split())
    if score <= 25 or any(word in normalized for word in ("cranky", "angry", "snarl", "hostile")):
        return "snarl"
    if any(word in normalized for word in ("eating", "feeding", "chew")):
        return "bite"
    if any(word in normalized for word in ("patrolling", "mischief", "boomerang", "sideways")):
        return "sideways_grin"
    return "smile"


def build_koalagotchi_status_payload(health: int, mood: str = "") -> dict:
    score = max(0, min(100, int(health)))
    clean_mood = _short(mood or "calm", 40).lower()
    return {
        "type": "koalagotchi_status",
        "health": score,
        "contentment": score,
        "mood": clean_mood,
        "expression": select_koalagotchi_expression(score, clean_mood),
        "target_display": "heltec-t114",
        "source": "pi-companion",
    }


def build_speech_payload(active: bool, message: str = "", channel: str = "pi-ai") -> dict:
    """Build the compact T114 speech lifecycle command used by either AI voice."""

    return {
        "type": "killerkoala_speech",
        "active": bool(active),
        "message": _short(message, 48) if active else "",
        "channel": _short(channel or "pi-ai", 20).lower(),
        "target_display": "heltec-t114",
        "source": "pi-companion",
    }


def build_heltec_loading_payload(frame: str, action_title: str = "", duration_ms: int = 1400) -> dict:
    """Build a compact Koalagotchi frame that fits the T114 USB command buffer."""

    frame_index = max(0, sum(1 for ch in str(frame) if ch.isalpha()) - 1)

    return {
        "type": "killerkoala_face",
        "enabled": True,
        "state": "koalagotchi_action",
        "message": "",
        "duration_ms": max(250, int(duration_ms)),
        "display_mode": "koalagotchi_action",
        "target_display": "heltec-t114",
        "action_title": _short(action_title, 24),
        "frame_index": frame_index,
    }


def build_esp32_loading_eyes_payload(action_title: str = "", duration_ms: int = 1400) -> dict:
    """Use the existing DualEye menu renderer to show the executing action."""

    label = _short(action_title or "KoalaByte action", 72)
    return {
        "type": "menu_sync",
        "source": "pi-companion",
        "menu_name": "action",
        "menu_title": "EXECUTING",
        "event_type": "select",
        "selected_position": 1,
        "total_items": 1,
        "selected_label": label,
        "selected_command": "executing_action",
        "selected_group": "KOALABYTE ACTION",
        "selected_enabled": True,
        "display_mode": "action_status",
        "target_display": "esp32-s3-dualeye",
        "animation": "pulse",
        "duration_ms": max(250, int(duration_ms)),
        "loading_text_on_eyes": False,
    }


def _candidate_usb_ports() -> list[str]:
    ports: list[str] = []
    for pattern in (
        "/dev/serial/by-id/*",
        "/dev/ttyACM*",
        "/dev/ttyUSB*",
        "/dev/cu.usbmodem*",
        "/dev/cu.usbserial*",
    ):
        ports.extend(sorted(glob.glob(pattern)))
    seen: set[str] = set()
    unique: list[str] = []
    for port in ports:
        if port not in seen:
            seen.add(port)
            unique.append(port)
    return unique


def _discover_usb_port(kind: str) -> str:
    stable = "/dev/koalabyte-heltec" if kind == "heltec" else "/dev/koalabyte-esp32-dualeye"
    if Path(stable).exists():
        return stable
    hints = HELTEC_USB_PORT_HINTS if kind == "heltec" else ESP32_USB_PORT_HINTS
    for port in _candidate_usb_ports():
        lower = port.lower()
        if any(hint in lower for hint in hints):
            return port
    return ""


def _serial_write(port: str, baud: int, payload: dict) -> bool:
    if not port:
        return False
    try:
        import serial  # type: ignore

        # Configure the port while closed so DTR/RTS stay inactive when it opens.
        # This avoids ESP32 auto-reset circuits firing during repeated loading frames.
        ser = serial.Serial()  # type: ignore[attr-defined]
        ser.port = port
        ser.baudrate = baud
        ser.timeout = 0.15
        ser.write_timeout = 0.35
        ser.dsrdtr = False
        ser.rtscts = False
        ser.dtr = False
        ser.rts = False
        try:
            ser.open()
            ser.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
            ser.flush()
        finally:
            if ser.is_open:
                ser.close()
        return True
    except Exception:
        return False


def _resolve_ports() -> tuple[str, str]:
    esp32_port = os.getenv("KOALABYTE_ESP32_FACE_PORT", os.getenv("ESP32_PORT", "")).strip()
    heltec_port = os.getenv(
        "KOALABYTE_HELTEC_USB_PORT",
        os.getenv("KOALABYTE_HELTEC_FACE_PORT", os.getenv("HELTEC_PORT", "")),
    ).strip()
    if not esp32_port:
        esp32_port = _discover_usb_port("esp32")
    if not heltec_port:
        heltec_port = _discover_usb_port("heltec")
    return esp32_port, heltec_port


def _write_result_log(filename: str, result: dict) -> None:
    DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    (DEFAULT_LOG_DIR / filename).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    with (DEFAULT_LOG_DIR / "face_commands.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(result, sort_keys=True) + "\n")


def _publish_hdmi(payload: dict) -> None:
    try:
        from .hdmi_display_state import publish_display_event

        publish_display_event(payload)
    except Exception:
        # HDMI is a read-only optional consumer and cannot block face fan-out.
        pass


def emit_face(state: str, message: str = "", *, enabled: bool = True, duration_ms: int = 4500) -> dict:
    payload = build_face_payload(state, message, enabled=enabled, duration_ms=duration_ms)
    _publish_hdmi(payload)
    esp32_port, heltec_port = _resolve_ports()
    baud = int(os.getenv("KOALABYTE_FACE_BAUD", str(DEFAULT_BAUD)))
    disabled = bool(os.getenv("KOALABYTE_FACE_DISABLED"))
    wrote_esp32 = False if disabled else _serial_write(esp32_port, baud, payload)
    wrote_heltec = False if disabled else _serial_write(heltec_port, baud, payload)
    result = {
        "mode": "shared_face",
        "payload": payload,
        "esp32_port": esp32_port,
        "heltec_usb_port": heltec_port,
        "heltec_connection": "usb-cdc",
        "wrote_esp32": wrote_esp32,
        "wrote_heltec": wrote_heltec,
        "disabled": disabled,
    }
    _write_result_log("last_face_command.json", result)
    return result


def emit_koalagotchi_status(health: int, mood: str = "") -> dict:
    """Drive the T114 cyber-mouth from the shared Koalagotchi state."""

    payload = build_koalagotchi_status_payload(health, mood)
    _publish_hdmi(payload)
    _, heltec_port = _resolve_ports()
    baud = int(os.getenv("KOALABYTE_FACE_BAUD", str(DEFAULT_BAUD)))
    disabled = bool(os.getenv("KOALABYTE_FACE_DISABLED"))
    wrote_heltec = False if disabled else _serial_write(heltec_port, baud, payload)
    result = {
        "mode": "koalagotchi_mood_mouth",
        "payload": payload,
        "heltec_usb_port": heltec_port,
        "wrote_heltec": wrote_heltec,
        "disabled": disabled,
    }
    _write_result_log("last_koalagotchi_status.json", result)
    return result


def emit_speech_state(active: bool, message: str = "", *, channel: str = "pi-ai") -> dict:
    """Start or stop the T114 speaking mouth for local or Pi-side AI audio."""

    payload = build_speech_payload(active, message, channel)
    _publish_hdmi(payload)
    _, heltec_port = _resolve_ports()
    baud = int(os.getenv("KOALABYTE_FACE_BAUD", str(DEFAULT_BAUD)))
    disabled = bool(os.getenv("KOALABYTE_FACE_DISABLED"))
    wrote_heltec = False if disabled else _serial_write(heltec_port, baud, payload)
    result = {
        "mode": "koalagotchi_speaking_mouth",
        "payload": payload,
        "heltec_usb_port": heltec_port,
        "wrote_heltec": wrote_heltec,
        "disabled": disabled,
    }
    _write_result_log("last_speech_state.json", result)
    return result


def emit_loading_frame(frame: str, action_title: str = "", *, duration_ms: int = 1400) -> dict:
    """Play Koalagotchi on T114 while DualEye names the executing action."""

    heltec_payload = build_heltec_loading_payload(frame, action_title, duration_ms)
    esp32_payload = build_esp32_loading_eyes_payload(action_title, duration_ms)
    _publish_hdmi(heltec_payload)
    _publish_hdmi(esp32_payload)
    esp32_port, heltec_port = _resolve_ports()
    baud = int(os.getenv("KOALABYTE_FACE_BAUD", str(DEFAULT_BAUD)))
    disabled = bool(os.getenv("KOALABYTE_FACE_DISABLED"))
    wrote_heltec = False if disabled else _serial_write(heltec_port, baud, heltec_payload)
    wrote_esp32 = False if disabled else _serial_write(esp32_port, baud, esp32_payload)
    result = {
        "mode": "split_loading",
        "frame": frame,
        "action_title": action_title,
        "heltec_payload": heltec_payload,
        "esp32_payload": esp32_payload,
        "heltec_usb_port": heltec_port,
        "esp32_port": esp32_port,
        "wrote_heltec": wrote_heltec,
        "wrote_esp32": wrote_esp32,
        "heltec_loading_text": False,
        "heltec_koalagotchi_action_active": True,
        "esp32_action_label_active": True,
        "loading_text_on_esp32": False,
        "disabled": disabled,
    }
    _write_result_log("last_loading_command.json", result)
    return result


def clear_face(message: str = "") -> dict:
    return emit_face("hidden", message, enabled=False, duration_ms=500)


def show_wake_face(message: str = "wake word heard") -> dict:
    return emit_face("wake", message, duration_ms=3200)


def show_thinking_face(message: str = "thinking") -> dict:
    return emit_face("thinking", message, duration_ms=5200)


def show_action_face(action_title: str, message: str = "") -> dict:
    return emit_face("action", message or f"{action_title} selected", duration_ms=5200)


def show_speaking_face(message: str, *, success: bool = True, stopped: bool = False) -> dict:
    return emit_speech_state(not stopped and success, message, channel="local-ai")


def should_show_action_face(command: str) -> bool:
    normalized = (command or "").strip().lower()
    if not normalized or normalized in KOALAGOTCHI_DISPLAY_COMMANDS or normalized in NON_ACTION_COMMANDS:
        return False
    if normalized.startswith("eucalyptus "):
        return False
    return True


def emit_action_for_menu_item(label: str, command: str) -> Optional[dict]:
    if not should_show_action_face(command):
        return None
    return show_action_face(label, f"{label} selected")
