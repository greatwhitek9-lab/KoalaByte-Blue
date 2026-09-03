from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Mapping, Optional


DEFAULT_STATE_PATH = Path(
    os.getenv(
        "KOALABYTE_PERSISTENT_ACTION_STATE",
        "logs/runtime/persistent_actions.json",
    )
)

_START_TOKENS = {"start", "on", "enable", "enabled", "arm", "activate"}
_STOP_TOKENS = {"stop", "off", "disable", "disabled", "disarm", "deactivate"}
_RESTART_TOKENS = {"restart"}
_NON_PERSISTENT_SYSTEM_COMMANDS = {
    "power_on_off",
    "power_toggle",
    "shutdown_confirm",
    "reset",
    "reset_confirm",
    "reset_reboot",
    "reboot",
    "hdmi_toggle",
}
_FAILURE_TOKENS = ("ERROR", "FAILED", "FAILURE", "BLOCKED", "SKIPPED", "DENIED")


def _normalise(value: str) -> str:
    text = str(value or "").strip().lower()
    for token in ("_", "-", ":", "/"):
        text = text.replace(token, " ")
    return " ".join(text.split())


def _command_tokens(command: str) -> list[str]:
    return _normalise(command).split()


def lifecycle_intent(command: str, label: str = "") -> Optional[str]:
    """Return start/stop/restart for explicit persistent lifecycle commands.

    Only explicit lifecycle words are considered. Generic verbs such as ``run``
    and ``scan`` remain one-shot so diagnostics and bounded surveys do not become
    accidental forever-jobs.
    """

    raw = str(command or "").strip().lower()
    if not raw or raw in _NON_PERSISTENT_SYSTEM_COMMANDS:
        return None

    tokens = _command_tokens(command)
    if not tokens:
        tokens = _command_tokens(label)
    if not tokens:
        return None

    if any(token in _RESTART_TOKENS for token in tokens):
        return "restart"
    if tokens[-1] in _STOP_TOKENS:
        return "stop"
    if tokens[-1] in _START_TOKENS:
        return "start"

    # Human-facing menu labels sometimes carry the lifecycle word while the
    # command id uses a compact legacy form. Respect the final label token too.
    label_tokens = _command_tokens(label)
    if label_tokens:
        if any(token in _RESTART_TOKENS for token in label_tokens):
            return "restart"
        if label_tokens[-1] in _STOP_TOKENS:
            return "stop"
        if label_tokens[-1] in _START_TOKENS:
            return "start"
    return None


def action_key(command: str, label: str = "") -> str:
    """Return the stable lifecycle key shared by matching start/stop commands."""

    tokens = _command_tokens(command)
    lifecycle_words = _START_TOKENS | _STOP_TOKENS | _RESTART_TOKENS
    trimmed = [token for token in tokens if token not in lifecycle_words]
    if not trimmed:
        trimmed = [
            token
            for token in _command_tokens(label)
            if token not in lifecycle_words
        ]
    return "_".join(trimmed)[:120] or "action"


def _safe_read(path: Path = DEFAULT_STATE_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload.setdefault("actions", {})
            return payload
    except Exception:
        pass
    return {"version": 1, "actions": {}, "updated_at": 0.0}


def _write(payload: Mapping[str, Any], path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temp.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temp, path)


def result_succeeded(result: Any) -> bool:
    if not isinstance(result, Mapping):
        return True
    if result.get("error"):
        return False
    status = str(result.get("status") or "SUCCESS").upper()
    return not any(token in status for token in _FAILURE_TOKENS)


def apply_lifecycle_transition(
    command: str,
    label: str = "",
    result: Any = None,
    *,
    source: str = "menu",
    path: Path = DEFAULT_STATE_PATH,
) -> Optional[dict[str, Any]]:
    """Persist one explicit START/STOP/RESTART transition.

    START/ON/ENABLE/ARM/ACTIVATE remains active until the matching
    STOP/OFF/DISABLE/DISARM/DEACTIVATE transition succeeds. RESTART records a new
    start time and remains active. Failed transitions do not mutate the previous
    active state.
    """

    intent = lifecycle_intent(command, label)
    if intent is None:
        return None

    key = action_key(command, label)
    state = _safe_read(path)
    actions = state.setdefault("actions", {})
    previous = actions.get(key, {}) if isinstance(actions, dict) else {}
    now = time.time()
    success = result_succeeded(result)

    record: dict[str, Any] = {
        "key": key,
        "label": " ".join(str(label or command).split())[:120],
        "last_command": str(command or "")[:160],
        "last_intent": intent,
        "source": " ".join(str(source or "menu").split())[:80],
        "transition_succeeded": success,
        "updated_at": now,
    }

    if not success:
        record["active"] = bool(previous.get("active", False))
        if previous.get("started_at") is not None:
            record["started_at"] = previous.get("started_at")
        if previous.get("stopped_at") is not None:
            record["stopped_at"] = previous.get("stopped_at")
    elif intent in {"start", "restart"}:
        record["active"] = True
        record["started_at"] = now
        record["stopped_at"] = None
        if intent == "restart":
            record["restarted_at"] = now
    else:
        record["active"] = False
        record["started_at"] = previous.get("started_at")
        record["stopped_at"] = now

    actions[key] = record
    state["version"] = 1
    state["updated_at"] = now
    _write(state, path)
    return dict(record)


def active_actions(path: Path = DEFAULT_STATE_PATH) -> dict[str, dict[str, Any]]:
    state = _safe_read(path)
    actions = state.get("actions", {})
    if not isinstance(actions, dict):
        return {}
    return {
        str(key): dict(value)
        for key, value in actions.items()
        if isinstance(value, Mapping) and bool(value.get("active", False))
    }


def is_action_active(command: str, label: str = "", path: Path = DEFAULT_STATE_PATH) -> bool:
    key = action_key(command, label)
    return key in active_actions(path)


__all__ = [
    "DEFAULT_STATE_PATH",
    "action_key",
    "active_actions",
    "apply_lifecycle_transition",
    "is_action_active",
    "lifecycle_intent",
    "result_succeeded",
]
