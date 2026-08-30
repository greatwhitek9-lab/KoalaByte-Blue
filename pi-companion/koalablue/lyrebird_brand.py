from __future__ import annotations

from typing import Any

PLAYER_NAME = "Lyrebird"
SUBMENU_NAME = "music_player"
SUBMENU_COMMAND = f"submenu:{SUBMENU_NAME}"

_REQUIRED_COMMANDS = {
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

_COMMAND_LABELS = {
    "music_status": "Lyrebird Status",
    "music_now_playing": "Lyrebird Now Playing",
    "music_play": "Lyrebird Play",
    "music_pause": "Lyrebird Pause",
    "music_toggle": "Lyrebird Toggle",
    "music_next": "Lyrebird Next",
    "music_previous": "Lyrebird Previous",
    "music_stop": "Lyrebird Stop",
    "music_volume_up": "Lyrebird Volume Up",
    "music_volume_down": "Lyrebird Volume Down",
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
        row["label"] = f"Lyrebird Radio {preset}" if preset else "Lyrebird Radio"


def _ensure_catalog_structure(menu_catalog: Any, mopidy_player: Any) -> None:
    """Repair a partial Mopidy menu injection before the one-shot audits it."""
    if PLAYER_NAME not in menu_catalog.MENU_GROUPS:
        insert_at = (
            menu_catalog.MENU_GROUPS.index("System / Companion")
            if "System / Companion" in menu_catalog.MENU_GROUPS
            else len(menu_catalog.MENU_GROUPS)
        )
        menu_catalog.MENU_GROUPS.insert(insert_at, PLAYER_NAME)
    menu_catalog._GROUP_ORDER = {
        name: index for index, name in enumerate(menu_catalog.MENU_GROUPS)
    }

    if not any(
        str(row.get("command", "")) == SUBMENU_COMMAND
        for row in menu_catalog.MAIN_MENU_ITEMS
    ):
        row = menu_catalog._item(
            PLAYER_NAME,
            PLAYER_NAME,
            SUBMENU_COMMAND,
            "Open Lyrebird, the Pi-owned Mopidy music player",
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

    # A previous import could have inserted the main link before failing while
    # generating the submenu. Rebuild the submenu from the stable Mopidy command
    # catalog so no dangling submenu link can survive into one-shot validation.
    if not menu_catalog.SUBMENU_ITEMS.get(SUBMENU_NAME):
        menu_catalog.SUBMENU_ITEMS[SUBMENU_NAME] = mopidy_player._menu_rows()


def _install_title_patch(menu_catalog: Any) -> None:
    if getattr(menu_catalog, "_lyrebird_submenu_title_patch", False):
        return
    original_title = menu_catalog.submenu_title

    def lyrebird_title(menu_name: str) -> str:
        if menu_name == SUBMENU_NAME:
            return PLAYER_NAME
        return original_title(menu_name)

    menu_catalog.submenu_title = lyrebird_title
    menu_catalog._lyrebird_submenu_title_patch = True


def install_lyrebird_brand() -> None:
    """Install a complete, jungle-rendered Lyrebird menu over stable Mopidy internals."""
    from . import menu_catalog, mopidy_player

    mopidy_player.GROUP_NAME = PLAYER_NAME
    _ensure_catalog_structure(menu_catalog, mopidy_player)

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

    # Refresh from the canonical generator on every install. This repairs stale or
    # partially generated rows and also picks up current configured radio presets.
    menu_catalog.SUBMENU_ITEMS[SUBMENU_NAME] = mopidy_player._menu_rows()
    for row in menu_catalog.SUBMENU_ITEMS[SUBMENU_NAME]:
        _brand_row(row)

    _install_title_patch(menu_catalog)

    # Keep the menu leaf dispatcher synchronized with the repaired catalog. This
    # does not contact Mopidy; it only installs the command routing wrapper.
    install_runner_patch = getattr(mopidy_player, "_install_action_runner_patch", None)
    if callable(install_runner_patch):
        install_runner_patch()

    main_links = [
        row
        for row in menu_catalog.MAIN_MENU_ITEMS
        if str(row.get("command", "")) == SUBMENU_COMMAND
    ]
    if len(main_links) != 1:
        raise RuntimeError(f"Lyrebird requires exactly one main-menu link, found {len(main_links)}")
    if str(main_links[0].get("label", "")) != PLAYER_NAME:
        raise RuntimeError("Lyrebird main-menu label drifted from the product name")

    commands = {
        str(row.get("command", ""))
        for row in menu_catalog.SUBMENU_ITEMS.get(SUBMENU_NAME, [])
    }
    missing = sorted(_REQUIRED_COMMANDS - commands)
    if missing:
        raise RuntimeError(f"Lyrebird submenu is incomplete; missing commands: {missing}")
