from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .killerkoala_voice_control import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_XP_PATH,
    execute_module,
    module_manifest,
    parse_voice_command,
)
from .menu_voice_launcher import build_menu_voice_manifest, route_menu_voice_launch


_SPACED_WAKE_RE = re.compile(r"\b(?:hey\s+)?killer\s+koala\b", re.IGNORECASE)
_FUSED_WAKE_RE = re.compile(r"\b(?:hey\s+)?killerkoala\b", re.IGNORECASE)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def canonicalize_killerkoala_wake(phrase: str) -> str:
    """Normalize spoken/fused wake forms to the parser's canonical token."""

    text = " ".join(str(phrase or "").split())
    text = _SPACED_WAKE_RE.sub(
        lambda match: "hey killerkoala"
        if match.group(0).lower().lstrip().startswith("hey")
        else "killerkoala",
        text,
    )
    text = _FUSED_WAKE_RE.sub(
        lambda match: "hey killerkoala"
        if match.group(0).lower().lstrip().startswith("hey")
        else "killerkoala",
        text,
    )
    return " ".join(text.split())


def speak(text: str) -> bool:
    """Optional host-side CLI speech preview.

    The deployed voice bridge uses dualeye_tts and the William Australian male
    backend. This pyttsx3 path is retained only for interactive CLI compatibility.
    """

    try:
        import pyttsx3  # type: ignore
    except Exception:
        return False
    try:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return True
    except Exception:
        return False


def listen_once(timeout: int = 5, phrase_time_limit: int = 8) -> str:
    """Capture one optional host microphone phrase for the CLI router."""

    try:
        import speech_recognition as sr  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "microphone mode requires SpeechRecognition and PyAudio installed on the Pi"
        ) from exc
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:  # type: ignore[attr-defined]
        recognizer.adjust_for_ambient_noise(source, duration=0.4)
        audio = recognizer.listen(
            source, timeout=timeout, phrase_time_limit=phrase_time_limit
        )
    return str(recognizer.recognize_google(audio))


def route_voice_phrase(
    phrase: str,
    *,
    require_wake_word: bool = True,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    xp_path: Path = DEFAULT_XP_PATH,
    force_flexible_banter: bool = False,
):
    """Route a KillerKoala phrase.

    Explicit menu/submenu launch syntax is checked first. Other recognized basic
    commands route through the core parser. Open-ended wake-word questions route
    to the local TinyLlama companion, with web evidence added when available.
    """

    canonical_phrase = canonicalize_killerkoala_wake(phrase)

    menu_result = route_menu_voice_launch(
        canonical_phrase,
        output_dir=output_dir / "menu_voice",
        xp_path=xp_path,
        require_wake_word=require_wake_word,
    )
    if menu_result is not None:
        return menu_result

    parsed = parse_voice_command(
        canonical_phrase,
        require_wake_word=require_wake_word,
    )
    return execute_module(
        parsed,
        output_dir=output_dir,
        xp_path=xp_path,
        force_flexible_banter=force_flexible_banter,
    )


def combined_manifest() -> dict[str, Any]:
    voice = module_manifest()
    voice["menu_voice_launch"] = build_menu_voice_manifest()
    voice["syntax"] = [
        "killerkoala run <menu item or command>",
        "killerkoala open <menu item or command>",
        "killerkoala voice commands",
        "killerkoala <general question>",
    ]
    return voice


def run_cli() -> int:
    parser = argparse.ArgumentParser(
        description="KillerKoala spoken-command, menu, and TinyLlama question router"
    )
    parser.add_argument(
        "--phrase",
        default=None,
        help="Typed phrase, e.g. 'killerkoala why is the sky blue'",
    )
    parser.add_argument(
        "--listen",
        action="store_true",
        help="Listen once using optional SpeechRecognition/PyAudio",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Continuously listen until interrupted",
    )
    parser.add_argument(
        "--no-wake-required",
        action="store_true",
        help="Testing mode: do not require the KillerKoala wake word",
    )
    parser.add_argument(
        "--flexible-banter",
        action="store_true",
        help="Request open-ended local TinyLlama output",
    )
    parser.add_argument(
        "--speak",
        action="store_true",
        help="Speak the response through optional CLI pyttsx3",
    )
    parser.add_argument(
        "--manifest",
        action="store_true",
        help="Write and print the supported voice/menu manifest",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--xp-path", default=str(DEFAULT_XP_PATH))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    xp_path = Path(args.xp_path)

    if args.manifest:
        out = output_dir / "killerkoala_voice_and_menu_manifest.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        manifest = combined_manifest()
        out.write_text(
            json.dumps(_jsonable(manifest), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(
            json.dumps(
                {"manifest_path": str(out), "syntax": manifest.get("syntax", [])},
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    def handle_phrase(phrase: str):
        result = route_voice_phrase(
            phrase,
            require_wake_word=not args.no_wake_required,
            output_dir=output_dir,
            xp_path=xp_path,
            force_flexible_banter=args.flexible_banter,
        )
        print(json.dumps(_jsonable(result), indent=2, sort_keys=True))
        if args.speak:
            speak(result.companion_line)
        return result

    if args.phrase:
        handle_phrase(args.phrase)
        return 0

    if args.listen or args.loop:
        while True:
            phrase = listen_once()
            handle_phrase(phrase)
            if not args.loop:
                break
        return 0

    parser.error("provide --phrase, --listen, --loop, or --manifest")
    return 2


if __name__ == "__main__":
    raise SystemExit(run_cli())
