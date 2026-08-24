from __future__ import annotations

import glob
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Mapping, Optional

from .bounded_log import append_jsonl
from .runtime_log_hardening import atomic_write_json


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_ROOT = REPO_ROOT / "logs" / "hdmi"
VALID_DISPLAY_MODES = {"koalabyte", "desktop"}
DISPLAY_EVENT_TYPES = {
    "ai_face",
    "ai_face_sync",
    "display_fault",
    "killerkoala_face",
    "killerkoala_speech",
    "koalagotchi_status",
    "local_speech_state",
    "menu_sync",
    "node_error",
    "pi_execution_result",
    "system_fault",
}
ERROR_STATES = {
    "alarmed",
    "error",
    "failed",
    "failure",
    "fault",
    "node_error",
    "system_fault",
}
ERROR_CLEAR_STATES = {"cleared", "error_clear", "recovered", "resolved"}
ACTION_DISPLAY_MODES = {"action_status", "jungle_loading_banner", "koalagotchi_action"}

_DISPLAY_FIELDS = {
    "action_title",
    "active",
    "animation",
    "brightness",
    "channel",
    "companion_line",
    "contentment",
    "display_mode",
    "duration_ms",
    "enabled",
    "error",
    "event_type",
    "expression",
    "frame_index",
    "health",
    "intensity",
    "koalagotchi_display_state",
    "left_eye",
    "menu_name",
    "menu_title",
    "message",
    "mood",
    "mouth_expression",
    "persistent_koalagotchi_mode",
    "right_eye",
    "scroll_offset",
    "selected_command",
    "selected_enabled",
    "selected_group",
    "selected_index",
    "selected_label",
    "selected_position",
    "source",
    "speech_motion",
    "state",
    "status",
    "subject",
    "tone",
    "total_items",
    "ts",
    "type",
    "updated_at",
    "visible_items",
    "visible_rows",
}
_VISIBLE_ITEM_FIELDS = {
    "description",
    "enabled",
    "group",
    "index",
    "label",
    "position",
    "selected",
}


def _state_root(root: str | Path | None = None) -> Path:
    if root is not None:
        return Path(root)
    configured = os.getenv("KOALABYTE_HDMI_STATE_DIR", "").strip()
    return Path(configured) if configured else DEFAULT_STATE_ROOT


def _clean_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return " ".join(value.split())[:512]
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return str(value)[:512]


