from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Dict, Optional

from .killerkoala_voice_control import parse_voice_command
from .killerkoala_web_research import looks_like_general_question
from .menu_voice_launcher import parse_menu_voice_launch

_FAST_STATUS_FORMS = {
    "killerkoala status",
    "hey killerkoala status",
}
_CONVERSATIONAL_TRIGGERS = (
    "banter",
    "chat",
    "talk",
    "say something",
    "be cheeky",
    "surprise me",
    "what do you reckon",
    "give me some attitude",
    "hello",
    "hi",
    "thanks",
    "thank you",
    "how are you",
)
_SUPPORTED_RECOGNIZERS = {
    "jsgf_commands",
    "general_lm",
    "whisper",
    "online",
}


def _normalize_phrase(phrase: str) -> str:
    text = " ".join(str(phrase or "").lower().split())
    text = text.replace("killer koala", "killerkoala")
    return text.strip(" ,.!?;:")


def _working_phrase(phrase: str) -> str:
    normalized = _normalize_phrase(phrase)
    if normalized.startswith("hey killerkoala"):
        return normalized[len("hey killerkoala") :].strip()
    if normalized.startswith("killerkoala"):
        return normalized[len("killerkoala") :].strip()
    return normalized


def should_fast_clarify_misheard_phrase(phrase: str, recognizer_search: str) -> bool:
    recognizer = str(recognizer_search or "").strip()
    if recognizer not in _SUPPORTED_RECOGNIZERS:
        return False

    normalized = _normalize_phrase(phrase)
    if normalized in _FAST_STATUS_FORMS:
        return False

    parsed = parse_voice_command(normalized, require_wake_word=True)
    if parsed.module_key is not None or parsed.menu_action is not None:
        return False

    menu_match = parse_menu_voice_launch(normalized, require_wake_word=True)
    if menu_match is not None:
        return False

    working = _working_phrase(normalized)
    if not working:
        return True
    if looks_like_general_question(working):
        return False
    if any(token in working for token in _CONVERSATIONAL_TRIGGERS):
        return False
    return True


def wake_is_independently_confirmed(event: Any) -> bool:
    payload = getattr(event, "payload", {})
    if isinstance(payload, dict) and bool(payload.get("wake_already_confirmed")):
        return True
    source = str(getattr(event, "source", "") or "").strip().lower()
    return source == "esp32_s3_es7210_confirmed_wake_followup"


def _route_live_voice_submenu(self: Any, event: Any) -> Optional[Dict[str, Any]]:
    """Open voice-requested submenus on the live Pi menu and DualEye immediately."""

    match = parse_menu_voice_launch(
        _normalize_phrase(event.phrase),
        require_wake_word=True,
    )
    if match is None or not match.is_submenu:
        return None

    try:
        from .hdmi_display_state import submit_menu_command
        from .menu_display_sync import _esp32_menu_payload, build_menu_sync_payload
        from scripts.run_menu_screen import make_menu, open_submenu

        menu = make_menu()
        if match.submenu == "main":
            menu_event = menu.reopen_menu("main_menu")
            live_command = "main_menu"
        else:
            if not open_submenu(menu, match.command):
                raise RuntimeError(f"submenu target not available: {match.command}")
            menu.display_mode = "menu"
            menu.face_state = "menu"
            menu.face_message = f"{menu.menu_title} open"
            menu.last_input_at = __import__("time").time()
            menu_event = menu._event("submenu_voice_open", match.command)
            live_command = match.command

        full_payload = build_menu_sync_payload(menu, menu_event)
        compact_payload = _esp32_menu_payload(full_payload)
        compact_payload["source"] = "killerkoala-voice-live-menu"
        compact_payload["voice_request"] = True

        self._write_json(compact_payload)
        queue_record = submit_menu_command(live_command, source="killerkoala_voice")

        message = f"Opening {match.label}, mate."
        result_data: Dict[str, Any] = {
            "status": "success",
            "module_key": "menu_voice_live_navigation",
            "module_title": "Live Menu Voice Navigation",
            "phrase": event.phrase,
            "command_id": match.command,
            "menu_label": match.label,
            "submenu": match.submenu,
            "companion_line": message,
            "live_menu_command": live_command,
            "live_menu_queued": True,
            "queue_record": queue_record,
            "llm_used": False,
            "web_searched": False,
        }
        self._write_json(
            {
                "type": "pi_execution_result",
                "request_id": event.request_id,
                "status": "success",
                "message": message,
                "action": match.label,
                "voice_request": True,
                "command_id": match.command,
                "result": result_data,
            }
        )
        self._play_response(message, "pi-menu-navigation")
        return {"event": asdict(event), "result": result_data}
    except Exception as exc:
        result_data = {
            "status": "error",
            "module_key": "menu_voice_live_navigation",
            "module_title": "Live Menu Voice Navigation",
            "phrase": event.phrase,
            "companion_line": "",
            "error": str(exc),
            "llm_used": False,
            "web_searched": False,
        }
        self._write_json(
            {
                "type": "voice_rejected",
                "request_id": event.request_id,
                "reason": "live_menu_navigation_failed",
                "result": result_data,
            }
        )
        return {"event": asdict(event), "result": result_data}


