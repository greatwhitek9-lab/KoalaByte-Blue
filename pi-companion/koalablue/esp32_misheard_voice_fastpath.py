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
    """Fail fast on unsupported JSGF output instead of invoking TinyLlama.

    A command-grammar transcript that includes the wake phrase but maps to no
    supported module/menu action is most likely a recognition miss. Exact short
    status, explicit questions and intentional conversation/banter are excluded
    so their normal fast-status or semantic-generation paths remain available.
    """

    if str(recognizer_search or "").strip() != "jsgf_commands":
        return False

    normalized = _normalize_phrase(phrase)
    if normalized in _FAST_STATUS_FORMS:
        return False

    parsed = parse_voice_command(phrase, require_wake_word=True)
    if parsed.module_key is not None or parsed.menu_action is not None:
        return False

    working = _working_phrase(phrase)
    if not working:
        return True
    if looks_like_general_question(working):
        return False
    if any(token in working for token in _CONVERSATIONAL_TRIGGERS):
        return False
    return True


def install_esp32_misheard_voice_fastpath(bridge_class: type) -> Callable[..., Dict[str, Any]]:
    """Install the production fast clarification path on the DualEye bridge."""

    original = bridge_class._route_phrase
    if getattr(original, "_koalabyte_misheard_fastpath", False):
        return original

    def _route_phrase(self, event):
        if should_fast_clarify_misheard_phrase(
            event.phrase,
            str(getattr(self, "_last_stt_search", "")),
        ):
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
]
