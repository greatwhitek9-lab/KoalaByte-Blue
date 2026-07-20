#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue import menu_action_runner, menu_catalog  # noqa: E402
from koalablue import mopidy_player  # noqa: E402
from koalablue import music_speech_duck  # noqa: E402

STATUS_PATH = ROOT / "logs" / "music_player" / "music_player_readiness.json"


class FakeMopidyClient:
    state = "stopped"
    volume_value = 65
    current_uri = "file:///srv/koalabyte-music/test-track.ogg"
    calls: list[tuple[str, dict[str, Any] | None]] = []

    def __init__(self, rpc_url: str = mopidy_player.RPC_URL, timeout: float = 4.0) -> None:
        self.rpc_url = rpc_url
        self.timeout = timeout

    def rpc(self, method: str, params: dict[str, Any] | None = None) -> Any:
        type(self).calls.append((method, params))
        if method == "core.playback.get_state":
            return type(self).state
        if method == "core.mixer.get_volume":
            return type(self).volume_value
        if method == "core.playback.get_current_track":
            return {
                "name": "KoalaByte Test Track",
                "uri": type(self).current_uri,
                "artists": [{"name": "KillerKoala"}],
                "album": {"name": "Canopy Tests"},
                "length": 180000,
            }
        if method == "core.playback.get_stream_title":
            return "KoalaByte Test Stream"
        if method == "core.playback.get_time_position":
            return 42000
        if method == "core.tracklist.get_length":
            return 1
        if method in {"core.playback.play", "core.playback.resume"}:
            type(self).state = "playing"
            return None
        if method == "core.playback.pause":
            type(self).state = "paused"
            return None
        if method == "core.playback.stop":
            type(self).state = "stopped"
            return None
        if method in {"core.playback.next", "core.playback.previous"}:
            return None
        if method == "core.mixer.set_volume":
            type(self).volume_value = int((params or {}).get("volume", 0))
            return True
        if method == "core.library.refresh":
            return None
        if method == "core.tracklist.clear":
            return None
        if method == "core.tracklist.add":
            uris = list((params or {}).get("uris", []))
            type(self).current_uri = str(uris[0]) if uris else ""
            return [{"tlid": 7, "track": {"uri": type(self).current_uri}}]
        if method == "core.library.search":
            return [{"tracks": [{"name": "Found Track", "uri": "file:///found.ogg"}]}]
        raise AssertionError(f"unhandled fake Mopidy method: {method}")

    playback_state = mopidy_player.MopidyClient.playback_state
    volume = mopidy_player.MopidyClient.volume
    current_track = mopidy_player.MopidyClient.current_track
    stream_title = mopidy_player.MopidyClient.stream_title
    time_position = mopidy_player.MopidyClient.time_position
    tracklist_length = mopidy_player.MopidyClient.tracklist_length
    status = mopidy_player.MopidyClient.status
    play = mopidy_player.MopidyClient.play
    pause = mopidy_player.MopidyClient.pause
    toggle = mopidy_player.MopidyClient.toggle
    next = mopidy_player.MopidyClient.next
    previous = mopidy_player.MopidyClient.previous
    stop = mopidy_player.MopidyClient.stop
    change_volume = mopidy_player.MopidyClient.change_volume
    refresh_library = mopidy_player.MopidyClient.refresh_library
    play_uri = mopidy_player.MopidyClient.play_uri
    search_and_play = mopidy_player.MopidyClient.search_and_play


def require_marker(path: Path, marker: str, failures: list[str]) -> None:
    if not path.exists():
        failures.append(f"missing music player file: {path.relative_to(ROOT)}")
        return
    text = path.read_text(encoding="utf-8", errors="ignore")
    if marker not in text:
        failures.append(f"{path.relative_to(ROOT)} missing marker: {marker}")


