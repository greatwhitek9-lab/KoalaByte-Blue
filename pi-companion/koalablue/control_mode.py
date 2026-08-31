from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

DEFAULT_CONTROL_MODE_PATH = Path("logs/control/control_mode.json")
VALID_CONTROL_MODES = {"auto", "full_controls", "touch_speech_only"}
TOUCH_SPEECH_ONLY = "touch_speech_only"
FULL_CONTROLS = "full_controls"
AUTO = "auto"


def control_mode_path() -> Path:
    raw = os.getenv("KOALABYTE_CONTROL_MODE_PATH", "").strip()
    return Path(raw) if raw else DEFAULT_CONTROL_MODE_PATH


def _normalize_mode(mode: str) -> str:
    value = str(mode or AUTO).strip().lower().replace("-", "_")
    aliases = {
        "touch": TOUCH_SPEECH_ONLY,
        "speech": TOUCH_SPEECH_ONLY,
        "touch_speech": TOUCH_SPEECH_ONLY,
        "touch_and_speech": TOUCH_SPEECH_ONLY,
        "buttons": FULL_CONTROLS,
        "gpio": FULL_CONTROLS,
        "normal": FULL_CONTROLS,
    }
    value = aliases.get(value, value)
    if value not in VALID_CONTROL_MODES:
        raise ValueError(f"unsupported KoalaByte control mode: {mode}")
    return value


def write_control_mode(
    mode: str,
    *,
    reason: str = "",
    source: str = "runtime",
    buttons_available: bool | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = _normalize_mode(mode)
    path = control_mode_path()
    payload: dict[str, Any] = {
        "status": "KOALABYTE_CONTROL_MODE_READY",
        "mode": normalized,
        "gpio_buttons_enabled": normalized != TOUCH_SPEECH_ONLY,
        "touch_enabled": True,
        "speech_enabled": True,
        "keyboard_enabled": True,
        "fallback_active": normalized == TOUCH_SPEECH_ONLY,
        "reason": str(reason or ""),
        "source": str(source or "runtime"),
        "updated_at": time.time(),
    }
    if buttons_available is not None:
        payload["buttons_available"] = bool(buttons_available)
    if extra:
        payload.update(extra)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def load_control_mode() -> dict[str, Any]:
    path = control_mode_path()
    if not path.exists():
        return {
            "status": "KOALABYTE_CONTROL_MODE_DEFAULT",
            "mode": AUTO,
            "gpio_buttons_enabled": True,
            "touch_enabled": True,
            "speech_enabled": True,
            "keyboard_enabled": True,
            "fallback_active": False,
            "reason": "No persisted control-mode artifact; automatic GPIO detection is allowed.",
            "source": "default",
            "path": str(path),
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "status": "KOALABYTE_CONTROL_MODE_INVALID",
            "mode": AUTO,
            "gpio_buttons_enabled": True,
            "touch_enabled": True,
            "speech_enabled": True,
            "keyboard_enabled": True,
            "fallback_active": False,
            "reason": f"Could not read control-mode artifact: {exc}",
            "source": "default_after_error",
            "path": str(path),
        }
    mode = _normalize_mode(str(payload.get("mode", AUTO)))
    payload["mode"] = mode
    payload["gpio_buttons_enabled"] = mode != TOUCH_SPEECH_ONLY
    payload["touch_enabled"] = True
    payload["speech_enabled"] = True
    payload["keyboard_enabled"] = True
    payload["fallback_active"] = mode == TOUCH_SPEECH_ONLY
    payload["path"] = str(path)
    return payload


def _automatic_gpio_fallback(payload: dict[str, Any]) -> bool:
    """Return True only for a fallback produced by failed GPIO auto-detection."""
    return (
        _normalize_mode(str(payload.get("mode", AUTO))) == TOUCH_SPEECH_ONLY
        and str(payload.get("source", "")) == "gpio_button_manager"
        and payload.get("buttons_available") is False
    )


def effective_control_mode() -> str:
    override = os.getenv("KOALABYTE_CONTROL_MODE", "").strip()
    if override:
        return _normalize_mode(override)

    payload = load_control_mode()
    # A gpio_button_manager fallback is diagnostic state, not a permanent user
    # preference. Retry GPIO initialization on the next service start so a
    # transient boot/resource failure cannot disable K1-K8 forever. Explicit
    # touch_speech_only choices from users/installers remain persistent.
    if _automatic_gpio_fallback(payload):
        return AUTO
    return _normalize_mode(str(payload.get("mode", AUTO)))


def gpio_buttons_enabled() -> bool:
    return effective_control_mode() != TOUCH_SPEECH_ONLY
