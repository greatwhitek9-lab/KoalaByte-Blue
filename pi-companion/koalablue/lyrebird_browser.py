from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PLAYER_NAME = "Lyrebird"
ROOT_MENU = "music_player"
SONGS_MENU = "lyrebird_uploaded_songs"
RADIO_MENU = "lyrebird_radio_stations"
MUSIC_DIR_ENV = "KOALABYTE_MUSIC_DIR"
DEFAULT_MUSIC_DIR = Path("/srv/koalabyte-music")
DOUBLE_BACK_SECONDS = float(os.getenv("KOALABYTE_LYREBIRD_DOUBLE_BACK_SECONDS", "0.75"))
SUPPORTED_AUDIO_SUFFIXES = {
    ".aac",
    ".aiff",
    ".alac",
    ".flac",
    ".m4a",
    ".mp3",
    ".oga",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",
}

_INSTALLED = False
_SONG_COMMANDS: dict[str, "MediaChoice"] = {}
_RADIO_COMMANDS: dict[str, "MediaChoice"] = {}


@dataclass(frozen=True)
class MediaChoice:
    command: str
    label: str
    uri: str
    kind: str
    relative_path: str = ""


def music_directory() -> Path:
    configured = os.getenv(MUSIC_DIR_ENV, "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_MUSIC_DIR


def _slug(value: str, limit: int = 44) -> str:
    cleaned = "_".join(
        part
        for part in "".join(ch.lower() if ch.isalnum() else " " for ch in value).split()
        if part
    )
    return cleaned[:limit] or "item"


def _song_label(relative: Path) -> str:
    without_suffix = relative.with_suffix("")
    return " / ".join(without_suffix.parts)[:72] or relative.name[:72]


def uploaded_songs() -> list[MediaChoice]:
    root = music_directory()
    if not root.exists() or not root.is_dir():
        _SONG_COMMANDS.clear()
        return []

    choices: list[MediaChoice] = []
    for path in root.rglob("*"):
        try:
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES:
                continue
            relative = path.relative_to(root)
        except (OSError, ValueError):
            continue
        if any(part.startswith(".") for part in relative.parts):
            continue
        relative_text = relative.as_posix()
        digest = hashlib.sha1(relative_text.encode("utf-8")).hexdigest()[:12]
        command = f"music_song:{digest}"
        try:
            uri = path.resolve().as_uri()
        except ValueError:
            continue
        choices.append(
            MediaChoice(
                command=command,
                label=_song_label(relative),
                uri=uri,
                kind="song",
                relative_path=relative_text,
            )
        )

    choices.sort(key=lambda item: (item.label.casefold(), item.relative_path.casefold()))
    _SONG_COMMANDS.clear()
    _SONG_COMMANDS.update({choice.command: choice for choice in choices})
    return choices


def radio_stations() -> list[MediaChoice]:
    from . import mopidy_player

    choices: list[MediaChoice] = []
    for name, uri in mopidy_player.radio_presets().items():
        command = f"music_preset:{mopidy_player._safe_preset_key(name)}"
        choices.append(
            MediaChoice(
                command=command,
                label=name[:72],
                uri=uri,
                kind="radio",
            )
        )
    _RADIO_COMMANDS.clear()
    _RADIO_COMMANDS.update({choice.command: choice for choice in choices})
    return choices


def _choice_for_command(command: str) -> MediaChoice | None:
    if command.startswith("music_song:"):
        uploaded_songs()
        return _SONG_COMMANDS.get(command)
    if command.startswith("music_preset:"):
        radio_stations()
        return _RADIO_COMMANDS.get(command)
    return None


def _read_status() -> dict[str, Any]:
    from . import mopidy_player

    try:
        payload = json.loads(mopidy_player.STATUS_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _track_payload(status: dict[str, Any]) -> dict[str, Any]:
    track = status.get("track")
    return track if isinstance(track, dict) else {}


def _now_playing_label(status: dict[str, Any] | None = None) -> str:
    payload = status or _read_status()
    track = _track_payload(payload)
    label = str(
        payload.get("selected_song")
        or payload.get("preset")
        or track.get("stream_title")
        or track.get("name")
        or ""
    ).strip()
    if not label:
        uri = str(track.get("uri") or payload.get("selected_uri") or "").strip()
        if uri:
            try:
                label = Path(uri.split("?", 1)[0]).stem
            except Exception:
                label = uri
    state = str(payload.get("playback_state") or "").strip().lower()
    if not label:
        return "Lyrebird ready"
    if state == "paused":
        return f"Paused: {label}"[:72]
    if state == "playing":
        return f"Playing: {label}"[:72]
    return label[:72]


def _playback_state(status: dict[str, Any] | None = None) -> str:
    return str((status or _read_status()).get("playback_state") or "unknown").lower()


def _has_music_session(status: dict[str, Any] | None = None) -> bool:
    payload = status or _read_status()
    track = _track_payload(payload)
    return bool(
        str(track.get("uri") or payload.get("selected_uri") or "").strip()
        or _playback_state(payload) in {"playing", "paused"}
    )


def _queue_and_play(client: Any, choices: list[MediaChoice], selected: MediaChoice) -> dict[str, Any]:
    if not choices:
        raise RuntimeError("Lyrebird has no media choices to queue")
    uris = [choice.uri for choice in choices]
    client.rpc("core.tracklist.clear")
    added = client.rpc("core.tracklist.add", {"uris": uris})
    if not isinstance(added, list) or not added:
        raise RuntimeError("Mopidy did not add the Lyrebird media queue")

    selected_index = next(
        (index for index, choice in enumerate(choices) if choice.command == selected.command),
        0,
    )
    selected_index = min(selected_index, len(added) - 1)
    selected_row = added[selected_index] if isinstance(added[selected_index], dict) else {}
    tlid = selected_row.get("tlid")
    if tlid is None:
        client.rpc("core.playback.play")
    else:
        client.rpc("core.playback.play", {"tlid": tlid})
    return {
        "uri": selected.uri,
        "tlid": tlid,
        "queue_length": len(uris),
        "queue_index": selected_index,
    }


def _restart_current(client: Any) -> dict[str, Any]:
    state = client.playback_state()
    try:
        result = client.rpc("core.playback.seek", {"time_position": 0})
        if result is False:
            raise RuntimeError("Mopidy mixer rejected seek")
        return {"restart_method": "seek", "previous_state": state}
    except Exception:
        current = client.rpc("core.playback.get_current_tl_track")
        if isinstance(current, dict) and current.get("tlid") is not None:
            client.rpc("core.playback.play", {"tlid": current["tlid"]})
            return {"restart_method": "replay_tlid", "previous_state": state}
        track = client.current_track() or {}
        uri = str(track.get("uri") or "").strip() if isinstance(track, dict) else ""
        if uri:
            client.play_uri(uri)
            return {"restart_method": "reload_uri", "previous_state": state}
        client.play()
        return {"restart_method": "play", "previous_state": state}


def _install_music_command_extension() -> None:
    from . import mopidy_player

    if getattr(mopidy_player, "_lyrebird_browser_command_patch", False):
        return

    original_is_music_command = mopidy_player._is_music_command
    original_run_music_command = mopidy_player.run_music_command

    def is_music_command(command: str) -> bool:
        return (
            original_is_music_command(command)
            or command == "music_restart"
            or command.startswith("music_song:")
        )

    def run_music_command(command: str) -> dict[str, Any]:
        choice = _choice_for_command(command)
        if choice is None and command != "music_restart":
            return original_run_music_command(command)

        client = mopidy_player.MopidyClient()
        try:
            if command == "music_restart":
                result = {
                    "status": "MUSIC_RESTARTED",
                    **_restart_current(client),
                    **client.status(),
                }
            elif choice is not None and choice.kind == "song":
                queue = uploaded_songs()
                result = {
                    "status": "MUSIC_SONG_PLAYING",
                    "selected_song": choice.label,
                    "selected_uri": choice.uri,
                    "media_kind": "uploaded_song",
                    **_queue_and_play(client, queue, choice),
                    **client.status(),
                }
            elif choice is not None:
                queue = radio_stations()
                result = {
                    "status": "MUSIC_PRESET_PLAYING",
                    "preset": choice.label,
                    "selected_uri": choice.uri,
                    "media_kind": "internet_radio",
                    **_queue_and_play(client, queue, choice),
                    **client.status(),
                }
            else:
                raise RuntimeError(f"unknown Lyrebird command: {command}")

            result.setdefault("command", command)
            result.setdefault("manual_prompt_required", False)
            result.setdefault("execution_owner", "raspberry-pi")
            result.setdefault("selected_from_menu", True)
            result.setdefault("voice_command_compatible", True)
            return mopidy_player._write_status(result)
        except Exception as exc:
            return mopidy_player._write_status(
                {
                    "status": "MUSIC_PLAYER_ERROR",
                    "command": command,
                    "error": str(exc),
                    "execution_owner": "raspberry-pi",
                    "manual_prompt_required": False,
                    "selected_from_menu": True,
                    "voice_command_compatible": True,
                }
            )

    mopidy_player.MUSIC_COMMANDS.add("music_restart")
    mopidy_player._is_music_command = is_music_command
    mopidy_player.run_music_command = run_music_command
    mopidy_player._lyrebird_browser_command_patch = True


def _root_rows() -> list[dict[str, object]]:
    from . import mopidy_player
    from .menu_catalog import _item

    # Keep the stable controls, but move dynamic media into dedicated scrollable lists.
    raw_rows = mopidy_player._menu_rows()
    back_rows = [
        row for row in raw_rows
        if str(row.get("command", "")).startswith("submenu:main")
    ]
    controls = [
        row for row in raw_rows
        if not str(row.get("command", "")).startswith("music_preset:")
        and not str(row.get("command", "")).startswith("submenu:main")
    ]
    insert_at = min(2, len(controls))
    controls[insert_at:insert_at] = [
        _item(
            PLAYER_NAME,
            "Uploaded Songs",
            f"submenu:{SONGS_MENU}",
            f"Browse and play audio files stored in {music_directory()}",
        ),
        _item(
            PLAYER_NAME,
            "Radio Stations",
            f"submenu:{RADIO_MENU}",
            "Browse and play configured internet-radio presets",
        ),
    ]
    return controls + (
        back_rows
        or [_item("System / Companion", "Back to Main Canopy", "submenu:main", "Return to the main menu")]
    )


def _songs_rows() -> list[dict[str, object]]:
    from .menu_catalog import _item

    choices = uploaded_songs()
    rows: list[dict[str, object]] = [
        _item(
            PLAYER_NAME,
            "Refresh Uploaded Songs",
            "music_refresh_library",
            f"Rescan Mopidy and refresh {music_directory()}",
        )
    ]
    if choices:
        rows.extend(
            _item(
                PLAYER_NAME,
                choice.label,
                choice.command,
                f"Play {choice.relative_path} from {music_directory()}",
            )
            for choice in choices
        )
    else:
        rows.append(
            _item(
                PLAYER_NAME,
                "No Uploaded Songs Found",
                "music_no_uploaded_songs",
                f"Copy MP3, FLAC, Ogg, AAC, M4A, Opus, WMA, AIFF, or WAV files into {music_directory()}",
                enabled=False,
            )
        )
    rows.append(
        _item(
            "System / Companion",
            "Back to Lyrebird",
            f"submenu:{ROOT_MENU}",
            "Return to Lyrebird controls",
        )
    )
    return rows


def _radio_rows() -> list[dict[str, object]]:
    from .menu_catalog import _item

    choices = radio_stations()
    rows: list[dict[str, object]] = []
    if choices:
        rows.extend(
            _item(
                PLAYER_NAME,
                choice.label,
                choice.command,
                f"Play internet radio station {choice.label}",
            )
            for choice in choices
        )
    else:
        rows.append(
            _item(
                PLAYER_NAME,
                "No Radio Stations Configured",
                "music_no_radio_stations",
                "Add direct stream URLs under radio_presets in /etc/koalabyte-blue/music.json",
                enabled=False,
            )
        )
    rows.append(
        _item(
            "System / Companion",
            "Back to Lyrebird",
            f"submenu:{ROOT_MENU}",
            "Return to Lyrebird controls",
        )
    )
    return rows


def _install_menu_catalog_extension() -> None:
    from . import menu_catalog

    if getattr(menu_catalog, "_lyrebird_browser_catalog_patch", False):
        return

    # Keep compatibility snapshots populated while returning live lists to the UI.
    menu_catalog.SUBMENU_ITEMS.setdefault(SONGS_MENU, [])
    menu_catalog.SUBMENU_ITEMS.setdefault(RADIO_MENU, [])

    original_entries = menu_catalog._entries_for_menu
    original_title = menu_catalog.submenu_title

    def entries_for_menu(menu_name: str = "main") -> list[dict[str, object]]:
        if menu_name == ROOT_MENU:
            return _root_rows()
        if menu_name == SONGS_MENU:
            return _songs_rows()
        if menu_name == RADIO_MENU:
            return _radio_rows()
        return original_entries(menu_name)

    def submenu_title(menu_name: str) -> str:
        if menu_name == ROOT_MENU:
            return PLAYER_NAME
        if menu_name == SONGS_MENU:
            return "Uploaded Songs"
        if menu_name == RADIO_MENU:
            return "Radio Stations"
        return original_title(menu_name)

    menu_catalog._entries_for_menu = entries_for_menu
    menu_catalog.submenu_title = submenu_title
    menu_catalog._lyrebird_browser_catalog_patch = True

    # menu_ui imports submenu_title by name. Patch that binding if the module is loaded.
    try:
        from . import menu_ui

        menu_ui.submenu_title = submenu_title
    except Exception:
        pass


def _music_menu(menu: Any) -> bool:
    return str(getattr(menu, "menu_name", "")) in {ROOT_MENU, SONGS_MENU, RADIO_MENU}


def _media_command(command: str) -> bool:
    return command.startswith("music_song:") or command.startswith("music_preset:")


def _same_as_active(command: str, status: dict[str, Any]) -> bool:
    choice = _choice_for_command(command)
    if choice is None:
        return False
    track = _track_payload(status)
    current_uri = str(track.get("uri") or status.get("selected_uri") or "").strip()
    return bool(current_uri and current_uri == choice.uri)


def _run_control(menu: Any, command: str, item: Any, event_type: str) -> Any:
    from . import menu_action_runner

    result = menu_action_runner.run_automated_menu_action(
        command,
        label=str(getattr(item, "label", command)),
        group=str(getattr(item, "group", PLAYER_NAME)) or PLAYER_NAME,
    )
    menu.display_mode = "menu"
    menu.face_state = "music_playback"
    menu.face_message = _now_playing_label(result if isinstance(result, dict) else None)
    menu.last_input_at = time.time()
    event = menu._make_event(event_type, command)
    menu._log_event(event)
    return event


def _install_menu_control_extension() -> None:
    from . import menu_ui

    cls = menu_ui.MenuSelectionScreen
    if getattr(cls, "_lyrebird_browser_controls_patch", False):
        return

    original_handle_command = cls.handle_command
    original_select = cls.select

    def select(menu: Any, select_event_type: str = "select") -> Any:
        if getattr(menu, "display_mode", "") == "menu" and _music_menu(menu):
            item = menu.selected_item
            command = str(item.command)
            if command.startswith("submenu:") or not bool(getattr(item, "enabled", True)):
                return original_select(menu, select_event_type)
            if command.startswith("music_no_"):
                return original_select(menu, select_event_type)

            status = _read_status()
            resolved = "music_toggle" if _media_command(command) and _same_as_active(command, status) else command
            return _run_control(menu, resolved, item, "music_select")
        return original_select(menu, select_event_type)

    def handle_command(menu: Any, command: str) -> Any:
        normalized = command.strip().lower()
        status = _read_status()
        in_music_menu = _music_menu(menu)
        session = _has_music_session(status)

        if in_music_menu and session and normalized in {"move_right", "right", "forward"}:
            return _run_control(menu, "music_next", menu.selected_item, "music_next")

        if in_music_menu and session and normalized in {"move_left", "left", "back"}:
            now = time.monotonic()
            previous = float(getattr(menu, "_lyrebird_last_back_at", 0.0))
            if previous and now - previous <= DOUBLE_BACK_SECONDS:
                resolved = "music_previous"
                menu._lyrebird_last_back_at = 0.0
                event_type = "music_previous"
            else:
                resolved = "music_restart"
                menu._lyrebird_last_back_at = now
                event_type = "music_restart"
            return _run_control(menu, resolved, menu.selected_item, event_type)

        if (
            normalized in {"select", "enter"}
            and getattr(menu, "display_mode", "") != "menu"
            and getattr(menu, "face_state", "") == "music_playback"
            and session
        ):
            # Enter/K3 is Play/Pause when the Lyrebird playback face is active.
            return _run_control(menu, "music_toggle", menu.selected_item, "music_toggle")

        return original_handle_command(menu, command)

    cls.select = select
    cls.handle_command = handle_command
    cls._lyrebird_browser_controls_patch = True


def _install_display_extension() -> None:
    from . import menu_display_sync

    if getattr(menu_display_sync, "_lyrebird_browser_display_patch", False):
        return

    original_build_menu = menu_display_sync.build_menu_sync_payload
    original_heltec_face = menu_display_sync._heltec_face_payload

    def build_menu_sync_payload(menu: Any, event: Any | None = None) -> dict[str, object]:
        payload = original_build_menu(menu, event)
        if not _music_menu(menu):
            return payload

        status = _read_status()
        now_playing = _now_playing_label(status)
        state = _playback_state(status)
        has_session = _has_music_session(status)
        payload["lyrebird_mode"] = True
        payload["lyrebird_playback_state"] = state
        payload["lyrebird_now_playing"] = now_playing
        payload["lyrebird_media_directory"] = str(music_directory())
        payload["selected_group"] = PLAYER_NAME
        if has_session:
            # Existing ESP32 firmware renders selected_label on the left display,
            # while visible_items remain the scrollable list on the right display.
            payload["selected_label"] = now_playing
        payload["controls"] = {
            "scroll_up": ["K5", "touch_drag_up", "keyboard_up"],
            "scroll_down": ["K6", "touch_drag_down", "keyboard_down"],
            "select_or_play_pause": ["K3", "Enter", "touch_long_press"],
            "next_track": ["K4", "right", "forward"],
            "restart_track": ["K2", "left", "back"],
            "previous_track": ["K2_double_press"],
            "main_menu": ["K1", "touch_double_tap"],
            "power_on_off": ["K7"],
            "reset_reboot": ["K8"],
        }
        payload["execute_hint"] = (
            "K5/K6 scroll | K3/Enter selects; on the active item K3/Enter toggles play/pause | "
            "K4 next | K2 restart | double K2 previous"
        )
        return payload

    def heltec_face_payload(payload: dict[str, object]) -> dict[str, object]:
        if payload.get("lyrebird_mode"):
            state = str(payload.get("lyrebird_playback_state", "unknown")).lower()
            now_playing = str(payload.get("lyrebird_now_playing", "Lyrebird"))[:72]
            if state == "playing":
                # The existing persistent Koalagotchi action renderer cycles frames
                # continuously; the DANCE label makes this the Lyrebird dance emote.
                return {
                    "type": "killerkoala_face",
                    "state": "koalagotchi_persistent",
                    "message": f"DANCE • {now_playing}"[:92],
                    "menu_sync": False,
                    "duration_ms": 60000,
                    "enabled": True,
                    "lyrebird_dance": True,
                }
            if state in {"paused", "stopped"} and now_playing != "Lyrebird ready":
                return {
                    "type": "killerkoala_face",
                    "state": "koalagotchi_exit",
                    "message": f"LYREBIRD {state.upper()}"[:92],
                    "menu_sync": False,
                    "duration_ms": 1500,
                    "enabled": True,
                    "lyrebird_dance": False,
                }
        return original_heltec_face(payload)

    menu_display_sync.build_menu_sync_payload = build_menu_sync_payload
    menu_display_sync._heltec_face_payload = heltec_face_payload
    menu_display_sync._lyrebird_browser_display_patch = True


def install_lyrebird_browser() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _install_music_command_extension()
    _install_menu_catalog_extension()
    _install_menu_control_extension()
    _install_display_extension()
    _INSTALLED = True
