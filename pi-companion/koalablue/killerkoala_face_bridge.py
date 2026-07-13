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


def build_heltec_loading_payload(frame: str, action_title: str = "", duration_ms: int = 1400) -> dict:
    payload = build_face_payload("loading", frame, duration_ms=duration_ms)
    payload.update(
        {
            "display_mode": "jungle_loading_banner",
            "target_display": "heltec-t114",
            "action_title": _short(action_title, 48),
            "preserve_eyes": False,
            "banner_frame": _short(frame, 20),
        }
    )
    return payload


def build_esp32_loading_eyes_payload(action_title: str = "", duration_ms: int = 1400) -> dict:
    payload = build_face_payload("loading", "", duration_ms=duration_ms)
    payload.update(
        {
            "display_mode": "ai_eyes",
            "target_display": "esp32-s3-dualeye",
            "action_title": _short(action_title, 48),
            "preserve_eyes": True,
            "eye_animation": "idle",
            "loading_text_on_eyes": False,
        }
    )
    return payload


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

        with serial.Serial(port, baudrate=baud, timeout=0.15, write_timeout=0.35) as ser:  # type: ignore[attr-defined]
            ser.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
            ser.flush()
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


def emit_face(state: str, message: str = "", *, enabled: bool = True, duration_ms: int = 4500) -> dict:
    payload = build_face_payload(state, message, enabled=enabled, duration_ms=duration_ms)
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


def emit_loading_frame(frame: str, action_title: str = "", *, duration_ms: int = 1400) -> dict:
    """Render loading text on the T114 while keeping the DualEye AI eyes active."""

    heltec_payload = build_heltec_loading_payload(frame, action_title, duration_ms)
    esp32_payload = build_esp32_loading_eyes_payload(action_title, duration_ms)
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
        "heltec_loading_text": True,
        "esp32_ai_eyes_active": True,
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
