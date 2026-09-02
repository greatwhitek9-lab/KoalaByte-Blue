from __future__ import annotations

from typing import Any, Optional

from .killerkoala_voice_control import (
    BASE_MODULE_TO_MENU_COMMAND,
    VOICE_MODULES,
    parse_voice_command,
)
from .killerkoala_voice_router import canonicalize_killerkoala_wake
from .killerkoala_expression import expression_for_face_state


TRUSTED_PI_MENU_SOURCE = "koalabyte-blue-pi"


def voice_menu_preview(self: Any, phrase: str) -> Optional[dict[str, Any]]:
    """Show a menu-style preview for routed voice commands without hiding it.

    The whole-system face lifecycle introduced an immediate action-face fanout
    after menu_sync, which replaced the menu before it was visibly useful. A
    highlight event keeps the existing ESP32 menu renderer active while the Pi
    executes the command; the normal execution result then transitions to the
    success/error/speaking face lifecycle.

    Production JSGF transcripts use the spoken form ``killer koala`` while the
    historical voice parser uses ``killerkoala``. Normalize that boundary here
    exactly as the routing layer does so display preview and execution agree.

    The generated ESP32 wake-session wrapper only treats menu traffic from
    ``koalabyte-blue-pi`` as trusted Pi activity. Use that canonical source so a
    routed voice command can expose the menu even when the local wake session is
    otherwise sleeping.
    """

    canonical_phrase = canonicalize_killerkoala_wake(phrase)
    parsed = parse_voice_command(canonical_phrase, require_wake_word=True)

    if parsed.menu_action is not None:
        command = parsed.menu_action.command
        label = parsed.menu_action.label
        group = parsed.menu_action.group
    elif parsed.module_key in BASE_MODULE_TO_MENU_COMMAND:
        command, label, group = BASE_MODULE_TO_MENU_COMMAND[parsed.module_key]
    elif parsed.module_key == "killerkoala_help":
        command = "killerkoala_help"
        label = VOICE_MODULES["killerkoala_help"].title
        group = "System / Companion"
    else:
        # Open-ended questions keep the expressive thinking-eye lifecycle.
        return None

    payload: dict[str, Any] = {
        "type": "menu_sync",
        "menu_name": "voice",
        "menu_title": "VOICE COMMAND",
        "event_type": "highlight",
        "selected_position": 1,
        "total_items": 1,
        "selected_label": label,
        "selected_command": command,
        "selected_group": group,
        "selected_enabled": True,
        "visible_rows": 1,
        "visible_items": [
            {
                "position": 1,
                "label": label,
                "selected": True,
                "enabled": True,
            }
        ],
        "source": TRUSTED_PI_MENU_SOURCE,
        "voice_request": True,
        "execution_owner": "raspberry-pi",
        "display_intent": "voice_menu_preview",
    }
    expression = expression_for_face_state(
        "action",
        label,
        context={"input_source": "voice", "command": command, "menu": "voice"},
    )
    payload.update(expression.to_payload())
    payload["mood"] = expression.tone
    payload["brightness"] = expression.intensity
    payload["face_state"] = "action"
    payload["expression_source"] = "pi_voice_menu_state"
    payload["input_source"] = "voice"
    self._write_json(payload)
    return payload


def install_voice_menu_display_restore(bridge_cls: type) -> type:
    """Install the restored menu-visible voice preview on the production bridge."""

    bridge_cls._menu_preview = voice_menu_preview
    return bridge_cls


__all__ = [
    "TRUSTED_PI_MENU_SOURCE",
    "install_voice_menu_display_restore",
    "voice_menu_preview",
]
