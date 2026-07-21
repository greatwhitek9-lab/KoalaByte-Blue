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

STATUS_PATH = ROOT / "logs" / "music_player" / "lyrebird_browser_readiness.json"


class FakeMopidyClient:
    state = "stopped"
    volume_value = 60
    queue: list[str] = []
    current_index = 0
    current_track_payload: dict[str, Any] = {}
    calls: list[tuple[str, dict[str, Any] | None]] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    @classmethod
    def reset(cls) -> None:
        cls.state = "stopped"
        cls.volume_value = 60
        cls.queue = []
        cls.current_index = 0
        cls.current_track_payload = {}
        cls.calls = []

    @classmethod
    def _select_index(cls, index: int) -> None:
        if not cls.queue:
            cls.current_track_payload = {}
            return
        cls.current_index = max(0, min(len(cls.queue) - 1, index))
        uri = cls.queue[cls.current_index]
        cls.current_track_payload = {
            "name": Path(uri.split("?", 1)[0]).stem,
            "uri": uri,
            "artists": [{"name": "KillerKoala"}],
            "album": {"name": "Lyrebird Tests"},
            "length": 180000,
        }

    def rpc(self, method: str, params: dict[str, Any] | None = None) -> Any:
        type(self).calls.append((method, params))
        if method == "core.playback.get_state":
            return type(self).state
        if method == "core.mixer.get_volume":
            return type(self).volume_value
        if method == "core.playback.get_current_track":
            return dict(type(self).current_track_payload)
        if method == "core.playback.get_stream_title":
            return ""
        if method == "core.playback.get_time_position":
            return 0
        if method == "core.tracklist.get_length":
            return len(type(self).queue)
        if method == "core.tracklist.clear":
            type(self).queue = []
            type(self).current_index = 0
            type(self).current_track_payload = {}
            return None
        if method == "core.tracklist.add":
            type(self).queue = [str(uri) for uri in (params or {}).get("uris", [])]
            return [
                {"tlid": index + 1, "track": {"uri": uri}}
                for index, uri in enumerate(type(self).queue)
            ]
        if method == "core.playback.play":
            tlid = (params or {}).get("tlid") if params else None
            if tlid is not None:
                type(self)._select_index(int(tlid) - 1)
            elif type(self).queue and not type(self).current_track_payload:
                type(self)._select_index(type(self).current_index)
            type(self).state = "playing"
            return None
        if method == "core.playback.resume":
            type(self).state = "playing"
            return None
        if method == "core.playback.pause":
            type(self).state = "paused"
            return None
        if method == "core.playback.stop":
            type(self).state = "stopped"
            return None
        if method == "core.playback.next":
            type(self)._select_index(type(self).current_index + 1)
            type(self).state = "playing"
            return None
        if method == "core.playback.previous":
            type(self)._select_index(type(self).current_index - 1)
            type(self).state = "playing"
            return None
        if method == "core.playback.seek":
            return True
        if method == "core.playback.get_current_tl_track":
            if not type(self).current_track_payload:
                return None
            return {
                "tlid": type(self).current_index + 1,
                "track": dict(type(self).current_track_payload),
            }
        if method == "core.mixer.set_volume":
            type(self).volume_value = int((params or {}).get("volume", 0))
            return True
        if method == "core.library.refresh":
            return None
        raise AssertionError(f"unhandled fake Mopidy method: {method}")

    def playback_state(self) -> str:
        return str(self.rpc("core.playback.get_state") or "stopped")

    def volume(self) -> int | None:
        value = self.rpc("core.mixer.get_volume")
        return int(value) if value is not None else None

    def current_track(self) -> dict[str, Any] | None:
        track = self.rpc("core.playback.get_current_track")
        return dict(track) if isinstance(track, dict) else None

    def stream_title(self) -> str:
        return str(self.rpc("core.playback.get_stream_title") or "")

    def time_position(self) -> int:
        return int(self.rpc("core.playback.get_time_position") or 0)

    def tracklist_length(self) -> int:
        return int(self.rpc("core.tracklist.get_length") or 0)

    def status(self) -> dict[str, Any]:
        track = self.current_track() or {}
        artists = track.get("artists") if isinstance(track, dict) else []
        return {
            "status": "MUSIC_PLAYER_READY",
            "engine": "mopidy",
            "rpc_url": "http://127.0.0.1:6680/mopidy/rpc",
            "playback_state": self.playback_state(),
            "volume": self.volume(),
            "tracklist_length": self.tracklist_length(),
            "time_position_ms": self.time_position(),
            "track": {
                "name": str(track.get("name") or ""),
                "uri": str(track.get("uri") or ""),
                "artists": [
                    str(artist.get("name") or "")
                    for artist in (artists or [])
                    if isinstance(artist, dict)
                ],
                "album": str((track.get("album") or {}).get("name") or "")
                if isinstance(track.get("album"), dict)
                else "",
                "length_ms": track.get("length"),
                "stream_title": self.stream_title(),
            },
        }

    def play(self) -> None:
        if self.playback_state() == "paused":
            self.rpc("core.playback.resume")
        else:
            self.rpc("core.playback.play")

    def pause(self) -> None:
        self.rpc("core.playback.pause")

    def toggle(self) -> str:
        if self.playback_state() == "playing":
            self.pause()
            return "paused"
        self.play()
        return "playing"

    def next(self) -> None:
        self.rpc("core.playback.next")

    def previous(self) -> None:
        self.rpc("core.playback.previous")

    def stop(self) -> None:
        self.rpc("core.playback.stop")

    def change_volume(self, delta: int) -> int:
        target = max(0, min(100, int(self.volume() or 50) + int(delta)))
        self.rpc("core.mixer.set_volume", {"volume": target})
        return target

    def refresh_library(self) -> None:
        self.rpc("core.library.refresh")

    def play_uri(self, uri: str) -> dict[str, Any]:
        self.rpc("core.tracklist.clear")
        added = self.rpc("core.tracklist.add", {"uris": [uri]})
        self.rpc("core.playback.play", {"tlid": 1})
        return dict(added[0])


