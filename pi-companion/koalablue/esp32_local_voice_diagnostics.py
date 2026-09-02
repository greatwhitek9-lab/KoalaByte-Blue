from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

LOCAL_VOICE_STATUS_PATH = Path(
    os.getenv(
        "KOALABYTE_ESP32_LOCAL_VOICE_STATUS_PATH",
        "logs/killerkoala/esp32_dualeye_local_voice_status.json",
    )
)
LOCAL_VOICE_EVENTS_PATH = Path(
    os.getenv(
        "KOALABYTE_ESP32_LOCAL_VOICE_EVENTS_PATH",
        "logs/killerkoala/esp32_dualeye_local_voice_events.jsonl",
    )
)
LOCAL_VOICE_TYPES = {
    "local_voice_status",
    "local_voice_detected",
    "local_ai_response",
}


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _append_event(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def install_esp32_local_voice_diagnostics(bridge_cls: type[Any]) -> type[Any]:
    """Persist firmware-local recognizer and voice-response diagnostics.

    The production bridge historically ignored ``local_voice_status``,
    ``local_voice_detected`` and ``local_ai_response`` because they are not Pi
    voice-routing requests. Keeping them visible makes failures in the ES7210
    microphone, ESP-SR/MultiNet model, wake recognition, and local speaker bank
    independently diagnosable without opening a second serial monitor.
    """

    if getattr(bridge_cls, "_koalabyte_local_voice_diagnostics_installed", False):
        return bridge_cls

    original_handle_payload = bridge_cls.handle_payload

    def handle_payload(instance: Any, payload: dict[str, Any]) -> Any:
        payload_type = str(payload.get("type") or "").strip().lower()
        if payload_type in LOCAL_VOICE_TYPES:
            record: dict[str, Any] = {
                "captured_at": time.time(),
                "transport": str(getattr(instance, "_last_transport", "unknown")),
                **dict(payload),
            }
            _append_event(LOCAL_VOICE_EVENTS_PATH, record)
            if payload_type == "local_voice_status":
                _atomic_write_json(LOCAL_VOICE_STATUS_PATH, record)
        return original_handle_payload(instance, payload)

    bridge_cls.handle_payload = handle_payload
    bridge_cls._koalabyte_local_voice_diagnostics_installed = True
    return bridge_cls


__all__ = [
    "LOCAL_VOICE_STATUS_PATH",
    "LOCAL_VOICE_EVENTS_PATH",
    "LOCAL_VOICE_TYPES",
    "install_esp32_local_voice_diagnostics",
]
