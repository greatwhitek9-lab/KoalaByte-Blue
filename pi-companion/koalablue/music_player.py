from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import httpx

DEFAULT_MOPIDY_RPC = "http://127.0.0.1:6680/mopidy/rpc"
DEFAULT_STATUS_PATH = Path("logs/music/music_status.json")
DEFAULT_SOURCES_PATH = Path("config/music_sources.json")
DEFAULT_TIMEOUT_SECONDS = 4.0


class MopidyUnavailable(RuntimeError):
    pass


@dataclass
class MusicStatus:
    status: str
    playback_state: str = "unknown"
    volume: int | None = None
    muted: bool | None = None
    track_name: str = ""
    artists: list[str] = field(default_factory=list)
    album: str = ""
    uri: str = ""
    time_position_ms: int | None = None
    queue_length: int | None = None
    source: str = "mopidy"
    rpc_url: str = DEFAULT_MOPIDY_RPC
    error: str = ""
    updated_at: float = 0.0

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


class MopidyClient:
    def __init__(
        self,
        rpc_url: str | None = None,
        *,
        timeout_seconds: float | None = None,
        status_path: str | Path = DEFAULT_STATUS_PATH,
    ) -> None:
        self.rpc_url = (
            rpc_url
            or os.getenv("KOALABYTE_MOPIDY_RPC", "").strip()
            or DEFAULT_MOPIDY_RPC
        )
        self.timeout_seconds = float(
            timeout_seconds
            if timeout_seconds is not None
            else os.getenv("KOALABYTE_MOPIDY_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
        )
        self.status_path = Path(status_path)
        self._request_id = 0

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        self._request_id += 1
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(self.rpc_url, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            raise MopidyUnavailable(f"Mopidy RPC unavailable at {self.rpc_url}: {exc}") from exc
        if not isinstance(data, dict):
            raise MopidyUnavailable("Mopidy returned a non-object JSON-RPC response")
        if data.get("error"):
            raise RuntimeError(f"Mopidy {method} failed: {data['error']}")
        return data.get("result")

    @staticmethod
    def _track_fields(track: Any) -> tuple[str, list[str], str, str]:
        if not isinstance(track, dict):
            return "", [], "", ""
        artists: list[str] = []
        for artist in track.get("artists") or []:
            if isinstance(artist, dict) and artist.get("name"):
                artists.append(str(artist["name"]))
        album = track.get("album") or {}
        album_name = str(album.get("name") or "") if isinstance(album, dict) else ""
        return (
            str(track.get("name") or ""),
            artists,
            album_name,
            str(track.get("uri") or ""),
        )

    def status(self) -> MusicStatus:
        try:
            playback_state = str(self.call("core.playback.get_state") or "unknown")
            volume = self.call("core.mixer.get_volume")
            muted = self.call("core.mixer.get_mute")
            track = self.call("core.playback.get_current_track")
            position = self.call("core.playback.get_time_position")
            queue_length = self.call("core.tracklist.get_length")
            track_name, artists, album, uri = self._track_fields(track)
            result = MusicStatus(
                status="MUSIC_READY",
                playback_state=playback_state,
                volume=int(volume) if volume is not None else None,
                muted=bool(muted) if muted is not None else None,
                track_name=track_name,
                artists=artists,
                album=album,
                uri=uri,
                time_position_ms=int(position) if position is not None else None,
                queue_length=int(queue_length) if queue_length is not None else None,
                rpc_url=self.rpc_url,
                updated_at=time.time(),
            )
        except Exception as exc:
            result = MusicStatus(
                status="MUSIC_UNAVAILABLE",
                error=str(exc),
                rpc_url=self.rpc_url,
                updated_at=time.time(),
            )
        self._write_status(result)
        return result

    def _write_status(self, status: MusicStatus) -> None:
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        self.status_path.write_text(
            json.dumps(status.to_payload(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def play(self) -> MusicStatus:
        state = str(self.call("core.playback.get_state") or "")
        if state == "paused":
            self.call("core.playback.resume")
        else:
            self.call("core.playback.play")
        return self.status()

    def pause(self) -> MusicStatus:
        self.call("core.playback.pause")
        return self.status()

    def stop(self) -> MusicStatus:
        self.call("core.playback.stop")
        return self.status()

    def next(self) -> MusicStatus:
        self.call("core.playback.next")
        return self.status()

    def previous(self) -> MusicStatus:
        self.call("core.playback.previous")
        return self.status()

    def set_volume(self, volume: int) -> MusicStatus:
        self.call("core.mixer.set_volume", {"volume": max(0, min(100, int(volume)))})
        return self.status()

    def adjust_volume(self, delta: int) -> MusicStatus:
        current = self.call("core.mixer.get_volume")
        value = int(current) if current is not None else 50
        return self.set_volume(value + int(delta))

    def refresh(self) -> MusicStatus:
        self.call("core.library.refresh")
        return self.status()

    def replace_queue_and_play(self, uri: str) -> MusicStatus:
        cleaned = str(uri or "").strip()
        if not cleaned:
            raise ValueError("music URI is empty")
        self.call("core.tracklist.clear")
        self.call("core.tracklist.add", {"uris": [cleaned]})
        self.call("core.playback.play")
        return self.status()


def load_sources(path: str | Path = DEFAULT_SOURCES_PATH) -> dict[str, Any]:
    source_path = Path(path)
    if not source_path.exists():
        return {"default": "", "favorites": []}
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid music sources file {source_path}: {exc}") from exc
    return payload if isinstance(payload, dict) else {"default": "", "favorites": []}


def default_stream_uri(path: str | Path = DEFAULT_SOURCES_PATH) -> str:
    env_uri = os.getenv("KOALABYTE_MUSIC_DEFAULT_URI", "").strip()
    if env_uri:
        return env_uri
    payload = load_sources(path)
    default = str(payload.get("default") or "").strip()
    if default:
        return default
    favorites = payload.get("favorites") or []
    for row in favorites:
        if isinstance(row, dict) and str(row.get("uri") or "").strip():
            return str(row["uri"]).strip()
    return ""


def run_music_action(command: str, client: MopidyClient | None = None) -> dict[str, Any]:
    player = client or MopidyClient()
    try:
        if command == "music_status":
            status = player.status()
        elif command == "music_play":
            status = player.play()
        elif command == "music_pause":
            status = player.pause()
        elif command == "music_stop":
            status = player.stop()
        elif command == "music_next":
            status = player.next()
        elif command == "music_previous":
            status = player.previous()
        elif command == "music_volume_up":
            status = player.adjust_volume(5)
        elif command == "music_volume_down":
            status = player.adjust_volume(-5)
        elif command == "music_refresh":
            status = player.refresh()
        elif command == "music_favorite":
            uri = default_stream_uri()
            if not uri:
                return {
                    "status": "MUSIC_SOURCE_NOT_CONFIGURED",
                    "command": command,
                    "sources_path": str(DEFAULT_SOURCES_PATH),
                    "hint": "Set KOALABYTE_MUSIC_DEFAULT_URI or add a default/favorite URI to config/music_sources.json.",
                    "updated_at": time.time(),
                }
            status = player.replace_queue_and_play(uri)
        else:
            return {
                "status": "MUSIC_COMMAND_UNKNOWN",
                "command": command,
                "updated_at": time.time(),
            }
        payload = status.to_payload()
        payload["command"] = command
        return payload
    except Exception as exc:
        unavailable = MusicStatus(
            status="MUSIC_ACTION_FAILED",
            error=str(exc),
            rpc_url=player.rpc_url,
            updated_at=time.time(),
        )
        player._write_status(unavailable)
        payload = unavailable.to_payload()
        payload["command"] = command
        return payload


def pause_for_speech(client: MopidyClient | None = None) -> dict[str, Any]:
    player = client or MopidyClient()
    current = player.status()
    was_playing = current.status == "MUSIC_READY" and current.playback_state == "playing"
    if was_playing:
        try:
            player.pause()
        except Exception:
            was_playing = False
    return {
        "was_playing": was_playing,
        "playback_state": current.playback_state,
        "track_name": current.track_name,
    }


def resume_after_speech(token: dict[str, Any], client: MopidyClient | None = None) -> None:
    if not bool(token.get("was_playing")):
        return
    try:
        (client or MopidyClient()).play()
    except Exception:
        pass
