from __future__ import annotations

from typing import Any, TypeVar

from .mopidy_player import prepare_speech_duck, restore_after_speech

BridgeType = TypeVar("BridgeType", bound=type)


def install_music_speech_ducking(bridge_class: BridgeType) -> BridgeType:
    """Pause Pi music for KillerKoala speech, then resume it afterward.

    The deployed DualEye service is the authoritative Pi speech owner. Wrapping
    that concrete class avoids coupling the reusable TTS or core voice modules to
    Mopidy while still covering AI replies, action results, and post-error digs.
    """

    if getattr(bridge_class, "_koalabyte_music_ducking_installed", False):
        return bridge_class

    original = bridge_class._play_response

    def ducked_play_response(self: Any, text: str, channel: str) -> None:
        token = prepare_speech_duck()
        try:
            original(self, text, channel)
        finally:
            restore_after_speech(token)

    bridge_class._play_response = ducked_play_response
    bridge_class._koalabyte_music_ducking_installed = True
    return bridge_class
