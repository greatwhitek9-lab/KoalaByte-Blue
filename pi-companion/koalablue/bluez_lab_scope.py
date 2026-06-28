from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

SCOPE_PATH = Path("logs/security/bluez_lab_scope.json")
TARGET_ENV = "KOALABYTE_BLUEZ_LAB_TARGET"
ALT_TARGET_ENV = "KOALABYTE_BLUEZ_TARGET"
OWNED_ENV = "KOALABYTE_BLUEZ_OWNED_DEVICE"
_TARGET_RE = re.compile(r"^[0-9A-F]{2}(:[0-9A-F]{2}){5}$")


def _normalise_target(value: str) -> str:
    cleaned = value.strip().upper().replace("-", ":")
    if re.fullmatch(r"[0-9A-F]{12}", cleaned):
        cleaned = ":".join(cleaned[i : i + 2] for i in range(0, 12, 2))
    return cleaned


def _redact_target(target: str) -> str:
    target = target.strip().upper()
    parts = target.split(":")
    if len(parts) == 6:
        return ":".join([parts[0], parts[1], "**", "**", parts[4], parts[5]])
    return "<target-set>" if target else ""


def _load() -> dict[str, Any]:
    if not SCOPE_PATH.exists():
        return {"target": "", "owned_device": False}
    try:
        loaded = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            return {"target": str(loaded.get("target", "")), "owned_device": bool(loaded.get("owned_device", False))}
    except Exception:
        pass
    return {"target": "", "owned_device": False}


def _save(state: dict[str, Any]) -> dict[str, Any]:
    clean = {"target": str(state.get("target", "")), "owned_device": bool(state.get("owned_device", False)), "updated_at": time.time(), "scope": "local menu-managed owned-device BlueZ lab scope"}
    SCOPE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCOPE_PATH.write_text(json.dumps(clean, indent=2, sort_keys=True), encoding="utf-8")
    try:
        SCOPE_PATH.chmod(0o600)
    except Exception:
        pass
    return clean


def scope_status() -> dict[str, Any]:
    state = _load()
    return {
        "status": "BLUEZ_LAB_SCOPE_READY" if state.get("target") and state.get("owned_device") else "BLUEZ_LAB_SCOPE_INCOMPLETE",
        "path": str(SCOPE_PATH),
        "target_configured": bool(state.get("target")),
        "target_redacted": _redact_target(str(state.get("target", ""))),
        "owned_device": bool(state.get("owned_device", False)),
        "target_env": TARGET_ENV,
        "owned_env": OWNED_ENV,
        "note": "Use only for owned devices or explicit authorized test scope.",
    }


def set_target(value: str) -> dict[str, Any]:
    target = _normalise_target(value)
    if target and not _TARGET_RE.fullmatch(target):
        return {"status": "BLUEZ_LAB_TARGET_REJECTED", "reason": "target must be a 12-hex Bluetooth address", "value_length": len(value)}
    state = _load()
    state["target"] = target
    saved = _save(state)
    return {"status": "BLUEZ_LAB_TARGET_SAVED", "path": str(SCOPE_PATH), "target_configured": bool(target), "target_redacted": _redact_target(target), "owned_device": bool(saved.get("owned_device", False))}


def set_owned(enabled: bool) -> dict[str, Any]:
    state = _load()
    state["owned_device"] = bool(enabled)
    saved = _save(state)
    return {"status": "BLUEZ_LAB_OWNED_SCOPE_SET", "enabled": bool(enabled), "path": str(SCOPE_PATH), "target_configured": bool(saved.get("target")), "target_redacted": _redact_target(str(saved.get("target", "")))}


def clear_scope() -> dict[str, Any]:
    saved = _save({"target": "", "owned_device": False})
    os.environ.pop(TARGET_ENV, None)
    os.environ.pop(ALT_TARGET_ENV, None)
    os.environ.pop(OWNED_ENV, None)
    return {"status": "BLUEZ_LAB_SCOPE_CLEARED", "path": str(SCOPE_PATH), "target_configured": bool(saved.get("target")), "owned_device": bool(saved.get("owned_device", False))}


def apply_env() -> dict[str, Any]:
    state = _load()
    target = str(state.get("target", "")).strip()
    owned = bool(state.get("owned_device", False))
    if target:
        os.environ[TARGET_ENV] = target
        os.environ[ALT_TARGET_ENV] = target
    else:
        os.environ.pop(TARGET_ENV, None)
        os.environ.pop(ALT_TARGET_ENV, None)
    if owned:
        os.environ[OWNED_ENV] = "1"
    else:
        os.environ.pop(OWNED_ENV, None)
    return {"target_configured": bool(target), "target_redacted": _redact_target(target), "owned_device": owned, "path": str(SCOPE_PATH)}