def install_esp32_misheard_voice_fastpath(bridge_class: type) -> Callable[..., Dict[str, Any]]:
    """Install live menu navigation and deterministic unresolved-STT handling."""

    original = bridge_class._route_phrase
    if getattr(original, "_koalabyte_misheard_fastpath", False):
        return original

    def _route_phrase(self, event):
        live_menu = _route_live_voice_submenu(self, event)
        if live_menu is not None:
            return live_menu

        if should_fast_clarify_misheard_phrase(
            event.phrase,
            str(getattr(self, "_last_stt_search", "")),
        ):
            if not wake_is_independently_confirmed(event):
                result_data = {
                    "status": "ignored",
                    "module_key": "killerkoala_false_wake_guard",
                    "module_title": "KillerKoala False Wake Guard",
                    "phrase": event.phrase,
                    "companion_line": "",
                    "source": "local_unconfirmed_stt_guard",
                    "llm_used": False,
                    "web_searched": False,
                    "wake_confirmed": False,
                }
                self._write_json(
                    {
                        "type": "voice_rejected",
                        "request_id": event.request_id,
                        "reason": "unconfirmed_stt_miss",
                        "resume_menu": bool(
                            getattr(event, "payload", {}).get("menu_was_visible", False)
                            if isinstance(getattr(event, "payload", {}), dict)
                            else False
                        ),
                        "result": result_data,
                    }
                )
                return {"event": asdict(event), "result": result_data}

            message = "Didn't catch that command, mate. Try that again."
            result_data = {
                "status": "clarify",
                "module_key": "killerkoala_clarification",
                "module_title": "KillerKoala Clarification",
                "phrase": event.phrase,
                "companion_line": message,
                "source": "local_misheard_fastpath",
                "llm_used": False,
                "web_searched": False,
                "wake_confirmed": True,
            }
            self._write_json(
                {
                    "type": "pi_execution_result",
                    "request_id": event.request_id,
                    "status": "clarify",
                    "message": message,
                    "action": "KillerKoala clarification",
                    "voice_request": True,
                    "result": result_data,
                }
            )
            self._fanout_face("curious", message, 2800)
            self._play_response(message, "pi-clarification")
            return {"event": asdict(event), "result": result_data}
        return original(self, event)

    _route_phrase._koalabyte_misheard_fastpath = True  # type: ignore[attr-defined]
    bridge_class._route_phrase = _route_phrase
    return _route_phrase


__all__ = [
    "install_esp32_misheard_voice_fastpath",
    "should_fast_clarify_misheard_phrase",
    "wake_is_independently_confirmed",
]
