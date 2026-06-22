from __future__ import annotations

import argparse
import json
from pathlib import Path

from .killerkoala_face_bridge import show_action_face, show_speaking_face, show_thinking_face, show_wake_face
from .killerkoala_voice_control import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_XP_PATH,
    VOICE_MODULES,
    _jsonable,
    _write_json,
    execute_module,
    listen_once,
    module_manifest,
    parse_voice_command,
    speak,
)


def run_cli() -> int:
    parser = argparse.ArgumentParser(description="killerkoala spoken-command module executor with split koala face output")
    parser.add_argument("--phrase", default=None, help="Typed spoken phrase for CI/testing, e.g. 'killerkoala run bluez inventory'")
    parser.add_argument("--listen", action="store_true", help="Listen once from the microphone using optional SpeechRecognition/PyAudio")
    parser.add_argument("--loop", action="store_true", help="Continuously listen for commands until interrupted")
    parser.add_argument("--no-wake-required", action="store_true", help="Testing mode: do not require the killerkoala wake word")
    parser.add_argument("--flexible-banter", action="store_true", help="Allow optional tiny LLM/Ollama LoRA banter path for this response")
    parser.add_argument("--speak", action="store_true", help="Speak the response if optional pyttsx3 is installed")
    parser.add_argument("--manifest", action="store_true", help="Write and print supported module manifest")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--xp-path", default=str(DEFAULT_XP_PATH))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    xp_path = Path(args.xp_path)

    if args.manifest:
        out = output_dir / "killerkoala_voice_modules.json"
        _write_json(out, module_manifest())
        print(json.dumps({"manifest_path": str(out), "modules": sorted(VOICE_MODULES)}, indent=2, sort_keys=True))
        return 0

    def handle_phrase(phrase: str):
        parsed = parse_voice_command(phrase, require_wake_word=not args.no_wake_required)
        if parsed.wake_word_detected:
            show_wake_face("killerkoala heard")
        if parsed.module_key and parsed.module_key in VOICE_MODULES:
            show_action_face(VOICE_MODULES[parsed.module_key].title, f"{VOICE_MODULES[parsed.module_key].title} selected")
        else:
            show_thinking_face("sussing the phrase")
        result = execute_module(parsed, output_dir=output_dir, xp_path=xp_path, force_flexible_banter=args.flexible_banter)
        show_speaking_face(result.companion_line, success=result.status == "success", stopped=result.status != "success")
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
