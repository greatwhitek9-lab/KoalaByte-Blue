#!/usr/bin/env python3
from __future__ import annotations

import json

from koalablue.esp32_dualeye_sphinx_bridge import (
    _command_grammar_for_root,
    resolve_pocketsphinx_model,
)


def main() -> int:
    root = resolve_pocketsphinx_model()
    if root is None:
        print(json.dumps({"ready": False, "reason": "model_not_found"}, indent=2))
        return 2

    grammar = _command_grammar_for_root(root)

    try:
        from pocketsphinx import Decoder

        Decoder(
            hmm=str(root / "en-us"),
            jsgf=str(grammar.path),
            dict=str(grammar.dictionary_path),
            samprate=16000,
            loglevel="ERROR",
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ready": False,
                    "reason": f"jsgf_compile_failed:{type(exc).__name__}:{exc}",
                    "grammar_path": str(grammar.path),
                    "dictionary_path": str(grammar.dictionary_path),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 3

    required = {
        "help",
        "voice commands",
        "status",
        "bluez status",
        "gatt readiness",
        "koala kapture",
        "capture metadata",
        "ear tag tx lab",
        "kruisin prompt status",
    }
    missing = sorted(required.difference(grammar.phrases))
    payload = {
        "ready": not missing,
        "status": "POCKETSPHINX_COMMAND_GRAMMAR_READY" if not missing else "POCKETSPHINX_COMMAND_GRAMMAR_INCOMPLETE",
        "model_root": str(root),
        "grammar_path": str(grammar.path),
        "dictionary_path": str(grammar.dictionary_path),
        "dictionary_words": grammar.dictionary_words,
        "custom_dictionary_words": list(grammar.custom_dictionary_words),
        "custom_dictionary_word_count": len(grammar.custom_dictionary_words),
        "accepted_phrases": len(grammar.phrases),
        "menu_phrases": len(grammar.menu_phrases),
        "rejected_oov_phrases": len(grammar.rejected_phrases),
        "capacity_skipped_phrases": len(grammar.capacity_skipped_phrases),
        "missing_dictionary_words": list(grammar.missing_dictionary_words),
        "missing_dictionary_word_count": len(grammar.missing_dictionary_words),
        "required_missing": missing,
        "first_commands": list(grammar.phrases[:40]),
        "first_menu_commands": list(grammar.menu_phrases[:30]),
        "first_rejected": list(grammar.rejected_phrases[:40]),
        "first_capacity_skipped": list(grammar.capacity_skipped_phrases[:40]),
        "wake_forms": ["killer koala", "hey killer koala"],
        "menu_verbs": ["run", "start", "launch", "open", "select"],
        "grammar_shape": "direct commands plus shared optional menu verb rule",
        "search_order": ["jsgf_commands", "whisper_if_available", "general_lm", "online_if_enabled"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ready"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
