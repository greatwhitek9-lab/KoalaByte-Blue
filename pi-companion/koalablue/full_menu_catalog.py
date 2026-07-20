from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List, Type, TypeVar

from . import menu_catalog as base

T = TypeVar("T")

MENU_GROUPS = base.MENU_GROUPS
_GROUP_ORDER = {name: index for index, name in enumerate(MENU_GROUPS)}


def _item(
    group: str,
    label: str,
    command: str,
    description: str = "",
    enabled: bool = True,
) -> dict[str, object]:
    row: dict[str, object] = {
        "group": group,
        "label": label,
        "command": command,
        "description": description,
    }
    if enabled is not True:
        row["enabled"] = enabled
    return row


MUSIC_MENU_ITEMS: List[dict[str, object]] = [
    _item("System / Companion", "Now Playing", "music_status", "Show Mopidy playback, track, source, and volume"),
    _item("System / Companion", "Play / Resume Music", "music_play", "Resume the current Mopidy track or queue"),
    _item("System / Companion", "Pause Music", "music_pause", "Pause playback without clearing the queue"),
    _item("System / Companion", "Next Track", "music_next", "Advance to the next queued track"),
    _item("System / Companion", "Previous Track", "music_previous", "Return to the previous queued track"),
    _item("System / Companion", "Music Volume Up", "music_volume_up", "Raise Mopidy software volume by five percent"),
    _item("System / Companion", "Music Volume Down", "music_volume_down", "Lower Mopidy software volume by five percent"),
    _item("System / Companion", "Stop Music", "music_stop", "Stop playback while preserving the configured library"),
    _item("System / Companion", "Refresh Music Library", "music_refresh", "Ask Mopidy backends to refresh their libraries"),
    _item("System / Companion", "Back to Main Canopy", "submenu:main", "Return to the main menu"),
]

MAIN_MENU_ITEMS: List[dict[str, object]] = list(base.MAIN_MENU_ITEMS)
_music_main = _item(
    "System / Companion",
    "Music Player",
    "submenu:music",
    "Open Pi-owned Mopidy local, radio, and optional streaming controls",
)
_insert_at = next(
    (
        index
        for index, row in enumerate(MAIN_MENU_ITEMS)
        if str(row.get("command", "")) == "submenu:system"
    ),
    len(MAIN_MENU_ITEMS),
)
MAIN_MENU_ITEMS.insert(_insert_at, _music_main)

SUBMENU_ITEMS: Dict[str, List[dict[str, object]]] = {
    name: list(rows) for name, rows in base.SUBMENU_ITEMS.items()
}
SUBMENU_ITEMS["music"] = MUSIC_MENU_ITEMS


def _entries_for_menu(menu_name: str = "main") -> List[dict[str, object]]:
    if menu_name == "main":
        return MAIN_MENU_ITEMS
    return SUBMENU_ITEMS.get(menu_name, [])


def submenu_name_from_command(command: str) -> str:
    return base.submenu_name_from_command(command)


def submenu_title(menu_name: str) -> str:
    if menu_name == "music":
        return "Music Player"
    return base.submenu_title(menu_name)


def _entry_group(entry: dict[str, object]) -> str:
    group = str(entry.get("group", "System / Companion"))
    return group if group in _GROUP_ORDER else "System / Companion"


def grouped_entries(menu_name: str = "main") -> Dict[str, List[dict[str, object]]]:
    groups: Dict[str, List[dict[str, object]]] = OrderedDict(
        (name, []) for name in MENU_GROUPS
    )
    for entry in _entries_for_menu(menu_name):
        groups[_entry_group(entry)].append(entry)
    return groups


def grouped_menu_labels(menu_name: str = "main") -> Dict[str, List[str]]:
    return {
        group: [str(entry.get("label", "")) for entry in entries]
        for group, entries in grouped_entries(menu_name).items()
    }


def sorted_menu_entries(menu_name: str = "main") -> List[dict[str, object]]:
    return list(_entries_for_menu(menu_name))


def all_menu_entries() -> List[dict[str, object]]:
    rows: List[dict[str, object]] = []
    rows.extend(_entries_for_menu("main"))
    for menu_name in list(SUBMENU_ITEMS.keys()):
        rows.extend(_entries_for_menu(menu_name))
    return rows


def leaf_menu_entries() -> List[dict[str, object]]:
    return [
        entry
        for entry in all_menu_entries()
        if not str(entry.get("command", "")).startswith("submenu:")
    ]


def make_menu_items(cls: Type[T], menu_name: str = "main") -> List[T]:
    return [
        cls(
            label=str(entry["label"]),
            command=str(entry["command"]),
            description=str(entry.get("description", "")),
            enabled=bool(entry.get("enabled", True)),
            group=str(entry.get("group", "System / Companion")),
        )
        for entry in sorted_menu_entries(menu_name)
    ]


def menu_labels(menu_name: str = "main") -> List[str]:
    return [str(entry["label"]) for entry in sorted_menu_entries(menu_name)]


def menu_commands(menu_name: str = "main") -> List[str]:
    return [str(entry["command"]) for entry in sorted_menu_entries(menu_name)]
