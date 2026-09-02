from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class KillerKoalaExpression:
    tone: str
    subject: str
    intensity: int
    eye_look: str
    eye_animation: str
    left_eye: str
    right_eye: str
    mouth_expression: str
    speech_motion: str

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


_POSITIVE = (
    "happy", "great", "excellent", "perfect", "success", "complete", "done",
    "bonza", "beaut", "sweet", "good news", "working", "ready", "clean run",
    "content", "eating", "feeding",
)
_ANGRY = (
    "angry", "furious", "hostile", "rage", "snarl", "mad", "bloody",
    "unacceptable", "attack", "threat", "reckless", "cranky",
)
_ERROR = (
    "error", "failed", "failure", "fault", "crash", "broken", "blocked",
    "denied", "exception", "offline", "unavailable", "cannot", "can't",
    "alarmed", "alarm",
)
_CONCERNED = (
    "warning", "careful", "risk", "concern", "unsafe", "uncertain", "unknown",
    "check", "verify", "attention", "caution", "problem", "issue",
)
_CURIOUS = (
    "why", "how", "what", "which", "who", "when", "where", "question",
    "wonder", "curious", "explain", "research", "look up",
)
_EXCITED = (
    "excited", "brilliant", "legend", "crikey", "rip in", "let's go", "lets go",
    "outstanding", "new discovery",
)
_SAD = (
    "sad", "sorry", "unfortunate", "disappointed", "lost", "missed", "down",
)
_MISCHIEF = (
    "cheeky", "mischief", "funny", "joke", "boomerang", "sneaky", "grin",
)

_STATE_TONES = {
    "idle": "neutral",
    "hidden": "neutral",
    "wake": "excited",
    "listening": "curious",
    "thinking": "curious",
    "menu": "curious",
    "menu_open": "curious",
    "navigation": "curious",
    "keyboard": "focused",
    "action": "focused",
    "action_running": "focused",
    "loading": "focused",
    "speaking": "neutral",
    "success": "happy",
    "action_complete": "happy",
    "koalagotchi_mode": "mischievous",
    "disappointed": "disappointed",
    "angry": "angry",
    "error": "error",
    "alarmed": "error",
    "fault": "error",
    "exception": "error",
}

_SUBJECTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("bluetooth", ("bluetooth", "ble", "bluez", "gatt", "beacon")),
    ("wifi", ("wi-fi", "wifi", "wireless", "ssid", "access point")),
    ("web", ("web", "internet", "online", "source", "search", "news")),
    ("hardware", ("gpio", "button", "pin", "firmware", "flash", "board", "esp32", "heltec", "raspberry pi")),
    ("location", ("gps", "gnss", "location", "latitude", "longitude", "map")),
    ("security", ("security", "risk", "threat", "defensive", "authorized", "scope")),
    ("system", ("service", "process", "memory", "cpu", "temperature", "status", "log")),
)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _subject(text: str) -> str:
    for name, terms in _SUBJECTS:
        if _contains_any(text, terms):
            return name
    return "conversation"


