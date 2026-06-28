from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

LOG_DIR = Path("logs/popup_keyboard")
STATUS_PATH = LOG_DIR / "popup_keyboard_status.json"

LOWER_ROWS = ["abcdefghi", "jklmnopqr", "stuvwxyz", "0123456789", "@._-:/!#$%+?&="]
UPPER_ROWS = [row.upper() if row.isalpha() else row for row in LOWER_ROWS]
SYMBOL_ROWS = ["0123456789", "@._-:/", "!#$%+?&=", "*()[]{}", "'\" ,;"]
SPECIAL_KEYS = ["space", "back", "clear", "shift", "symbols", "voice", "save", "cancel"]

KEYBOARD_TARGETS: dict[str, dict[str, Any]] = {
    "wigle_api_name": {"label": "WiGLE API Name", "secret": False, "placeholder": "username or API name"},
    "wigle_api_token": {"label": "WiGLE API Token", "secret": True, "placeholder": "token"},
    "location_password": {"label": "Create Location Password", "secret": True, "placeholder": "new local password"},
    "location_unlock_password": {"label": "Unlock Current Process", "secret": True, "placeholder": "current local password"},
    "meshtastic_send_message": {"label": "Meshtastic Message", "secret": False, "placeholder": "message text"},
    "meshtastic_send_dest": {"label": "Meshtastic Destination", "secret": False, "placeholder": "optional node id"},
    "bluez_lab_target": {"label": "BlueZ Lab Target", "secret": False, "placeholder": "owned device address"},
}


@dataclass
class PopupKeyboardState:
    target: str
    title: str
    secret: bool = False
    placeholder: str = ""
    text: str = ""
    mode: str = "lower"
    row: int = 0
    col: int = 0
    voice_buffer: str = ""
    message: str = "Use arrows/touch to pick keys. Select adds key. Voice can dictate text."
    opened_at: float = field(default_factory=time.time)

    @property
    def rows(self) -> list[str]:
        if self.mode == "upper":
            return UPPER_ROWS
        if self.mode == "symbols":
            return SYMBOL_ROWS
        return LOWER_ROWS

    @property
    def visible_text(self) -> str:
        if not self.secret:
            return self.text
        return "•" * len(self.text)

    @property
    def selected_key(self) -> str:
        rows = self.rows
        if self.row < len(rows):
            row_text = rows[self.row]
            if not row_text:
                return ""
            return row_text[min(self.col, len(row_text) - 1)]
        special_index = max(0, min(self.col, len(SPECIAL_KEYS) - 1))
        return SPECIAL_KEYS[special_index]

    def move(self, delta_row: int = 0, delta_col: int = 0) -> None:
        max_row = len(self.rows)
        self.row = max(0, min(max_row, self.row + delta_row))
        row_len = len(SPECIAL_KEYS) if self.row == max_row else len(self.rows[self.row])
        self.col = max(0, min(max(0, row_len - 1), self.col + delta_col))

    def select(self) -> dict[str, Any]:
        key = self.selected_key
        if key == "space":
            self.text += " "
            return {"status": "KEYBOARD_EDITING", "action": "space"}
        if key == "back":
            self.text = self.text[:-1]
            return {"status": "KEYBOARD_EDITING", "action": "back"}
        if key == "clear":
            self.text = ""
            return {"status": "KEYBOARD_EDITING", "action": "clear"}
        if key == "shift":
            self.mode = "upper" if self.mode == "lower" else "lower"
            return {"status": "KEYBOARD_EDITING", "action": "shift", "mode": self.mode}
        if key == "symbols":
            self.mode = "symbols" if self.mode != "symbols" else "lower"
            return {"status": "KEYBOARD_EDITING", "action": "symbols", "mode": self.mode}
        if key == "voice":
            self.message = "Voice mode ready: say 'keyboard text ...' or use voice-to-text input."
            return {"status": "KEYBOARD_VOICE_READY", "action": "voice"}
        if key == "save":
            return save_keyboard_value(self.target, self.text)
        if key == "cancel":
            return {"status": "KEYBOARD_CANCELLED", "target": self.target}
        self.text += key
        return {"status": "KEYBOARD_EDITING", "action": "append", "key": key}

    def apply_voice_text(self, text: str, *, append: bool = True) -> dict[str, Any]:
        cleaned = text.strip()
        if append and self.text and cleaned:
            self.text += " " + cleaned
        elif cleaned:
            self.text = cleaned
        self.voice_buffer = cleaned
        return {"status": "KEYBOARD_VOICE_TEXT_APPLIED", "target": self.target, "length": len(cleaned), "secret": self.secret}

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["visible_text"] = self.visible_text
        data["selected_key"] = self.selected_key
        data["rows"] = self.rows
        data["special_keys"] = SPECIAL_KEYS
        if self.secret:
            data["text"] = "<secret-hidden>"
            data["voice_buffer"] = "<secret-hidden>" if self.voice_buffer else ""
        return data


