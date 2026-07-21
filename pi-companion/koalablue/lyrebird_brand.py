from __future__ import annotations

from typing import Any

PLAYER_NAME = "Lyrebird"
SUBMENU_NAME = "music_player"
SUBMENU_COMMAND = f"submenu:{SUBMENU_NAME}"

_COMMAND_LABELS = {
    "music_status": "Lyrebird Status",
    "music_now_playing": "Lyrebird Now Playing",
    "music_play": "Lyrebird Play / Resume",
    "music_pause": "Lyrebird Pause",
    "music_toggle": "Lyrebird Play / Pause",
    "music_next": "Lyrebird Next Track",
    "music_previous": "Lyrebird Previous Track",
    "music_stop": "Lyrebird Stop",
    "music_volume_up": "Lyrebird Volume +5",
    "music_volume_down": "Lyrebird Volume -5",
    "music_refresh_library": "Lyrebird Refresh Library",
    "music_config_status": "Lyrebird Configuration",
}


def _brand_row(row: dict[str, Any]) -> None:
    command = str(row.get("command", ""))
    if command == SUBMENU_COMMAND:
        row["group"] = PLAYER_NAME
        row["label"] = PLAYER_NAME
        row["description"] = "Open Lyrebird, the Pi-owned Mopidy music player"
        return
    if command in _COMMAND_LABELS:
        row["group"] = PLAYER_NAME
        row["label"] = _COMMAND_LABELS[command]
        return
    if command.startswith("music_preset:"):
        row["group"] = PLAYER_NAME
        label = str(row.get("label", ""))
        preset = label.split(":", 1)[-1].strip() if ":" in label else label
        row["label"] = f"Lyrebird Radio: {preset}" if preset else "Lyrebird Radio"


def install_lyrebird_brand() -> None:
    """Apply the Lyrebird product name without changing stable Mopidy internals."""
    from . import menu_catalog, mopidy_player

    mopidy_player.GROUP_NAME = PLAYER_NAME

    for row in menu_catalog.MAIN_MENU_ITEMS:
        _brand_row(row)
    for row in menu_catalog.SUBMENU_ITEMS.get(SUBMENU_NAME, []):
        _brand_row(row)

    # Dynamic radio presets are regenerated whenever the submenu is opened. Wrap
    # that generator so newly added presets receive the Lyrebird name as well.
    if not getattr(mopidy_player, "_lyrebird_rows_patch", False):
        original_rows = mopidy_player._menu_rows

        def branded_rows() -> list[dict[str, object]]:
            rows = original_rows()
            for row in rows:
                _brand_row(row)
            return rows

        mopidy_player._menu_rows = branded_rows
        mopidy_player._lyrebird_rows_patch = True
        menu_catalog.SUBMENU_ITEMS[SUBMENU_NAME] = branded_rows()
