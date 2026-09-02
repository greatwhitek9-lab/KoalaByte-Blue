from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .bounded_log import append_jsonl
from .killerkoala_expression import expression_for_face_state
from .runtime_log_hardening import atomic_write_json

DEFAULT_STATE_PATH = Path("logs/menu_sync/current_menu_state.json")
DEFAULT_EVENT_PATH = Path("logs/menu_sync/menu_sync_events.jsonl")


def _enabled() -> bool:
    return os.getenv("KOALABYTE_MENU_SYNC", "auto").strip().lower() not in {
        "0", "false", "no", "off", "skip"
    }


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
        names = ["KOALABYTE_ESP32_MENU_PORT", "KOALABYTE_ESP32_FACE_PORT", "ESP32_PORT"]
        defaults = ["/dev/koalabyte-esp32-dualeye"]
    candidates = [os.getenv(name, "").strip() for name in names]
    candidates.extend(defaults)
    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


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


def _visible_item_payloads(menu: Any) -> list[dict[str, object]]:
    """Normalize visible menu rows from either MenuItem or (index, MenuItem)."""
    scroll_offset = int(getattr(menu, "scroll_offset", 0))
    selected_index = int(getattr(menu, "selected_index", 0))
    rows: list[dict[str, object]] = []
    for ordinal, entry in enumerate(menu.visible_items()):
        index = scroll_offset + ordinal
        item = entry
        if isinstance(entry, tuple) and len(entry) == 2:
            raw_index, item = entry
            try:
                index = int(raw_index)
            except (TypeError, ValueError):
                index = scroll_offset + ordinal
        rows.append(_display_item_payload(index, item, selected_index))
    return rows


def _expression_payload(
    state: str,
    message: str,
    *,
    input_source: str,
    event_type: str = "",
    command: str = "",
) -> dict[str, object]:
    expression = expression_for_face_state(
        state,
        message,
        context={
            "input_source": input_source,
            "event_type": event_type,
            "command": command,
        },
    )
    return {
        **expression.to_payload(),
        "mood": expression.tone,
        "brightness": expression.intensity,
        "face_state": state,
        "expression_source": "pi_button_voice_menu_state",
        "input_source": input_source,
    }