def main() -> int:
    failures: list[str] = []
    results: dict[str, Any] = {}
    original_client = mopidy_player.MopidyClient
    original_config = os.environ.get("KOALABYTE_MUSIC_CONFIG")

    with tempfile.TemporaryDirectory(prefix="koalabyte-music-check-") as temp:
        temp_path = Path(temp)
        config_path = temp_path / "music.json"
        config_path.write_text(
            json.dumps(
                {
                    "engine": "mopidy",
                    "rpc_url": "http://127.0.0.1:6680/mopidy/rpc",
                    "radio_presets": {
                        "Test Radio": "https://radio.example.invalid/test.ogg"
                    },
                }
            ),
            encoding="utf-8",
        )
        os.environ["KOALABYTE_MUSIC_CONFIG"] = str(config_path)
        mopidy_player.MopidyClient = FakeMopidyClient  # type: ignore[assignment]
        mopidy_player.install_menu_catalog()

        try:
            main_commands = {
                str(row.get("command", "")) for row in menu_catalog.MAIN_MENU_ITEMS
            }
            if "submenu:music_player" not in main_commands:
                failures.append("Music Player submenu is missing from the main menu")

            submenu_commands = {
                str(row.get("command", ""))
                for row in menu_catalog.SUBMENU_ITEMS.get("music_player", [])
            }
            required_commands = {
                "music_status",
                "music_play",
                "music_pause",
                "music_toggle",
                "music_next",
                "music_previous",
                "music_stop",
                "music_volume_up",
                "music_volume_down",
                "music_refresh_library",
                "music_config_status",
                "music_preset:test_radio",
            }
            missing = sorted(required_commands - submenu_commands)
            if missing:
                failures.append(f"Music submenu missing commands: {missing}")

            for command in (
                "music_status",
                "music_play",
                "music_pause",
                "music_toggle",
                "music_next",
                "music_previous",
                "music_stop",
                "music_volume_up",
                "music_volume_down",
                "music_refresh_library",
                "music_config_status",
                "music_preset:test_radio",
            ):
                result = menu_action_runner.run_automated_menu_action(
                    command,
                    label=command,
                    group="Music Player",
                )
                results[command] = result
                if "ERROR" in str(result.get("status", "")).upper():
                    failures.append(f"offline fake music command failed: {command}: {result}")

            FakeMopidyClient.state = "playing"
            token = mopidy_player.prepare_speech_duck()
            if not token.was_playing or FakeMopidyClient.state != "paused":
                failures.append("prepare_speech_duck did not pause active music")
            mopidy_player.restore_after_speech(token)
            if FakeMopidyClient.state != "playing":
                failures.append("restore_after_speech did not resume music")

            duck_events: list[str] = []
            original_prepare = music_speech_duck.prepare_speech_duck
            original_restore = music_speech_duck.restore_after_speech
            music_speech_duck.prepare_speech_duck = lambda: duck_events.append("pause") or token  # type: ignore[assignment]
            music_speech_duck.restore_after_speech = lambda _token: duck_events.append("resume")  # type: ignore[assignment]

            class DummyBridge:
                def _play_response(self, text: str, channel: str) -> None:
                    duck_events.append(f"speak:{channel}:{text}")

            try:
                music_speech_duck.install_music_speech_ducking(DummyBridge)
                DummyBridge()._play_response("test speech", "pi-ai")
            finally:
                music_speech_duck.prepare_speech_duck = original_prepare  # type: ignore[assignment]
                music_speech_duck.restore_after_speech = original_restore  # type: ignore[assignment]
            if duck_events != ["pause", "speak:pi-ai:test speech", "resume"]:
                failures.append(f"speech duck wrapper order is wrong: {duck_events}")
        finally:
            mopidy_player.MopidyClient = original_client  # type: ignore[assignment]
            if original_config is None:
                os.environ.pop("KOALABYTE_MUSIC_CONFIG", None)
            else:
                os.environ["KOALABYTE_MUSIC_CONFIG"] = original_config

    class BrokenClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def status(self) -> dict[str, Any]:
            raise mopidy_player.MopidyPlayerError("simulated player outage")

    original_client = mopidy_player.MopidyClient
    mopidy_player.MopidyClient = BrokenClient  # type: ignore[assignment]
    try:
        error_result = mopidy_player.run_music_command("music_status")
    finally:
        mopidy_player.MopidyClient = original_client  # type: ignore[assignment]
    results["simulated_error"] = error_result
    if error_result.get("status") != "MUSIC_PLAYER_ERROR":
        failures.append("Mopidy outage did not return MUSIC_PLAYER_ERROR")

    require_marker(
        ROOT / "scripts/setup_mopidy_player.sh",
        "mopidy-archive-keyring.gpg",
        failures,
    )
    require_marker(
        ROOT / "scripts/setup_mopidy_player.sh",
        "hostname = 127.0.0.1",
        failures,
    )
    require_marker(
        ROOT / "scripts/run_esp32_dualeye_voice_bridge.py",
        "install_music_speech_ducking",
        failures,
    )
    require_marker(
        PI_ROOT / "koalablue/__init__.py",
        "install_music_player_menu",
        failures,
    )

    payload = {
        "status": "MUSIC_PLAYER_READY" if not failures else "MUSIC_PLAYER_INCOMPLETE",
        "engine": "mopidy",
        "execution_owner": "raspberry-pi",
        "sources": ["local_files", "internet_radio", "optional_extensions"],
        "menu_controls": sorted(mopidy_player.MUSIC_COMMANDS),
        "speech_ducking": True,
        "error_result_status": error_result.get("status"),
        "universal_error_sequence_compatible": error_result.get("status") == "MUSIC_PLAYER_ERROR",
        "fake_rpc_calls": FakeMopidyClient.calls,
        "results": results,
        "failures": failures,
        "updated_at": time.time(),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": payload["status"], "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
