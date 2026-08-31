from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .killerkoala_voice_control import VOICE_MODULES, voice_menu_actions

DEFAULT_MAX_PHRASES = 512
DEFAULT_GRAMMAR_PATH = Path("/tmp/koalabyte_pocketsphinx_commands.gram")
DEFAULT_DICTIONARY_PATH = Path("/tmp/koalabyte_pocketsphinx_commands.dict")
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
_DIGIT_WORDS = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}

# Project terms are deliberately local additions. The distro CMU dictionary is
# never modified. Pronunciations use the same ARPAbet phone inventory as CMUdict.
CUSTOM_PRONUNCIATIONS: dict[str, str] = {
    "bluez": "B L UW Z",
    "ble": "B IY EH L IY",
    "btmon": "B IY T IY M AA N",
    "gatt": "G AE T",
    "hci": "EY CH S IY AY",
    "gumleaf": "G AH M L IY F",
    "gumnut": "G AH M N AH T",
    "dropbear": "D R AA P B EH R",
    "billabong": "B IH L AH B AO NG",
    "kookaburra": "K UH K AH B ER AH",
    "koalabyte": "K OW AA L AH B AY T",
    "killerkoala": "K IH L ER K OW AA L AH",
    "koalagotchi": "K OW AA L AH G OW T CH IY",
    "kapture": "K AE P CH ER",
    "kry": "K R AY",
    "heltec": "HH EH L T EH K",
    "innomaker": "IH N OW M EY K ER",
    "didgeridoo": "D IH JH ER IY D UW",
    "eucalyptus": "Y UW K AH L IH P T AH S",
    "suss": "S AH S",
    "squiz": "S K W IH Z",
    "gumtrees": "G AH M T R IY Z",
    "wifi": "W AY F AY",
    "gpio": "JH IY P IY AY OW",
    "gnss": "JH IY EH N EH S EH S",
    "gps": "JH IY P IY EH S",
    "nmea": "EH N EH M IY EY",
    "sdr": "EH S D IY AA R",
    "uart": "Y UW AA R T",
    "esp": "IY EH S P IY",
    "kruisin": "K R UW Z IH N",
    "metadata": "M EH T AH D EY T AH",
    "treehouse": "T R IY HH AW S",
    "tx": "T IY EH K S",
    "rx": "AA R EH K S",
}


@dataclass(frozen=True)
class CommandGrammar:
    path: Path
    dictionary_path: Path
    phrases: tuple[str, ...]
    menu_phrases: tuple[str, ...]
    rejected_phrases: tuple[str, ...]
    missing_dictionary_words: tuple[str, ...]
    dictionary_words: int
    custom_dictionary_words: tuple[str, ...]


def _expand_digits(value: str) -> str:
    out: list[str] = []
    for char in value:
        if char in _DIGIT_WORDS:
            out.extend((" ", _DIGIT_WORDS[char], " "))
        else:
            out.append(char)
    return "".join(out)


def normalize_spoken_phrase(value: str) -> str:
    text = str(value or "").lower().replace("’", "'")
    text = text.replace("wi-fi", "wifi")
    text = _expand_digits(text)
    text = text.replace("&", " and ").replace("+", " and ")
    text = text.replace("-", " ").replace("/", " ").replace("_", " ")
    return " ".join(_TOKEN_RE.findall(text))


def _load_dictionary(root: Path) -> tuple[set[str], list[str]]:
    words: set[str] = set()
    lines: list[str] = []
    dictionary = root / "cmudict-en-us.dict"
    with dictionary.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            clean = line.rstrip("\n")
            lines.append(clean)
            stripped = clean.strip()
            if not stripped or stripped.startswith(";;;"):
                continue
            head = stripped.split(None, 1)[0].lower()
            words.add(_VARIANT_RE.sub("", head))
    return words, lines


def _write_augmented_dictionary(
    root: Path,
    destination: Path,
) -> tuple[set[str], tuple[str, ...]]:
    words, lines = _load_dictionary(root)
    added: list[str] = []
    for word, pronunciation in sorted(CUSTOM_PRONUNCIATIONS.items()):
        if word in words:
            continue
        lines.append(f"{word} {pronunciation}")
        words.add(word)
        added.append(word)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return words, tuple(added)