def main() -> int:
    failures: list[str] = []
    checked: dict[str, Any] = {}

    with tempfile.TemporaryDirectory(prefix="koalabyte-lyrebird-check-") as temp:
        temp_path = Path(temp)
        music_dir = temp_path / "music"
        music_dir.mkdir()
        for index in range(10):
            suffix = ".mp3" if index % 2 == 0 else ".ogg"
            (music_dir / f"{index:02d}-canopy-track{suffix}").write_bytes(b"test")
        nested = music_dir / "album"
        nested.mkdir()
        (nested / "hidden-gem.flac").write_bytes(b"test")

        config_path = temp_path / "music.json"
        config_path.write_text(
            json.dumps(
                {
                    "engine": "mopidy",
                    "radio_presets": {
                        "Bush Radio": "https://radio.example.invalid/bush.ogg",
                        "Outback Rock": "https://radio.example.invalid/rock.mp3",
                        "Rainforest FM": "https://radio.example.invalid/rain.aac",
                    },
                }
            ),
            encoding="utf-8",
        )

        os.environ["KOALABYTE_MUSIC_DIR"] = str(music_dir)
        os.environ["KOALABYTE_MUSIC_CONFIG"] = str(config_path)
        os.environ["KOALABYTE_MENU_SYNC"] = "0"

        from koalablue import lyrebird_browser, menu_catalog, menu_display_sync, mopidy_player
        from koalablue.menu_ui import MenuItem, MenuSelectionScreen

        original_client = mopidy_player.MopidyClient
        original_status_path = mopidy_player.STATUS_PATH
        mopidy_player.MopidyClient = FakeMopidyClient  # type: ignore[assignment]
        mopidy_player.STATUS_PATH = temp_path / "status.json"
        FakeMopidyClient.reset()

        try:
            root_commands = {
                str(row.get("command", ""))
                for row in menu_catalog._entries_for_menu(lyrebird_browser.ROOT_MENU)
            }
            if f"submenu:{lyrebird_browser.SONGS_MENU}" not in root_commands:
                failures.append("Lyrebird root menu is missing Uploaded Songs")
            if f"submenu:{lyrebird_browser.RADIO_MENU}" not in root_commands:
                failures.append("Lyrebird root menu is missing Radio Stations")

            song_rows = menu_catalog.make_menu_items(MenuItem, lyrebird_browser.SONGS_MENU)
            song_commands = [row.command for row in song_rows if row.command.startswith("music_song:")]
            if len(song_commands) != 11:
                failures.append(f"expected 11 uploaded song rows, found {len(song_commands)}")

            song_menu = MenuSelectionScreen(items=song_rows, visible_rows=4)
            song_menu.menu_name = lyrebird_browser.SONGS_MENU
            for _ in range(7):
                song_menu.handle_command("down")
            if song_menu.scroll_offset <= 0:
                failures.append("Uploaded Songs list did not scroll beyond the first visible page")

            first_song_index = next(
                index for index, row in enumerate(song_menu.items)
                if row.command.startswith("music_song:")
            )
            song_menu.selected_index = first_song_index
            song_menu._clamp_scroll_to_selection()
            selected_command = song_menu.selected_item.command
            play_event = song_menu.handle_command("enter")
            status = json.loads(mopidy_player.STATUS_PATH.read_text(encoding="utf-8"))
            if play_event is None or play_event.command != selected_command:
                failures.append("Enter/K3 did not play the highlighted uploaded song")
            if status.get("playback_state") != "playing":
                failures.append("highlighted uploaded song did not enter playing state")
            if song_menu.display_mode != "menu":
                failures.append("song selection did not retain the Lyrebird list display")

            menu_payload = menu_display_sync.build_menu_sync_payload(song_menu, play_event)
            if not str(menu_payload.get("selected_label", "")).startswith("Playing:"):
                failures.append("left-eye selected_label was not replaced with now-playing text")
            if len(menu_payload.get("visible_items", [])) > 4:
                failures.append("right-eye song list exceeded the configured visible-row window")
            heltec_playing = menu_display_sync._heltec_face_payload(menu_payload)
            if heltec_playing.get("lyrebird_dance") is not True:
                failures.append("Heltec did not receive the Lyrebird dance state while playing")
            if heltec_playing.get("state") != "koalagotchi_persistent":
                failures.append("Heltec dance did not use the persistent Koalagotchi animation")

            toggle_event = song_menu.handle_command("enter")
            paused = json.loads(mopidy_player.STATUS_PATH.read_text(encoding="utf-8"))
            if toggle_event is None or toggle_event.command != "music_toggle":
                failures.append("Enter/K3 on the active song did not become Play/Pause")
            if paused.get("playback_state") != "paused":
                failures.append("Enter/K3 did not pause active Lyrebird playback")
            paused_payload = menu_display_sync.build_menu_sync_payload(song_menu, toggle_event)
            heltec_paused = menu_display_sync._heltec_face_payload(paused_payload)
            if heltec_paused.get("state") != "koalagotchi_exit":
                failures.append("Heltec dance did not clear when Lyrebird paused")

            song_menu.handle_command("enter")
            if json.loads(mopidy_player.STATUS_PATH.read_text(encoding="utf-8")).get("playback_state") != "playing":
                failures.append("Enter/K3 did not resume paused Lyrebird playback")

            before_next = FakeMopidyClient.current_index
            next_event = song_menu.handle_command("forward")
            if next_event is None or next_event.command != "music_next":
                failures.append("K4/forward did not route to music_next")
            if FakeMopidyClient.current_index <= before_next:
                failures.append("K4/forward did not advance the queued song")

            restart_event = song_menu.handle_command("back")
            previous_event = song_menu.handle_command("back")
            if restart_event is None or restart_event.command != "music_restart":
                failures.append("first K2/back press did not restart the current track")
            if previous_event is None or previous_event.command != "music_previous":
                failures.append("second rapid K2/back press did not select the previous track")

            radio_rows = menu_catalog.make_menu_items(MenuItem, lyrebird_browser.RADIO_MENU)
            radio_commands = [row.command for row in radio_rows if row.command.startswith("music_preset:")]
            if len(radio_commands) != 3:
                failures.append(f"expected 3 radio station rows, found {len(radio_commands)}")
            radio_menu = MenuSelectionScreen(items=radio_rows, visible_rows=2)
            radio_menu.menu_name = lyrebird_browser.RADIO_MENU
            radio_menu.selected_index = next(
                index for index, row in enumerate(radio_menu.items)
                if row.command.startswith("music_preset:")
            )
            radio_event = radio_menu.handle_command("select")
            radio_status = json.loads(mopidy_player.STATUS_PATH.read_text(encoding="utf-8"))
            if radio_event is None or not radio_event.command.startswith("music_preset:"):
                failures.append("radio station selection did not route through the Lyrebird player")
            if radio_status.get("media_kind") != "internet_radio":
                failures.append("radio station selection did not record internet_radio media kind")

            checked = {
                "uploaded_song_count": len(song_commands),
                "radio_station_count": len(radio_commands),
                "scroll_offset": song_menu.scroll_offset,
                "left_eye_now_playing": menu_payload.get("selected_label"),
                "right_eye_visible_rows": len(menu_payload.get("visible_items", [])),
                "heltec_state_playing": heltec_playing.get("state"),
                "heltec_state_paused": heltec_paused.get("state"),
                "enter_active_command": toggle_event.command if toggle_event else None,
                "forward_command": next_event.command if next_event else None,
                "first_back_command": restart_event.command if restart_event else None,
                "double_back_command": previous_event.command if previous_event else None,
                "fake_rpc_call_count": len(FakeMopidyClient.calls),
            }
        finally:
            mopidy_player.MopidyClient = original_client  # type: ignore[assignment]
            mopidy_player.STATUS_PATH = original_status_path

    payload = {
        "status": "LYREBIRD_BROWSER_READY" if not failures else "LYREBIRD_BROWSER_INCOMPLETE",
        "checked": checked,
        "failures": failures,
        "updated_at": time.time(),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
