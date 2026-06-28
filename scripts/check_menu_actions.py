#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue.menu_catalog import MAIN_MENU_ITEMS, SUBMENU_ITEMS, all_menu_entries, leaf_menu_entries, submenu_name_from_command  # noqa: E402
from koalablue.menu_theme import DEFAULT_JUNGLE_MENU_THEME, GRAPHICAL_DESCRIPTION_MAX_LINES, GRAPHICAL_LABEL_MAX_LINES, render_terminal_jungle_menu  # noqa: E402
from scripts.run_menu_screen import make_menu, open_submenu  # noqa: E402

OUTPUT_DIR = ROOT / "logs" / "menu_actions"
MANIFEST_PATH = OUTPUT_DIR / "menu_action_manifest.json"
STATUS_PATH = OUTPUT_DIR / "menu_action_status.json"
TERMINAL_FRAME_WIDTH = 74

ALLOWED_DUPLICATE_COMMANDS = {
    "koala_bluez_info",
    "koala_bluez_services",
    "koala_bluez_gatt_readiness",
    "bluez_outback_radio_ledger",
    "bluez_classic_track_finder",
    "bluez_treehouse_rfcomm_wiremap",
    "bluez_pouch_link_echo",
    "bluez_gumnut_gatt_ghostmap",
    "bluez_platypus_bt_proxy",
    "location_gate_status",
    "keyboard:bluez_lab_target",
    "bluez_lab_scope_status",
    "bluez_lab_owned_on",
    "bluez_lab_owned_off",
    "bluez_lab_scope_clear",
}


def _command(entry: dict[str, Any]) -> str:
    return str(entry.get("command", "")).strip()


def _label(entry: dict[str, Any]) -> str:
    return str(entry.get("label", "")).strip()


def _enabled(entry: dict[str, Any]) -> bool:
    return bool(entry.get("enabled", True))


def _menu_names() -> set[str]:
    return {"main", *SUBMENU_ITEMS.keys()}


def _walk_menu_entries() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in MAIN_MENU_ITEMS:
        rows.append({"menu": "main", **entry})
    for menu_name, entries in SUBMENU_ITEMS.items():
        for entry in entries:
            rows.append({"menu": menu_name, **entry})
    return rows


def _visible_duplicate_commands() -> dict[str, list[str]]:
    seen: dict[str, list[str]] = {}
    for entry in _walk_menu_entries():
        if not _enabled(entry):
            continue
        command = _command(entry)
        if not command or command.startswith("submenu:") or command == "quit":
            continue
        seen.setdefault(command, []).append(_label(entry))
    return {command: labels for command, labels in seen.items() if len(set(labels)) > 1}


def _check_terminal_theme_fit(menu_names: set[str]) -> list[str]:
    failures: list[str] = []
    for menu_name in sorted(menu_names):
        menu = make_menu()
        if menu_name != "main":
            open_submenu(menu, f"submenu:{menu_name}")
        text = render_terminal_jungle_menu(menu)
        for line_no, line in enumerate(text.splitlines(), start=1):
            if len(line) > TERMINAL_FRAME_WIDTH:
                failures.append(f"{menu_name} terminal theme line {line_no} exceeds {TERMINAL_FRAME_WIDTH} chars")
    return failures


def build_manifest() -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    menu_names = _menu_names()
    menu = make_menu()
    handlers = getattr(menu, "_handlers", {})
    rows = []

    for entry in _walk_menu_entries():
        command = _command(entry)
        label = _label(entry)
        enabled = _enabled(entry)
        submenu = submenu_name_from_command(command)
        is_submenu = bool(submenu)
        is_status_row = command.startswith("status:")
        handler_name = ""
        routed = False
        automated = False

        if is_submenu:
            routed = submenu in menu_names
            automated = routed
            if enabled and not routed:
                failures.append(f"submenu item '{label}' points to missing submenu: {command}")
        elif enabled:
            handler = handlers.get(command)
            routed = handler is not None
            automated = routed
            handler_name = getattr(handler, "__name__", "") if handler is not None else ""
            if not routed:
                failures.append(f"enabled menu item '{label}' has no automated select handler: {command}")
        else:
            routed = True
            automated = True

        rows.append(
            {
                "menu": entry.get("menu", "main"),
                "group": entry.get("group", ""),
                "label": label,
                "command": command,
                "enabled": enabled,
                "submenu": submenu,
                "is_submenu": is_submenu,
                "is_status_row": is_status_row,
                "routed": routed,
                "automated_select": automated,
                "handler": handler_name,
                "description": entry.get("description", ""),
            }
        )

    theme = DEFAULT_JUNGLE_MENU_THEME
    if "jungle" not in theme.border_style or "eucalyptus" not in theme.border_style:
        failures.append("menu theme no longer carries the jungle/eucalyptus border identity")
    if theme.font_family != theme.item_font_family:
        failures.append("menu title/item font stacks diverged")
    if GRAPHICAL_LABEL_MAX_LINES != 1:
        failures.append("graphical labels must be constrained to one line")
    if GRAPHICAL_DESCRIPTION_MAX_LINES > 2:
        failures.append("graphical descriptions must stay within two lines")
    failures.extend(_check_terminal_theme_fit(menu_names))

    duplicate_commands = _visible_duplicate_commands()
    unexpected_duplicates = sorted(set(duplicate_commands) - ALLOWED_DUPLICATE_COMMANDS)
    for command in unexpected_duplicates:
        failures.append(f"unexpected duplicate visible command '{command}': {duplicate_commands[command]}")

    leaf_commands = sorted({_command(entry) for entry in leaf_menu_entries()})
    status_rows = sorted({_command(entry) for entry in leaf_menu_entries() if _command(entry).startswith("status:")})
    handler_commands = sorted(str(command) for command in handlers.keys())
    manifest = {
        "status": "MENU_ACTIONS_READY" if not failures else "MENU_ACTIONS_INCOMPLETE",
        "updated_at": time.time(),
        "menu_count": len(menu_names),
        "menu_names": sorted(menu_names),
        "total_entries": len(rows),
        "catalog_entry_count": len(all_menu_entries()),
        "enabled_leaf_count": len(leaf_commands),
        "status_row_count": len(status_rows),
        "handler_count": len(handler_commands),
        "leaf_commands": leaf_commands,
        "handler_commands": handler_commands,
        "rows": rows,
        "theme": {
            "title": theme.title,
            "font_family": theme.font_family,
            "item_font_family": theme.item_font_family,
            "border_style": theme.border_style,
            "graphical_label_max_lines": GRAPHICAL_LABEL_MAX_LINES,
            "graphical_description_max_lines": GRAPHICAL_DESCRIPTION_MAX_LINES,
            "terminal_frame_width": TERMINAL_FRAME_WIDTH,
        },
        "visible_duplicate_commands": duplicate_commands,
        "allowed_duplicate_commands": sorted(ALLOWED_DUPLICATE_COMMANDS),
        "failures": failures,
    }
    return manifest, failures


def main() -> int:
    manifest, failures = build_manifest()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    STATUS_PATH.write_text(json.dumps({"status": manifest["status"], "manifest_path": str(MANIFEST_PATH), "failures": failures, "updated_at": manifest["updated_at"]}, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "manifest_path": str(MANIFEST_PATH), "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
