from __future__ import annotations

from typing import Any

PLAYER_NAME = "Lyrebird"
SUBMENU_COMMAND = "submenu:music_player"
DIRECT_PHRASES = {
    "play music",
    "play lyrebird",
}


def _wake_and_request(phrase: str, normalize: Any) -> tuple[bool, str, str]:
    normalized = normalize(phrase)
    # Speech recognizers may return the wake word as either one word or two.
    normalized = normalized.replace("killer koala", "killerkoala")
    tokens = normalized.split()
    wake_detected = "killerkoala" in tokens
    if wake_detected:
        wake_index = tokens.index("killerkoala")
        request = " ".join(tokens[wake_index + 1 :]).strip()
    else:
        request = normalized
    return wake_detected, request, normalized


def install_lyrebird_voice_alias() -> None:
    """Route ``KillerKoala, play music`` to the Lyrebird submenu.

    This is intentionally an application-opening command. It does not resume a
    stale Mopidy queue or choose a track without showing the Lyrebird browser.
    """

    from . import menu_voice_launcher as launcher

    if getattr(launcher, "_lyrebird_play_music_alias_patch", False):
        return

    original_parse = launcher.parse_menu_voice_launch
    original_manifest = launcher.build_menu_voice_manifest

    def parse_menu_voice_launch(
        phrase: str,
        require_wake_word: bool = True,
    ):
        match = original_parse(phrase, require_wake_word=require_wake_word)
        if match is not None:
            return match

        wake_detected, request, normalized = _wake_and_request(
            phrase,
            launcher._normalize,
        )
        if require_wake_word and not wake_detected:
            return None
        if request not in DIRECT_PHRASES:
            return None

        target: dict[str, Any] | None = None
        for entry in launcher._entry_rows():
            if (
                str(entry.get("command", "")) == SUBMENU_COMMAND
                and bool(entry.get("enabled", True))
            ):
                target = entry
                break
        if target is None:
            return None

        submenu = launcher.submenu_name_from_command(SUBMENU_COMMAND)
        return launcher.MenuVoiceMatch(
            phrase=phrase,
            normalized_phrase=normalized,
            wake_word_detected=wake_detected,
            verb="play",
            requested_item="music",
            menu=str(target.get("menu", "main")),
            label=str(target.get("label", PLAYER_NAME)),
            command=SUBMENU_COMMAND,
            group=str(target.get("group", PLAYER_NAME)),
            description=str(target.get("description", "Open Lyrebird")),
            is_submenu=True,
            submenu=submenu,
            alias=request,
        )

    def build_menu_voice_manifest() -> dict[str, Any]:
        manifest = original_manifest()
        aliases = manifest.setdefault("direct_application_aliases", [])
        if isinstance(aliases, list):
            record = {
                "phrase": "killerkoala play music",
                "alternate_wake_phrase": "killer koala play music",
                "command": SUBMENU_COMMAND,
                "behavior": "open_submenu",
                "application": PLAYER_NAME,
            }
            if record not in aliases:
                aliases.append(record)
        examples = manifest.setdefault("syntax", [])
        if isinstance(examples, list) and "killerkoala play music" not in examples:
            examples.append("killerkoala play music")
        return manifest

    launcher.parse_menu_voice_launch = parse_menu_voice_launch
    launcher.build_menu_voice_manifest = build_menu_voice_manifest
    launcher._lyrebird_play_music_alias_patch = True
