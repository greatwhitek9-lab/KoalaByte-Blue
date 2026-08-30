from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

SUBMENU_NAME = "music_player"
GROUP_NAME = "Music Player"
RPC_URL = os.getenv("KOALABYTE_MOPIDY_RPC_URL", "http://127.0.0.1:6680/mopidy/rpc")
OUTPUT_DIR = Path("logs/music_player")
STATUS_PATH = OUTPUT_DIR / "music_player_status.json"
DEFAULT_CONFIG_PATHS = (
    Path("/etc/koalabyte-blue/music.json"),
    Path.home() / ".config" / "koalabyte-blue" / "music.json",
)

MUSIC_COMMANDS = {
    "music_status",
    "music_now_playing",
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
}


class MopidyPlayerError(RuntimeError):
    pass


@dataclass(frozen=True)
class SpeechDuckToken:
    was_playing: bool
    state: str
    volume: int | None
    reason: str = ""


class MopidyClient:
    def __init__(self, rpc_url: str = RPC_URL, timeout: float = 4.0) -> None:
        self.rpc_url = rpc_url
        self.timeout = timeout
        self._request_id = 0

    def rpc(self, method: str, params: dict[str, Any] | None = None) -> Any:
        self._request_id += 1
        body: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
        }
        if params:
            body["params"] = params
        try:
            response = httpx.post(
                self.rpc_url,
                json=body,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise MopidyPlayerError(
                f"Mopidy is unavailable at {self.rpc_url}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise MopidyPlayerError("Mopidy returned a non-object JSON-RPC response")
        if payload.get("error"):
            error = payload["error"]
            if isinstance(error, dict):
                message = str(error.get("message") or error)
            else:
                message = str(error)
            raise MopidyPlayerError(f"Mopidy {method} failed: {message}")
        return payload.get("result")

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
        artist_names = [
            str(artist.get("name") or "")
            for artist in (artists or [])
            if isinstance(artist, dict) and artist.get("name")
        ]
        return {
            "status": "MUSIC_PLAYER_READY",
            "engine": "mopidy",
            "rpc_url": self.rpc_url,
            "playback_state": self.playback_state(),
            "volume": self.volume(),
            "tracklist_length": self.tracklist_length(),
            "time_position_ms": self.time_position(),
            "track": {
                "name": str(track.get("name") or ""),
                "uri": str(track.get("uri") or ""),
                "artists": artist_names,
                "album": str((track.get("album") or {}).get("name") or "")
                if isinstance(track.get("album"), dict)
                else "",
                "length_ms": track.get("length"),
                "stream_title": self.stream_title(),
            },
        }

    def play(self) -> None:
        state = self.playback_state()
        if state == "paused":
            self.rpc("core.playback.resume")
        else:
            self.rpc("core.playback.play")

    def pause(self) -> None:
        self.rpc("core.playback.pause")

    def toggle(self) -> str:
        state = self.playback_state()
        if state == "playing":
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
        current = self.volume()
        if current is None:
            raise MopidyPlayerError("Mopidy mixer does not expose a software volume")
        target = max(0, min(100, current + int(delta)))
        success = self.rpc("core.mixer.set_volume", {"volume": target})
        if success is False:
            raise MopidyPlayerError(f"Mopidy refused volume {target}")
        return target

    def refresh_library(self) -> None:
        self.rpc("core.library.refresh")

    def play_uri(self, uri: str) -> dict[str, Any]:
        resolved = str(uri or "").strip()
        if not resolved:
            raise MopidyPlayerError("music URI is empty")
        self.rpc("core.tracklist.clear")
        added = self.rpc("core.tracklist.add", {"uris": [resolved]})
        if not isinstance(added, list) or not added:
            raise MopidyPlayerError(f"Mopidy could not add URI: {resolved}")
        first = added[0] if isinstance(added[0], dict) else {}
        tlid = first.get("tlid")
        if tlid is None:
            self.rpc("core.playback.play")
        else:
            self.rpc("core.playback.play", {"tlid": tlid})
        return {"uri": resolved, "tlid": tlid}

    def search_and_play(self, query: str) -> dict[str, Any]:
        resolved = " ".join(str(query or "").split())
        if not resolved:
            raise MopidyPlayerError("music search query is empty")
        results = self.rpc(
            "core.library.search",
            {"query": {"any": [resolved]}},
        )
        for result in results or []:
            if not isinstance(result, dict):
                continue
            for track in result.get("tracks") or []:
                if isinstance(track, dict) and track.get("uri"):
                    played = self.play_uri(str(track["uri"]))
                    played["query"] = resolved
                    played["track"] = track
                    return played
        raise MopidyPlayerError(f"No Mopidy library result matched: {resolved}")


def _config_path() -> Path:
    override = os.getenv("KOALABYTE_MUSIC_CONFIG", "").strip()
    if override:
        return Path(override)
    for path in DEFAULT_CONFIG_PATHS:
        try:
            if path.exists():
                return path
        except OSError:
            # A system config may exist but be unreadable to an incomplete or
            # upgraded install. Menu enumeration must remain available so the
            # one-shot can repair permissions instead of crashing at import time.
            continue
    return DEFAULT_CONFIG_PATHS[0]


def load_music_config() -> dict[str, Any]:
    try:
        path = _config_path()
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        # Radio presets are optional. Treat a missing, unreadable, or malformed
        # config as an empty preset list; setup_mopidy_player.sh repairs the
        # system file ownership/mode for the normal KoalaByte service user.
        return {}


def radio_presets() -> dict[str, str]:
    raw = load_music_config().get("radio_presets", {})
    if not isinstance(raw, dict):
        return {}
    return {
        " ".join(str(name).split())[:40]: str(uri).strip()
        for name, uri in raw.items()
        if str(name).strip() and str(uri).strip()
    }


def _safe_preset_key(name: str) -> str:
    return "_".join(part for part in "".join(
        ch.lower() if ch.isalnum() else " " for ch in name
    ).split())[:48]


def _preset_commands() -> dict[str, tuple[str, str]]:
    return {
        f"music_preset:{_safe_preset_key(name)}": (name, uri)
        for name, uri in radio_presets().items()
    }


def _is_music_command(command: str) -> bool:
    return command in MUSIC_COMMANDS or command.startswith("music_preset:")


def _write_status(payload: dict[str, Any]) -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload.setdefault("updated_at", time.time())
    STATUS_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def run_music_command(command: str) -> dict[str, Any]:
    client = MopidyClient()
    preset_map = _preset_commands()
    try:
        if command in {"music_status", "music_now_playing"}:
            result = client.status()
        elif command == "music_play":
            client.play()
            result = client.status()
        elif command == "music_pause":
            client.pause()
            result = client.status()
        elif command == "music_toggle":
            result = {"playback_state": client.toggle(), **client.status()}
        elif command == "music_next":
            client.next()
            result = client.status()
        elif command == "music_previous":
            client.previous()
            result = client.status()
        elif command == "music_stop":
            client.stop()
            result = client.status()
        elif command == "music_volume_up":
            result = {"volume": client.change_volume(5), **client.status()}
        elif command == "music_volume_down":
            result = {"volume": client.change_volume(-5), **client.status()}
        elif command == "music_refresh_library":
            client.refresh_library()
            result = {"status": "MUSIC_LIBRARY_REFRESH_REQUESTED", **client.status()}
        elif command == "music_config_status":
            result = {
                "status": "MUSIC_CONFIG_READY",
                "config_path": str(_config_path()),
                "radio_presets": list(radio_presets().keys()),
                "rpc_url": client.rpc_url,
            }
        elif command in preset_map:
            name, uri = preset_map[command]
            result = {
                "status": "MUSIC_PRESET_PLAYING",
                "preset": name,
                **client.play_uri(uri),
                **client.status(),
            }
        else:
            raise MopidyPlayerError(f"unknown music command: {command}")
        result.setdefault("command", command)
        result.setdefault("manual_prompt_required", False)
        result.setdefault("execution_owner", "raspberry-pi")
        return _write_status(result)
    except Exception as exc:
        return _write_status(
            {
                "status": "MUSIC_PLAYER_ERROR",
                "command": command,
                "error": str(exc),
                "execution_owner": "raspberry-pi",
                "manual_prompt_required": False,
            }
        )


def prepare_speech_duck() -> SpeechDuckToken:
    try:
        client = MopidyClient(timeout=1.5)
        state = client.playback_state()
        volume = client.volume()
        if state == "playing":
            client.pause()
            return SpeechDuckToken(True, state, volume, "paused_for_killerkoala_speech")
        return SpeechDuckToken(False, state, volume, "music_not_playing")
    except Exception as exc:
        return SpeechDuckToken(False, "unavailable", None, str(exc)[:160])


def restore_after_speech(token: SpeechDuckToken) -> None:
    if not token.was_playing:
        return
    try:
        MopidyClient(timeout=1.5).play()
    except Exception:
        pass


def _menu_rows() -> list[dict[str, object]]:
    from .menu_catalog import _item

    rows = [
        _item(GROUP_NAME, "Player Status", "music_status", "Show Mopidy playback, volume, and current track"),
        _item(GROUP_NAME, "Now Playing", "music_now_playing", "Show current track and stream title"),
        _item(GROUP_NAME, "Play / Resume", "music_play", "Play or resume the current Mopidy track"),
        _item(GROUP_NAME, "Pause", "music_pause", "Pause music playback"),
        _item(GROUP_NAME, "Play / Pause Toggle", "music_toggle", "Toggle playback state"),
        _item(GROUP_NAME, "Next Track", "music_next", "Move to the next track"),
        _item(GROUP_NAME, "Previous Track", "music_previous", "Move to the previous track"),
        _item(GROUP_NAME, "Stop Music", "music_stop", "Stop Mopidy playback"),
        _item(GROUP_NAME, "Volume +5", "music_volume_up", "Raise Mopidy volume by five percent"),
        _item(GROUP_NAME, "Volume -5", "music_volume_down", "Lower Mopidy volume by five percent"),
        _item(GROUP_NAME, "Refresh Local Library", "music_refresh_library", "Refresh the Pi local music library"),
        _item(GROUP_NAME, "Music Configuration", "music_config_status", "Show Mopidy RPC and radio preset configuration"),
    ]
    for command, (name, _uri) in _preset_commands().items():
        rows.append(
            _item(GROUP_NAME, f"Radio: {name}", command, f"Play configured internet radio preset {name}")
        )
    rows.append(_item("System / Companion", "Back to Main Canopy", "submenu:main", "Return to the main menu"))
    return rows


def install_menu_catalog() -> None:
    from . import menu_catalog
    from .menu_catalog import _item

    if GROUP_NAME not in menu_catalog.MENU_GROUPS:
        insert_at = (
            menu_catalog.MENU_GROUPS.index("System / Companion")
            if "System / Companion" in menu_catalog.MENU_GROUPS
            else len(menu_catalog.MENU_GROUPS)
        )
        menu_catalog.MENU_GROUPS.insert(insert_at, GROUP_NAME)
        menu_catalog._GROUP_ORDER = {
            name: index for index, name in enumerate(menu_catalog.MENU_GROUPS)
        }

    if not any(
        str(entry.get("command", "")) == f"submenu:{SUBMENU_NAME}"
        for entry in menu_catalog.MAIN_MENU_ITEMS
    ):
        row = _item(
            GROUP_NAME,
            "Music Player",
            f"submenu:{SUBMENU_NAME}",
            "Open the Pi-owned Mopidy music player",
        )
        insert_at = next(
            (
                index
                for index, entry in enumerate(menu_catalog.MAIN_MENU_ITEMS)
                if str(entry.get("command", "")) == "submenu:system"
            ),
            len(menu_catalog.MAIN_MENU_ITEMS),
        )
        menu_catalog.MAIN_MENU_ITEMS.insert(insert_at, row)

    menu_catalog.SUBMENU_ITEMS[SUBMENU_NAME] = _menu_rows()

    if not getattr(menu_catalog, "_mopidy_title_patch", False):
        original_title = menu_catalog.submenu_title

        def patched_title(menu_name: str) -> str:
            if menu_name == SUBMENU_NAME:
                return GROUP_NAME
            return original_title(menu_name)

        menu_catalog.submenu_title = patched_title
        menu_catalog._mopidy_title_patch = True

    _install_refresh_patch()
    _install_action_runner_patch()


def _install_refresh_patch() -> None:
    from . import menu_catalog

    if getattr(menu_catalog, "_mopidy_refresh_patch", False):
        return
    original_entries = menu_catalog._entries_for_menu

    def patched_entries(menu_name: str = "main"):
        if menu_name == SUBMENU_NAME:
            menu_catalog.SUBMENU_ITEMS[SUBMENU_NAME] = _menu_rows()
        return original_entries(menu_name)

    menu_catalog._entries_for_menu = patched_entries
    menu_catalog._mopidy_refresh_patch = True


def _install_action_runner_patch() -> None:
    try:
        from . import menu_action_runner
    except Exception:
        return
    if getattr(menu_action_runner, "_mopidy_action_patch", False):
        return
    original_runner = menu_action_runner.run_automated_menu_action

    def patched_runner(command: str, label: str = "", group: str = "") -> dict[str, Any]:
        if _is_music_command(command):
            result = run_music_command(command)
            result.setdefault("label", label)
            result.setdefault("group", group or GROUP_NAME)
            result.setdefault("selected_from_menu", True)
            result.setdefault("voice_command_compatible", True)
            return result
        return original_runner(command, label, group)

    menu_action_runner.run_automated_menu_action = patched_runner
    menu_action_runner._mopidy_action_patch = True