def _write_status(payload: dict[str, Any]) -> dict[str, Any]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = time.time()
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def target_info(target: str) -> dict[str, Any]:
    return KEYBOARD_TARGETS.get(target, {"label": target.replace("_", " ").title(), "secret": True, "placeholder": "text"})


def open_keyboard(target: str, initial: str = "") -> PopupKeyboardState:
    info = target_info(target)
    return PopupKeyboardState(target=target, title=str(info.get("label", target)), secret=bool(info.get("secret", True)), placeholder=str(info.get("placeholder", "")), text=initial)


def _merge_json(path: Path, updates: dict[str, Any], *, chmod_private: bool = False) -> dict[str, Any]:
    current: dict[str, Any] = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                current = loaded
        except Exception:
            current = {}
    current.update(updates)
    current["updated_at"] = time.time()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2, sort_keys=True), encoding="utf-8")
    if chmod_private:
        try:
            path.chmod(0o600)
        except Exception:
            pass
    return current


def _save_wigle(target: str, value: str) -> dict[str, Any]:
    from .menu_prompt_state import WIGLE_CREDENTIAL_PATH

    key = "api_name" if target == "wigle_api_name" else "api_token"
    _merge_json(WIGLE_CREDENTIAL_PATH, {key: value}, chmod_private=True)
    return {"status": "KEYBOARD_VALUE_SAVED", "target": target, "path": str(WIGLE_CREDENTIAL_PATH), "saved_key": key, "secret": target.endswith("token"), "value_length": len(value)}


def _save_location_password(target: str, value: str) -> dict[str, Any]:
    from .location_password_gate import create_password, ensure_unlocked

    if target == "location_password":
        result = create_password(value)
        return {"status": "KEYBOARD_VALUE_SAVED", "target": target, "result": result, "secret": True}
    ok = ensure_unlocked(password=value, prompt=False)
    return {"status": "LOCATION_GATE_UNLOCKED" if ok else "LOCATION_GATE_UNLOCK_FAILED", "target": target, "secret": True}


def _save_meshtastic(target: str, value: str) -> dict[str, Any]:
    from .meshtastic_app import load_send_prompt_state, save_send_prompt_state

    state = load_send_prompt_state()
    if target == "meshtastic_send_message":
        state["message"] = value
        state["confirm_send"] = False
        saved_key = "message"
    else:
        state["dest"] = value
        saved_key = "dest"
    saved = save_send_prompt_state(state)
    return {"status": "KEYBOARD_VALUE_SAVED", "target": target, "saved_key": saved_key, **saved}


def _save_bluez_lab_target(value: str) -> dict[str, Any]:
    from .bluez_lab_scope import set_target

    result = set_target(value)
    return {"target": "bluez_lab_target", **result}


def save_keyboard_value(target: str, value: str) -> dict[str, Any]:
    if target in {"wigle_api_name", "wigle_api_token"}:
        payload = _save_wigle(target, value)
    elif target in {"location_password", "location_unlock_password"}:
        payload = _save_location_password(target, value)
    elif target in {"meshtastic_send_message", "meshtastic_send_dest"}:
        payload = _save_meshtastic(target, value)
    elif target == "bluez_lab_target":
        payload = _save_bluez_lab_target(value)
    else:
        payload = {"status": "KEYBOARD_UNKNOWN_TARGET", "target": target, "value_length": len(value)}
    return _write_status(payload)


def keyboard_manifest() -> dict[str, Any]:
    return _write_status({
        "status": "POPUP_KEYBOARD_READY",
        "targets": {key: {k: v for k, v in value.items() if k != "secret"} | {"secret": bool(value.get("secret"))} for key, value in KEYBOARD_TARGETS.items()},
        "controls": {
            "buttons": {"up_down_left_right": "move key highlight", "select": "press highlighted key", "back": "cancel or leave keyboard", "main_menu": "cancel and return"},
            "touch": {"tap_key": "highlight key", "long_press": "press key"},
            "voice_to_text": ["keyboard text <words>", "dictate <words>", "voice text <words>"],
        },
        "special_keys": SPECIAL_KEYS,
        "status_path": str(STATUS_PATH),
    })