def classify_response_expression(
    text: str,
    *,
    status: str = "",
    event: str = "",
    context: Mapping[str, Any] | None = None,
    preferred_tone: str = "",
) -> KillerKoalaExpression:
    combined = " ".join(
        (
            str(text or ""),
            str(status or ""),
            str(event or ""),
            # Context keys such as ``source`` are metadata, not dialogue. Only
            # values participate in subject classification so a transport field
            # cannot accidentally color every expression as a web/search mood.
            " ".join(str(value) for value in (context or {}).values()),
        )
    ).lower()
    subject = _subject(combined)

    forced = str(preferred_tone or "").strip().lower()
    if forced in {
        "angry", "error", "concerned", "disappointed", "excited", "happy",
        "mischievous", "curious", "focused", "neutral",
    }:
        tone = forced
    elif _contains_any(combined, _ANGRY):
        tone = "angry"
    elif _contains_any(combined, _ERROR):
        tone = "error"
    elif _contains_any(combined, _CONCERNED):
        tone = "concerned"
    elif _contains_any(combined, _SAD):
        tone = "disappointed"
    elif _contains_any(combined, _EXCITED):
        tone = "excited"
    elif _contains_any(combined, _POSITIVE):
        tone = "happy"
    elif _contains_any(combined, _MISCHIEF):
        tone = "mischievous"
    elif _contains_any(combined, _CURIOUS):
        tone = "curious"
    elif subject in {"hardware", "system", "security", "bluetooth", "wifi"}:
        tone = "focused"
    else:
        tone = "neutral"

    palette = {
        "angry": (95, "angry", "glitch", "#A54BFF", "#32FF71", "snarl", "hard_emphasis"),
        "error": (100, "angry", "glitch", "#A54BFF", "#32FF71", "snarl", "alarm_emphasis"),
        "concerned": (72, "slit", "pulse", "#FFB000", "#A54BFF", "sideways_grin", "measured_emphasis"),
        "disappointed": (55, "sleepy", "blink", "#5D7CFF", "#A54BFF", "sideways_grin", "slow_measured"),
        "excited": (92, "star", "pulse", "#32FF71", "#FFD84A", "smile", "fast_bright"),
        "happy": (82, "heart", "pulse", "#32FF71", "#A54BFF", "smile", "bright"),
        "mischievous": (76, "slit", "glitch", "#A54BFF", "#32FF71", "sideways_grin", "cheeky"),
        "curious": (68, "round", "scan", "#4DD9FF", "#A54BFF", "smile", "questioning"),
        "focused": (74, "cyber", "scan", "#4DD9FF", "#32FF71", "bite", "precise"),
        "neutral": (60, "cyber", "blink", "#A54BFF", "#32FF71", "smile", "natural"),
    }
    intensity, look, animation, left, right, mouth, motion = palette[tone]

    # Error/angry purple-green is a system-wide alarm contract. Subject palettes
    # may color normal conversation but must never obscure that warning state.
    if tone not in {"angry", "error"}:
        if subject == "bluetooth":
            right = "#32FF71"
        elif subject == "wifi":
            left = "#4DD9FF"
        elif subject == "web":
            left, right = "#4DD9FF", "#FFD84A"
        elif subject == "security":
            left, right = "#FFB000", "#32FF71"
        elif subject == "location":
            left, right = "#32FF71", "#4DD9FF"

    return KillerKoalaExpression(
        tone=tone,
        subject=subject,
        intensity=intensity,
        eye_look=look,
        eye_animation=animation,
        left_eye=left,
        right_eye=right,
        mouth_expression=mouth,
        speech_motion=motion,
    )


def expression_for_face_state(
    state: str,
    message: str = "",
    *,
    context: Mapping[str, Any] | None = None,
) -> KillerKoalaExpression:
    """Return the Pi-authoritative expression for a visible face lifecycle state.

    Explicit lifecycle states win over incidental words in a status message. This
    keeps a successful recovery happy even when its message mentions the error it
    cleared, while speech can still derive a natural tone from the spoken text.
    """

    normalized = " ".join(str(state or "idle").lower().replace("-", "_").split())
    tone = _STATE_TONES.get(normalized, "")
    if normalized == "speaking":
        tone = ""
    return classify_response_expression(
        message or normalized,
        status=normalized,
        event=normalized,
        context=context,
        preferred_tone=tone,
    )


LOCAL_CATEGORY_EXPRESSIONS = {
    "wake": "excited",
    "status": "focused",
    "help": "curious",
    "acknowledgement": "happy",
    "banter": "mischievous",
    "success": "happy",
    "error": "error",
    "escalate": "curious",
}


def expression_for_local_category(category: str, message: str = "") -> KillerKoalaExpression:
    preferred = LOCAL_CATEGORY_EXPRESSIONS.get(str(category or "").strip().lower())
    if preferred:
        return classify_response_expression(
            f"{preferred} {message}", event=preferred, context={"local_category": category}
        )
    return classify_response_expression(message, event="local_response")