def _candidate_phrases() -> Iterable[tuple[str, bool]]:
    for phrase in CORE_COMMANDS:
        yield phrase, False

    for spec in VOICE_MODULES.values():
        for phrase in spec.phrases:
            yield phrase, False

    # Menu labels are added once. The JSGF grammar supplies one shared optional
    # verb rule instead of duplicating each label for run/start/launch/open/select.
    for action in voice_menu_actions():
        label = normalize_spoken_phrase(action.label)
        if label:
            yield label, True


def build_command_grammar(
    root: Path,
    *,
    grammar_path: Path | None = None,
    dictionary_path: Path | None = None,
    max_phrases: int | None = None,
) -> CommandGrammar:
    destination_dictionary = dictionary_path or Path(
        os.getenv(
            "KOALABYTE_POCKETSPHINX_COMMAND_DICTIONARY_PATH",
            str(DEFAULT_DICTIONARY_PATH),
        )
    )
    dictionary, custom_words = _write_augmented_dictionary(
        root, destination_dictionary
    )

    limit = max_phrases or int(
        os.getenv("KOALABYTE_POCKETSPHINX_GRAMMAR_MAX_PHRASES", str(DEFAULT_MAX_PHRASES))
    )
    limit = max(16, min(limit, 1024))

    accepted: list[str] = []
    direct: list[str] = []
    menu: list[str] = []
    rejected: list[str] = []
    missing_words: set[str] = set()
    seen: set[str] = set()

    for candidate, is_menu in _candidate_phrases():
        phrase = normalize_spoken_phrase(candidate)
        if not phrase or phrase in seen:
            continue
        seen.add(phrase)
        tokens = phrase.split()
        missing = [token for token in tokens if token not in dictionary]
        if not tokens or missing:
            rejected.append(phrase)
            missing_words.update(missing)
            continue
        accepted.append(phrase)
        if is_menu:
            menu.append(phrase)
        else:
            direct.append(phrase)
        if len(accepted) >= limit:
            break

    for required in ("killer", "koala"):
        if required not in dictionary:
            raise RuntimeError(f"PocketSphinx dictionary is missing required wake word: {required}")

    if not accepted:
        raise RuntimeError("PocketSphinx command grammar has no dictionary-compatible commands")

    rules: list[str] = [
        "#JSGF V1.0;",
        "grammar killerkoala_commands;",
    ]

    alternatives: list[str] = []
    if direct:
        direct_body = " |\n    ".join(direct)
        rules.append(f"<direct_command> = (\n    {direct_body}\n);")
        alternatives.append("<direct_command>")

    if menu:
        verb_body = " | ".join(MENU_VERBS)
        menu_body = " |\n    ".join(menu)
        rules.append(f"<menu_verb> = ({verb_body});")
        rules.append(f"<menu_label> = (\n    {menu_body}\n);")
        rules.append("<menu_command> = [<menu_verb>] <menu_label>;")
        alternatives.append("<menu_command>")

    if not alternatives:
        raise RuntimeError("PocketSphinx command grammar has no usable command rules")

    rules.append(
        "public <command> = (killer koala | hey killer koala) ("
        + " | ".join(alternatives)
        + ");"
    )
    grammar = "\n".join(rules) + "\n"

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
        dictionary_path=destination_dictionary,
        phrases=tuple(accepted),
        menu_phrases=tuple(menu),
        rejected_phrases=tuple(rejected),
        missing_dictionary_words=tuple(sorted(missing_words)),
        dictionary_words=len(dictionary),
        custom_dictionary_words=custom_words,
    )


__all__ = [
    "CommandGrammar",
    "CORE_COMMANDS",
    "CUSTOM_PRONUNCIATIONS",
    "DEFAULT_DICTIONARY_PATH",
    "DEFAULT_GRAMMAR_PATH",
    "DEFAULT_MAX_PHRASES",
    "MENU_VERBS",
    "build_command_grammar",
    "normalize_spoken_phrase",
]
