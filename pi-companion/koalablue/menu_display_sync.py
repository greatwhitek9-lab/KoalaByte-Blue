from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

DEFAULT_STATE_PATH = Path("logs/menu_sync/current_menu_state.json")
DEFAULT_EVENT_PATH = Path("logs/menu_sync/menu_sync_events.jsonl")


def _enabled() -> bool:
    value = os.getenv("KOALABYTE_MENU_SYNC", "auto").strip().lower()
    return value not in {"0", "false", "no", "off", "skip"}


def _tool_port_candidates(kind: str) -> list[str]:
    if kind == "heltec":
        names = [
            "KOALABYTE_HELTEC_MENU_PORT",
            "KOALABYTE_HELTEC_USB_PORT",
            "KOALABYTE_PRIMARY_BLE_PORT",
            "HELTEC_PORT",
        ]
        defaults = ["/dev/koalabyte-heltec"]
    else:
        names = [
            "KOALABYTE_ESP32_MENU_PORT",
            "KOALABYTE_ESP32_FACE_PORT",
            "ESP32_PORT",
        ]
        defaults = ["/dev/koalabyte-esp32-dualeye"]
    candidates: list[str] = []
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            candidates.append(value)
    candidates.extend(defaults)
    deduped: list[str] = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _display_item_payload(index: int, item: Any, selected_index: int) -> dict[str, object]:
    return {
        "index": index,
        "position": index + 1,
        "label": str(getattr(item, "label", "")),
        "command": str(getattr(item, "command", "")),
        "description": str(getattr(item, "description", "")),
        "group": str(getattr(item, "group", "")),
        "enabled": bool(getattr(item, "enabled", True)),
        "selected": index == selected_index,
    }


def build_menu_sync_payload(menu: Any, event: Any | None = None) -> dict[str, object]:
    selected = menu.selected_item
    displayed_selected = menu._display_item(selected) if hasattr(menu, "_display_item") else selected
    visible_items = []
    try:
        visible_items = [_display_item_payload(index, item, menu.selected_index) for index, item in menu.visible_items()]
    except Exception:
        visible_items = []

    payload: dict[str, object] = {
        "type": "menu_sync",
        "source": "koalabyte-blue-pi",
        "menu_name": str(getattr(menu, "menu_name", "main")),
        "menu_title": str(getattr(menu, "menu_title", "Main Canopy")),
        "selected_index": int(getattr(menu, "selected_index", 0)),
        "selected_position": int(getattr(menu, "selected_index", 0)) + 1,
        "total_items": len(getattr(menu, "items", [])),
        "scroll_offset": int(getattr(menu, "scroll_offset", 0)),
        "visible_rows": int(getattr(menu, "visible_rows", 0)),
        "selected_label": str(getattr(displayed_selected, "label", "")),
        "selected_command": str(getattr(displayed_selected, "command", "")),
        "selected_description": str(getattr(displayed_selected, "description", "")),
        "selected_group": str(getattr(displayed_selected, "group", "")),
        "selected_enabled": bool(getattr(displayed_selected, "enabled", True)),
        "visible_items": visible_items,
        "controls": {
            "scroll_up": ["B5", "touch_drag_up", "keyboard_up"],
            "scroll_down": ["B6", "touch_drag_down", "keyboard_down"],
            "select": ["B3", "touch_long_press", "keyboard_enter"],
            "back": ["B2", "keyboard_left"],
            "main_menu": ["B1", "keyboard_m"],
        },
        "execute_hint": "Highlight a menu item, then press B3/select or long-press the touchscreen.",
        "synced_displays": ["heltec-t114", "esp32-s3-dualeye"],
        "updated_at": time.time(),
    }
    if event is not None:
        try:
            event_payload = asdict(event)
        except Exception:
            event_payload = {
                "event_type": str(getattr(event, "event_type", "unknown")),
                "command": str(getattr(event, "command", "")),
            }
        payload["event"] = event_payload
        payload["event_type"] = str(event_payload.get("event_type", "unknown"))
    else:
        payload["event_type"] = "state"
    return payload


def _write_local(payload: dict[str, object]) -> None:
    DEFAULT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_STATE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    with DEFAULT_EVENT_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def _send_json_line(port: str, payload: dict[str, object]) -> tuple[bool, str]:
    if not port or not Path(port).exists():
        return False, "port_missing"
    line = json.dumps(payload, separators=(",", ":")) + "\n"
    try:
        import serial  # type: ignore

        baud = int(os.getenv("KOALABYTE_MENU_SYNC_BAUD", os.getenv("SERIAL_BAUD", "115200")))
        with serial.Serial(port, baudrate=baud, timeout=0.05, write_timeout=0.25) as ser:
            ser.write(line.encode("utf-8"))
            ser.flush()
        return True, "sent"
    except Exception as exc:
        return False, f"send_failed:{exc}"


def _heltec_face_payload(payload: dict[str, object]) -> dict[str, object]:
    position = int(payload.get("selected_position", 1))
    total = int(payload.get("total_items", 1))
    label = str(payload.get("selected_label", "Menu"))
    command = str(payload.get("selected_command", ""))
    event_type = str(payload.get("event_type", "highlight"))
    message = f"{position:02d}/{max(total, 1):02d} {label}"
    return {
        "type": "killerkoala_face",
        "state": "menu_select" if event_type in {"select", "touch_long_press_select"} else "menu_highlight",
        "message": message[:92],
        "menu_sync": True,
        "selected_label": label,
        "selected_command": command,
        "event_type": event_type,
        "duration_ms": 60000,
        "enabled": True,
    }


def _esp32_menu_payload(payload: dict[str, object]) -> dict[str, object]:
    wire_payload = dict(payload)
    # Keep the serial line compact for the ESP32-S3 parser. The Pi still logs the
    # full visible item list locally under logs/menu_sync/current_menu_state.json.
    wire_payload.pop("visible_items", None)
    return wire_payload


def sync_menu_state(menu: Any, event: Any | None = None) -> dict[str, object]:
    payload = build_menu_sync_payload(menu, event)
    _write_local(payload)
    if not _enabled():
        payload["sync_status"] = "disabled"
        DEFAULT_STATE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return payload

    results: dict[str, list[dict[str, object]]] = {"heltec": [], "esp32": []}
    for kind in ("heltec", "esp32"):
        if kind == "heltec":
            wire_payload = _heltec_face_payload(payload)
            wire_payload["target_display"] = "heltec-t114"
        else:
            wire_payload = _esp32_menu_payload(payload)
            wire_payload["target_display"] = "esp32-s3-dualeye"
        for port in _tool_port_candidates(kind):
            sent, status = _send_json_line(port, wire_payload)
            results[kind].append({"port": port, "sent": sent, "status": status})
            if sent:
                break
    payload["sync_results"] = results
    DEFAULT_STATE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload
