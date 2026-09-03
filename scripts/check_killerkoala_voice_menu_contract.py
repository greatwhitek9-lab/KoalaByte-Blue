#!/usr/bin/env python3
from __future__ import annotations

from koalablue.menu_voice_launcher import LAUNCH_VERBS, parse_menu_voice_launch
from koalablue.pocketsphinx_command_grammar import _candidate_phrases, normalize_spoken_phrase


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    candidates = {
        normalize_spoken_phrase(phrase)
        for phrase, is_menu in _candidate_phrases()
        if is_menu
    }

    for label in (
        "Bluetooth Tools",
        "Didgeridoo",
        "System / Companion",
        "Eucalyptus GPS Trail",
        "Dropbear Discovery Sweep",
    ):
        normalized = normalize_spoken_phrase(label)
        require(
            normalized in candidates,
            f"voice grammar is missing enabled menu/submenu label: {label}",
        )

    for verb in ("run", "start", "launch", "open", "select"):
        require(verb in LAUNCH_VERBS, f"menu voice launcher is missing verb: {verb}")

    submenu = parse_menu_voice_launch("killerkoala open Bluetooth Tools")
    require(submenu is not None, "Bluetooth Tools submenu voice phrase did not resolve")
    require(submenu.command == "submenu:bluetooth", f"wrong submenu command: {submenu.command}")

    leaf = parse_menu_voice_launch("killerkoala launch Eucalyptus GPS Trail")
    require(leaf is not None, "launch verb did not resolve a leaf menu action")
    require(leaf.command == "eucalyptus gps-trail", f"wrong leaf command: {leaf.command}")

    selected = parse_menu_voice_launch("killerkoala select Dropbear Discovery Sweep")
    require(selected is not None, "select verb did not resolve a leaf menu action")
    require(selected.command == "koala_bluez_scan", f"wrong selected command: {selected.command}")

    print("KillerKoala full voice-menu contract check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
