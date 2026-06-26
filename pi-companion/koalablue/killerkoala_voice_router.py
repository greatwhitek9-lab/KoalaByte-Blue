from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .killerkoala_voice_control import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_XP_PATH,
    execute_module,
    listen_once,
    module_manifest,
    parse_voice_command,
    speak,
)
from .menu_voice_launcher import build_menu_voice_manifest, route_menu_voice_launch


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


def route_voice_phrase(
    phrase: str,
    *,
    require_wake_word: bool = True,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    xp_path: Path = DEFAULT_XP_PATH,
    force_flexible_banter: bool = False,
):
    """Route a KillerKoala phrase.

    Menu/submenu launch syntax is checked first:

        killerkoala run <menu item or command>
        killerkoala open <menu item or command>

    If the phrase is not a menu launch command, it falls back to the existing
    KillerKoala voice module parser.
    """

    menu_result = route_menu_voice_launch(
        phrase,
        output_dir=output_dir / "menu_voice",
        xp_path=xp_path,
        require_wake_word=require_wake_word,
    )
    if menu_result is not None:
        return menu_result

    parsed = parse_voice_command(phrase, require_wake_word=require_wake_word)
    return execute_module(parsed, output_dir=output_dir, xp_path=xp_path, force_flexible_banter=force_flexible_banter)


def combined_manifest() -> dict[str, Any]:
    voice = module_manifest()
    voice["menu_voice_launch"] = build_menu_voice_manifest()
    voice["syntax"] = [
        "killerkoala run <menu item or command>",
        "killerkoala open <menu item or command>",
        "killerkoala voice commands",
    ]
    return voice


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="killerkoala spoken-command and menu voice router")
    parser.add_argument("--phrase", default=None, help="Typed spoken phrase, e.g. 'killerkoala open Bluetooth Tools'")
    parser.add_argument("--listen", action="store_true", help="Listen once from the microphone using optional SpeechRecognition/PyAudio")
    parser.add_argument("--loop", action="store_true", help="Continuously listen for commands until interrupted")
    parser.add_argument("--no-wake-required", action="store_true", help="Testing mode: do not require the killerkoala wake word")
    parser.add_argument("--flexible-banter", action="store_true", help="Allow optional tiny LLM/Ollama LoRA banter path for this response")
    parser.add_argument("--speak", action="store_true", help="Speak the response if optional pyttsx3 is installed")
    parser.add_argument("--manifest", action="store_true", help="Write and print supported voice and menu command manifest")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--xp-path", default=str(DEFAULT_XP_PATH))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    xp_path = Path(args.xp_path)

    if args.manifest:
        out = output_dir / "killerkoala_voice_and_menu_manifest.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        manifest = combined_manifest()
        out.write_text(json.dumps(_jsonable(manifest), indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({"manifest_path": str(out), "syntax": manifest.get("syntax", [])}, indent=2, sort_keys=True))
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