def build_menu_sync_payload(menu: Any, event: Any | None = None) -> dict[str, object]:
    selected = menu.selected_item
    displayed = menu._display_item(selected) if hasattr(menu, "_display_item") else selected
    scroll_offset = int(getattr(menu, "scroll_offset", 0))
    try:
        visible_items = _visible_item_payloads(menu)
    except Exception:
        visible_items = []
    payload: dict[str, object] = {
        "type": "menu_sync",
        "source": "koalabyte-blue-pi",
        "menu_name": str(getattr(menu, "menu_name", "main")),
        "menu_title": str(getattr(menu, "menu_title", "Main Canopy")),
        "display_mode": str(getattr(menu, "display_mode", "menu")),
        "selected_index": int(getattr(menu, "selected_index", 0)),
        "selected_position": int(getattr(menu, "selected_index", 0)) + 1,
        "total_items": len(getattr(menu, "items", [])),
        "scroll_offset": scroll_offset,
        "visible_rows": int(getattr(menu, "visible_rows", 0)),
        "selected_label": str(getattr(displayed, "label", "")),
        "selected_command": str(getattr(displayed, "command", "")),
        "selected_description": str(getattr(displayed, "description", "")),
        "selected_group": str(getattr(displayed, "group", "")),
        "selected_enabled": bool(getattr(displayed, "enabled", True)),
        "visible_items": visible_items,
        "controls": {
            "scroll_up": ["K5", "touch_drag_up", "keyboard_up"],
            "scroll_down": ["K6", "touch_drag_down", "keyboard_down"],
            "select": ["K3", "B3", "touch_long_press", "keyboard_enter"],
            "back": ["K2", "B2", "keyboard_left"],
            "main_menu": ["K1", "B1", "keyboard_m"],
            "power_on_off": ["K7"],
            "reset_reboot": ["K8"],
            "reopen_menu": ["K1", "B1", "touch_double_tap"],
        },
        "execute_hint": "Highlight a menu item, then press K3/select or touchscreen long-press to execute it. B3/select or touchscreen long-press remains a legacy alias.",
        "idle_face_rule": "After 30 seconds idle, the menu returns to animated idle eyes. Confirmed wake-word and voice-command states also show eyes.",
        "synced_displays": ["heltec-t114", "esp32-s3-dualeye", "raspberry-pi-hdmi"],
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
    event_type = str(payload.get("event_type", "state"))
    command = str(payload.get("event", {}).get("command", "")) if isinstance(payload.get("event"), dict) else ""
    input_source = "voice" if "voice" in command or "voice" in event_type else "button_or_menu"
    if event_type in {"select", "touch_long_press_select", "action_running"}:
        face_state = "action"
    elif event_type in {"disabled", "action_error"}:
        face_state = "error"
    elif "keyboard" in event_type:
        face_state = "keyboard"
    else:
        face_state = "navigation"
    payload.update(
        _expression_payload(
            face_state,
            str(payload.get("selected_label", "Menu")),
            input_source=input_source,
            event_type=event_type,
            command=command,
        )
    )
    return payload


def build_ai_face_payload(
    menu: Any,
    event: Any | None = None,
    *,
    state: str = "idle",
    message: str = "KillerKoala is watching the canopy",
) -> dict[str, object]:
    selected = getattr(menu, "selected_item", None)
    payload: dict[str, object] = {
        "type": "ai_face_sync",
        "source": "koalabyte-blue-pi",
        "display_mode": "ai_face",
        "state": state,
        "message": message,
        "selected_label": str(getattr(selected, "label", "")) if selected else "",
        "selected_command": str(getattr(selected, "command", "")) if selected else "",
        "menu_reopen_hint": "Press K1/menu or double-tap touchscreen to reopen the menu. B1 remains a legacy alias.",
        "idle_timeout_seconds": int(getattr(menu, "idle_face_seconds", 30)),
        "synced_displays": ["heltec-t114", "esp32-s3-dualeye", "raspberry-pi-hdmi"],
        "updated_at": time.time(),
    }
    if event is not None:
        try:
            payload["event"] = asdict(event)
            payload["event_type"] = payload["event"].get("event_type", state)  # type: ignore[union-attr]
        except Exception:
            payload["event_type"] = state
    else:
        payload["event_type"] = state
    event_type = str(payload.get("event_type", state))
    payload.update(
        _expression_payload(
            state,
            message,
            input_source="voice" if "voice" in event_type else "button_or_runtime",
            event_type=event_type,
            command=str(payload.get("selected_command", "")),
        )
    )
    return payload


def _write_local(payload: dict[str, object]) -> None:
    atomic_write_json(DEFAULT_STATE_PATH, payload)
    append_jsonl(DEFAULT_EVENT_PATH, payload)
    try:
        from .hdmi_display_state import publish_display_event

        publish_display_event(payload)
    except Exception:
        # HDMI is an optional presentation surface. It must never break the
        # Pi-owned menu or either board's display synchronization.
        pass


def _send_json_line(port: str, payload: dict[str, object]) -> tuple[bool, str]:
    if not port or not Path(port).exists():
        return False, "port_missing"
    try:
        import serial  # type: ignore

        baud = int(os.getenv("KOALABYTE_MENU_SYNC_BAUD", os.getenv("SERIAL_BAUD", "115200")))
        serial_port = serial.Serial()
        serial_port.port = port
        serial_port.baudrate = baud
        serial_port.timeout = 0.05
        serial_port.write_timeout = 0.25
        serial_port.dsrdtr = False
        serial_port.rtscts = False
        serial_port.dtr = False
        serial_port.rts = False
        try:
            serial_port.open()
            serial_port.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8"))
            serial_port.flush()
        finally:
            if serial_port.is_open:
                serial_port.close()
        return True, "sent"
    except Exception as exc:
        return False, f"send_failed:{exc}"


def _heltec_face_payload(payload: dict[str, object]) -> dict[str, object]:
    if payload.get("type") == "ai_face_sync":
        wire = {
            "type": "killerkoala_face",
            "state": str(payload.get("state", "idle"))[:31],
            "message": str(payload.get("message", "KillerKoala idle"))[:92],
            "menu_sync": False,
            "duration_ms": 60000,
            "enabled": True,
        }
        for key, limit in (
            ("tone", 14), ("mouth_expression", 16),
            ("speech_motion", 18),
        ):
            if payload.get(key):
                wire[key] = str(payload[key])[:limit]
        if "intensity" in payload:
            wire["intensity"] = int(payload["intensity"])
        return wire

    # The T114 is the mouth/Koalagotchi surface, never a duplicate text menu.
    # While the Pi menu is active, show Koalagotchi and use the selected label
    # only as the action caption. Idle ai_face_sync restores the animated mouth.
    selected_index = max(0, int(payload.get("selected_index", 0)))
    label = str(payload.get("selected_label", "Menu"))
    wire = {
        "type": "killerkoala_face",
        "state": "action",
        "message": label[:92],
        "display_mode": "koalagotchi_action",
        "frame_index": selected_index % 4,
        "menu_sync": True,
        "selected_label": label[:48],
        "selected_command": str(payload.get("selected_command", ""))[:48],
        "event_type": str(payload.get("event_type", "highlight"))[:31],
        "duration_ms": 30000,
        "enabled": True,
    }
    for key, limit in (("tone", 14), ("mouth_expression", 16)):
        if payload.get(key):
            wire[key] = str(payload[key])[:limit]
    if "intensity" in payload:
        wire["intensity"] = int(payload["intensity"])
    return wire


def _esp32_menu_payload(payload: dict[str, object]) -> dict[str, object]:
    compact_items: list[dict[str, object]] = []
    raw_items = payload.get("visible_items", [])
    if isinstance(raw_items, list):
        for raw in raw_items[:6]:
            if not isinstance(raw, dict):
                continue
            compact_items.append(
                {
                    "position": int(raw.get("position", len(compact_items) + 1)),
                    "label": str(raw.get("label", ""))[:34],
                    "selected": bool(raw.get("selected", False)),
                    "enabled": bool(raw.get("enabled", True)),
                }
            )
    wire = {
        "type": "menu_sync",
        "source": "koalabyte-blue-pi",
        "menu_name": str(payload.get("menu_name", "main"))[:32],
        "menu_title": str(payload.get("menu_title", "Main Canopy"))[:32],
        "event_type": str(payload.get("event_type", "highlight"))[:32],
        "selected_index": int(payload.get("selected_index", 0)),
        "selected_position": int(payload.get("selected_position", 1)),
        "total_items": int(payload.get("total_items", 1)),
        "scroll_offset": int(payload.get("scroll_offset", 0)),
        "visible_rows": min(int(payload.get("visible_rows", len(compact_items))), 6),
        "selected_label": str(payload.get("selected_label", "Menu"))[:72],
        "selected_command": str(payload.get("selected_command", ""))[:72],
        "selected_group": str(payload.get("selected_group", ""))[:48],
        "selected_enabled": bool(payload.get("selected_enabled", True)),
        "visible_items": compact_items,
        "execute_hint": "K3 select | K2 back | K5/K6 scroll",
    }
    for key in (
        "face_state", "mood", "tone", "subject", "intensity", "eye_look",
        "eye_animation", "left_eye", "right_eye", "brightness",
        "expression_source", "input_source",
    ):
        if key in payload:
            wire[key] = payload[key]
    return wire


def _esp32_face_payload(payload: dict[str, object]) -> dict[str, object]:
    wire = {
        "type": "killerkoala_face",
        "state": str(payload.get("state", "idle"))[:31],
        "mood": str(payload.get("mood", payload.get("tone", "neutral")))[:31],
        "message": str(payload.get("message", "KillerKoala idle"))[:92],
        "left_eye": str(payload.get("left_eye", "#A54BFF"))[:10],
        "right_eye": str(payload.get("right_eye", "#32FF71"))[:10],
        "brightness": int(payload.get("brightness", payload.get("intensity", 92))),
        "enabled": True,
        "menu_reopen_hint": "K1/menu or touchscreen double-tap; B1 legacy alias accepted",
    }
    for key in (
        "tone", "subject", "intensity", "eye_look", "eye_animation",
        "expression_source", "input_source",
    ):
        if key in payload:
            wire[key] = payload[key]
    return wire


def _send_to_displays(payload: dict[str, object]) -> dict[str, list[dict[str, object]]]:
    results: dict[str, list[dict[str, object]]] = {"heltec": [], "esp32": []}
    for kind in ("heltec", "esp32"):
        if kind == "heltec":
            wire_payload = _heltec_face_payload(payload)
            wire_payload["target_display"] = "heltec-t114"
        else:
            wire_payload = _esp32_face_payload(payload) if payload.get("type") == "ai_face_sync" else _esp32_menu_payload(payload)
            wire_payload["target_display"] = "esp32-s3-dualeye"
        for port in _tool_port_candidates(kind):
            sent, status = _send_json_line(port, wire_payload)
            results[kind].append({"port": port, "sent": sent, "status": status})
            if sent:
                break
    return results


def _publish(payload: dict[str, object]) -> dict[str, object]:
    if not _enabled():
        payload["sync_status"] = "disabled"
    else:
        payload["sync_results"] = _send_to_displays(payload)
    _write_local(payload)
    return payload


def sync_menu_state(menu: Any, event: Any | None = None) -> dict[str, object]:
    return _publish(build_menu_sync_payload(menu, event))


def sync_ai_face_display(
    menu: Any,
    event: Any | None = None,
    *,
    state: str = "idle",
    message: str = "KillerKoala is watching the canopy",
) -> dict[str, object]:
    return _publish(build_ai_face_payload(menu, event, state=state, message=message))
