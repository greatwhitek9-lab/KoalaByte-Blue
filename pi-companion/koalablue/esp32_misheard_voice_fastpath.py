from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Dict

from .killerkoala_voice_control import parse_voice_command
from .killerkoala_web_research import looks_like_general_question

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
    """Identify unresolved physical STT before the legacy AI fallback.

    Any supported physical recognizer may mishear a command. If the normalized
    wake phrase maps to a real module/menu action, a general question, or an
    explicit conversational request, normal routing continues. Everything else
    is treated as an unresolved recognition event. Whether that event should be
    spoken or silently ignored depends on independent wake confirmation.
    """

    recognizer = str(recognizer_search or "").strip()
    if recognizer not in _SUPPORTED_RECOGNIZERS:
        return False

    normalized = _normalize_phrase(phrase)
    if normalized in _FAST_STATUS_FORMS:
        return False

    parsed = parse_voice_command(normalized, require_wake_word=True)
    if parsed.module_key is not None or parsed.menu_action is not None:
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


def install_esp32_misheard_voice_fastpath(bridge_class: type) -> Callable[..., Dict[str, Any]]:
    """Install deterministic unresolved-STT handling ahead of AI fallback."""

    original = bridge_class._route_phrase
    if getattr(original, "_koalabyte_misheard_fastpath", False):
        return original

    def _route_phrase(self, event):
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
