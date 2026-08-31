from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .killerkoala_voice_control import VOICE_MODULES, voice_menu_actions

DEFAULT_MAX_PHRASES = 384
DEFAULT_GRAMMAR_PATH = Path("/tmp/koalabyte_pocketsphinx_commands.gram")
MENU_VERBS = ("run", "start", "launch", "open", "select")
CORE_COMMANDS = (
    "help",
    "voice commands",
    "list commands",
    "show modules",
    "status",
)
_TOKEN_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")
_VARIANT_RE = re.compile(r"\(\d+\)$")


@dataclass(frozen=True)
class CommandGrammar:
    path: Path
    phrases: tuple[str, ...]
    rejected_phrases: tuple[str, ...]
    dictionary_words: int


def normalize_spoken_phrase(value: str) -> str:
    text = str(value or "").lower().replace("’", "'")
    text = text.replace("&", " and ").replace("+", " and ")
    text = text.replace("-", " ").replace("/", " ").replace("_", " ")
    return " ".join(_TOKEN_RE.findall(text))


def _dictionary_words(root: Path) -> set[str]:
    words: set[str] = set()
    dictionary = root / "cmudict-en-us.dict"
    with dictionary.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            clean = line.strip()
            if not clean or clean.startswith(";;;"):
                continue
            head = clean.split(None, 1)[0].lower()
            words.add(_VARIANT_RE.sub("", head))
    return words


def _candidate_phrases() -> Iterable[str]:
    yield from CORE_COMMANDS

    for spec in VOICE_MODULES.values():
        for phrase in spec.phrases:
            yield phrase

    for action in voice_menu_actions():
        label = normalize_spoken_phrase(action.label)
        if not label:
            continue
        yield label
        for verb in MENU_VERBS:
            yield f"{verb} {label}"


def build_command_grammar(
    root: Path,
    *,
    grammar_path: Path | None = None,
    max_phrases: int | None = None,
) -> CommandGrammar:
    dictionary = _dictionary_words(root)
    limit = max_phrases or int(
        os.getenv("KOALABYTE_POCKETSPHINX_GRAMMAR_MAX_PHRASES", str(DEFAULT_MAX_PHRASES))
    )
    limit = max(16, min(limit, 1024))

    accepted: list[str] = []
    rejected: list[str] = []
    seen: set[str] = set()

    for candidate in _candidate_phrases():
        phrase = normalize_spoken_phrase(candidate)
        if not phrase or phrase in seen:
            continue
        seen.add(phrase)
        tokens = phrase.split()
        if not tokens or any(token not in dictionary for token in tokens):
            rejected.append(phrase)
            continue
        accepted.append(phrase)
        if len(accepted) >= limit:
            break

    # The wake phrase must be representable by the installed dictionary or JSGF
    # compilation will fail before any command can be decoded.
    for required in ("killer", "koala"):
        if required not in dictionary:
            raise RuntimeError(f"PocketSphinx dictionary is missing required wake word: {required}")

    if not accepted:
        raise RuntimeError("PocketSphinx command grammar has no dictionary-compatible commands")

    body = " |\n    ".join(accepted)
    grammar = (
        "#JSGF V1.0;\n"
        "grammar killerkoala_commands;\n"
        "public <command> = (killer koala | hey killer koala) (\n"
        f"    {body}\n"
        ");\n"
    )

    destination = grammar_path or Path(
        os.getenv(
            "KOALABYTE_POCKETSPHINX_COMMAND_GRAMMAR_PATH",
            str(DEFAULT_GRAMMAR_PATH),
        )
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(grammar, encoding="utf-8")

    return CommandGrammar(
        path=destination,
        phrases=tuple(accepted),
        rejected_phrases=tuple(rejected),
        dictionary_words=len(dictionary),
    )


__all__ = [
    "CommandGrammar",
    "CORE_COMMANDS",
    "DEFAULT_GRAMMAR_PATH",
    "DEFAULT_MAX_PHRASES",
    "build_command_grammar",
    "normalize_spoken_phrase",
]
