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
USB_PORT_HINTS = ("heltec", "t114", "ht-n5262", "nrf52840", "adafruit", "usbmodem", "ttyacm")


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


def _candidate_usb_ports() -> list[str]:
    ports: list[str] = []
    for pattern in ("/dev/serial/by-id/*", "/dev/ttyACM*", "/dev/ttyUSB*", "/dev/cu.usbmodem*", "/dev/cu.usbserial*"):
        ports.extend(sorted(glob.glob(pattern)))
    seen: set[str] = set()
    unique: list[str] = []
    for port in ports:
        if port not in seen:
            seen.add(port)
            unique.append(port)
    return unique


def _discover_heltec_usb_port() -> str:
    for port in _candidate_usb_ports():
        lower = port.lower()
        if any(hint in lower for hint in USB_PORT_HINTS):
            return port
    return ""


def _serial_write(port: str, baud: int, payload: dict) -> bool:
    if not port:
        return False
    try:
        import serial  # type: ignore
        with serial.Serial(port, baudrate=baud, timeout=0.15, write_timeout=0.35) as ser:  # type: ignore[attr-defined]
            ser.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
            ser.flush()
        return True
    except Exception:
        return False


def emit_face(state: str, message: str = "", *, enabled: bool = True, duration_ms: int = 4500) -> dict:
    payload = build_face_payload(state, message, enabled=enabled, duration_ms=duration_ms)
    esp32_port = os.getenv("KOALABYTE_ESP32_FACE_PORT", os.getenv("ESP32_PORT", "")).strip()
    heltec_port = os.getenv("KOALABYTE_HELTEC_USB_PORT", os.getenv("KOALABYTE_HELTEC_FACE_PORT", os.getenv("HELTEC_PORT", ""))).strip()
    if not heltec_port:
        heltec_port = _discover_heltec_usb_port()
    baud = int(os.getenv("KOALABYTE_FACE_BAUD", str(DEFAULT_BAUD)))
    disabled = bool(os.getenv("KOALABYTE_FACE_DISABLED"))
    wrote_esp32 = False if disabled else _serial_write(esp32_port, baud, payload)
    wrote_heltec = False if disabled else _serial_write(heltec_port, baud, payload)
    DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        "payload": payload,
        "esp32_port": esp32_port,
        "heltec_usb_port": heltec_port,
        "heltec_connection": "usb-cdc",
        "wrote_esp32": wrote_esp32,
        "wrote_heltec": wrote_heltec,
        "disabled": disabled,
    }
    (DEFAULT_LOG_DIR / "last_face_command.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    with (DEFAULT_LOG_DIR / "face_commands.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(result, sort_keys=True) + "\n")
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
    if stopped:
        return emit_face("error", message, duration_ms=5200)
    return emit_face("speaking" if success else "error", message, duration_ms=5600)


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