def sanitize_display_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Keep the HDMI state useful without copying credentials or audio buffers."""

    clean: dict[str, Any] = {}
    for key in _DISPLAY_FIELDS:
        if key not in payload:
            continue
        value = payload[key]
        if key == "visible_items":
            rows: list[dict[str, Any]] = []
            if isinstance(value, list):
                for item in value[:10]:
                    if not isinstance(item, Mapping):
                        continue
                    rows.append(
                        {
                            field: _clean_scalar(item[field])
                            for field in _VISIBLE_ITEM_FIELDS
                            if field in item
                        }
                    )
            clean[key] = rows
        else:
            clean[key] = _clean_scalar(value)
    return clean


def display_channel(payload: Mapping[str, Any]) -> Optional[str]:
    payload_type = str(payload.get("type") or "").strip().lower()
    state = str(payload.get("state") or payload.get("status") or "").strip().lower()
    display_mode = str(payload.get("display_mode") or "").strip().lower()

    if payload_type not in DISPLAY_EVENT_TYPES and not (
        state in ERROR_STATES or state in ERROR_CLEAR_STATES
    ):
        return None
    if (
        state in ERROR_STATES
        or state in ERROR_CLEAR_STATES
        or payload_type.endswith("_fault")
        or payload_type == "node_error"
    ):
        return "error"
    if payload_type in {"killerkoala_speech", "local_speech_state"}:
        return "speech"
    if payload_type == "koalagotchi_status":
        return "koalagotchi"
    if display_mode in ACTION_DISPLAY_MODES or payload_type == "pi_execution_result":
        return "action"
    if payload_type == "menu_sync":
        return "menu"
    if payload_type in {"ai_face", "ai_face_sync", "killerkoala_face"}:
        return "face"
    return None


def publish_display_event(
    payload: Mapping[str, Any],
    *,
    channel: str | None = None,
    root: str | Path | None = None,
) -> Optional[dict[str, Any]]:
    """Publish a sanitized display snapshot without touching either board tty."""

    resolved_channel = channel or display_channel(payload)
    if not resolved_channel:
        return None
    resolved_channel = str(resolved_channel).strip().lower()
    if not resolved_channel.replace("_", "").isalnum():
        raise ValueError(f"invalid HDMI display channel: {resolved_channel}")

    now = time.time()
    clean = sanitize_display_payload(payload)
    duration_ms = max(0, int(clean.get("duration_ms") or 0))
    record: dict[str, Any] = {
        "channel": resolved_channel,
        "payload": clean,
        "updated_at": now,
    }
    if duration_ms:
        record["expires_at"] = now + duration_ms / 1000.0

    state_root = _state_root(root)
    atomic_write_json(state_root / "state" / f"{resolved_channel}.json", record)
    append_jsonl(state_root / "display_events.jsonl", record)
    return record


def _mode_path(root: str | Path | None = None) -> Path:
    return _state_root(root) / "display_mode.json"


def read_display_mode(
    *,
    root: str | Path | None = None,
    default: str = "koalabyte",
) -> str:
    fallback = default if default in VALID_DISPLAY_MODES else "koalabyte"
    path = _mode_path(root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        mode = str(payload.get("mode") or "").strip().lower()
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return fallback
    return mode if mode in VALID_DISPLAY_MODES else fallback


def set_display_mode(
    mode: str,
    *,
    source: str = "local-command",
    root: str | Path | None = None,
) -> dict[str, Any]:
    requested = str(mode or "").strip().lower().replace("pi_os", "desktop")
    previous = read_display_mode(root=root)
    if requested == "toggle":
        requested = "desktop" if previous == "koalabyte" else "koalabyte"
    if requested not in VALID_DISPLAY_MODES:
        raise ValueError(
            f"display mode must be koalabyte, desktop, or toggle; got {mode!r}"
        )
    payload = {
        "status": "HDMI_DISPLAY_MODE_UPDATED",
        "mode": requested,
        "previous_mode": previous,
        "source": " ".join(str(source or "local-command").split())[:80],
        "updated_at": time.time(),
    }
    atomic_write_json(_mode_path(root), payload)
    append_jsonl(_state_root(root) / "display_mode_events.jsonl", payload)
    return payload


def display_mode_status(*, root: str | Path | None = None) -> dict[str, Any]:
    path = _mode_path(root)
    mode = read_display_mode(root=root)
    return {
        "status": "HDMI_DISPLAY_MODE_STATUS",
        "mode": mode,
        "koalabyte_visible": mode == "koalabyte",
        "pi_os_visible": mode == "desktop",
        "state_path": str(path),
        "updated_at": time.time(),
    }


def submit_menu_command(
    command: str,
    *,
    source: str = "hdmi",
    root: str | Path | None = None,
) -> dict[str, Any]:
    clean = str(command or "").strip()
    if not clean or len(clean) > 512 or "\x00" in clean or "\n" in clean or "\r" in clean:
        raise ValueError("invalid HDMI menu command")
    payload = {
        "command": clean,
        "source": " ".join(str(source or "hdmi").split())[:80],
        "submitted_at": time.time(),
    }
    queue_dir = _state_root(root) / "commands"
    queue_dir.mkdir(parents=True, exist_ok=True)
    name = f"{time.time_ns():020d}-{os.getpid()}-{uuid.uuid4().hex}.json"
    atomic_write_json(queue_dir / name, payload)
    return payload


def drain_menu_commands(
    *,
    root: str | Path | None = None,
    max_items: int = 32,
) -> list[dict[str, Any]]:
    queue_dir = _state_root(root) / "commands"
    if not queue_dir.exists():
        return []
    commands: list[dict[str, Any]] = []
    for path in sorted(queue_dir.glob("*.json"))[: max(1, int(max_items))]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and str(payload.get("command") or "").strip():
                commands.append(payload)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
        finally:
            path.unlink(missing_ok=True)
    return commands


def read_channel_snapshots(
    *,
    root: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    state_dir = _state_root(root) / "state"
    if not state_dir.exists():
        return snapshots
    for path in state_dir.glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
        if isinstance(record, dict) and isinstance(record.get("payload"), dict):
            snapshots[path.stem] = record
    return snapshots


def _record_time(record: Mapping[str, Any] | None) -> float:
    if not record:
        return 0.0
    try:
        return float(record.get("updated_at") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _record_active(
    record: Mapping[str, Any] | None,
    *,
    now: float,
    default_seconds: float,
) -> bool:
    if not record:
        return False
    try:
        expires_at = float(record.get("expires_at") or 0.0)
    except (TypeError, ValueError):
        expires_at = 0.0
    if expires_at:
        return now <= expires_at
    return now - _record_time(record) <= default_seconds


def compose_scene(
    snapshots: Mapping[str, Mapping[str, Any]],
    *,
    mode: str = "koalabyte",
    now: float | None = None,
) -> dict[str, Any]:
    """Resolve independent producer snapshots into one read-only HDMI scene."""

    current_time = time.time() if now is None else float(now)
    if mode == "desktop":
        return {"mode": "desktop", "view": "desktop", "updated_at": current_time}

    def payload(channel: str) -> dict[str, Any]:
        record = snapshots.get(channel, {})
        value = record.get("payload", {}) if isinstance(record, Mapping) else {}
        return dict(value) if isinstance(value, Mapping) else {}

    menu_record = snapshots.get("menu")
    face_record = snapshots.get("face")
    action_record = snapshots.get("action")
    error_record = snapshots.get("error")
    koala_record = snapshots.get("koalagotchi")
    speech_record = snapshots.get("speech")

    menu = payload("menu")
    face = payload("face")
    action = payload("action")
    error = payload("error")
    koalagotchi = payload("koalagotchi")
    speech = payload("speech")

    error_state = str(error.get("state") or error.get("status") or "").lower()
    error_type = str(error.get("type") or "").lower()
    error_active = (
        error_state not in ERROR_CLEAR_STATES
        and (
            error_state in ERROR_STATES
            or error_type.endswith("_fault")
            or error_type == "node_error"
        )
        and _record_active(error_record, now=current_time, default_seconds=30.0)
    )
    speech_active = bool(speech.get("active")) and _record_active(
        speech_record, now=current_time, default_seconds=20.0
    )
    action_active = _record_active(
        action_record, now=current_time, default_seconds=12.0
    )
    koala_fresh = _record_active(
        koala_record, now=current_time, default_seconds=5.0
    )

    latest_normal = max(_record_time(menu_record), _record_time(face_record))
    if error_active:
        view = "error"
    elif action_active and _record_time(action_record) >= latest_normal - 0.05:
        view = "action"
    elif koala_fresh and _record_time(koala_record) > latest_normal:
        view = "koalagotchi"
    elif _record_time(menu_record) >= _record_time(face_record) and menu:
        view = "menu"
    else:
        view = "face"

    if not face:
        face = {
            "type": "killerkoala_face",
            "state": "idle",
            "message": "KillerKoala is watching the canopy",
            "left_eye": "#A54BFF",
            "right_eye": "#32FF71",
        }
    return {
        "mode": "koalabyte",
        "view": view,
        "menu": menu,
        "face": face,
        "action": action,
        "error": error,
        "error_active": error_active,
        "koalagotchi": koalagotchi,
        "koalagotchi_fresh": koala_fresh,
        "speech": speech,
        "speech_active": speech_active,
        "updated_at": current_time,
    }


def hdmi_connected(connector_glob: str | None = None) -> bool:
    policy = os.getenv("KOALABYTE_HDMI", "auto").strip().lower()
    if policy in {"0", "false", "no", "off", "skip"}:
        return False
    if policy in {"1", "true", "yes", "on", "force"}:
        return True
    override = os.getenv("KOALABYTE_HDMI_FORCE", "").strip().lower()
    if override in {"1", "true", "yes", "on"}:
        return True
    if override in {"0", "false", "no", "off"}:
        return False

    patterns = (
        [connector_glob]
        if connector_glob is not None
        else [
            os.getenv("KOALABYTE_HDMI_CONNECTOR_GLOB", "").strip(),
            "/sys/class/drm/card*-HDMI-A-*/status",
            "/sys/class/drm/card*-HDMI-*/status",
        ]
    )
    paths: list[str] = []
    for pattern in patterns:
        if pattern:
            paths.extend(glob.glob(pattern))
    for path in dict.fromkeys(paths):
        try:
            if Path(path).read_text(encoding="utf-8").strip().lower() == "connected":
                return True
        except OSError:
            continue
    return bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))


__all__ = [
    "ACTION_DISPLAY_MODES",
    "DEFAULT_STATE_ROOT",
    "VALID_DISPLAY_MODES",
    "compose_scene",
    "display_channel",
    "display_mode_status",
    "drain_menu_commands",
    "hdmi_connected",
    "publish_display_event",
    "read_channel_snapshots",
    "read_display_mode",
    "sanitize_display_payload",
    "set_display_mode",
    "submit_menu_command",
]
