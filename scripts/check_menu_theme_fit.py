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

from koalablue.menu_catalog import MAIN_MENU_ITEMS, SUBMENU_ITEMS, all_menu_entries, grouped_menu_labels, submenu_title  # noqa: E402
from koalablue.menu_theme import (  # noqa: E402
    DEFAULT_JUNGLE_MENU_THEME,
    GRAPHICAL_DESCRIPTION_MAX_LINES,
    GRAPHICAL_LABEL_MAX_LINES,
    TERMINAL_DESCRIPTION_WIDTH,
    TERMINAL_LABEL_WIDTH,
    render_terminal_jungle_menu,
)
from scripts.run_menu_screen import make_menu, open_submenu  # noqa: E402

OUTPUT_DIR = ROOT / "logs" / "menu_actions"
STATUS_PATH = OUTPUT_DIR / "menu_theme_fit_status.json"
TERMINAL_FRAME_WIDTH = 74
MAX_LABEL_CHARS = 42
MAX_DESCRIPTION_CHARS = 118


def _entry_command(entry: dict[str, Any]) -> str:
    return str(entry.get("command", "")).strip()


def _entry_label(entry: dict[str, Any]) -> str:
    return str(entry.get("label", "")).strip()


def _entry_description(entry: dict[str, Any]) -> str:
    return str(entry.get("description", "")).strip()


def _visible_duplicate_commands() -> dict[str, list[str]]:
    duplicates: dict[str, list[str]] = {}
    seen: dict[str, list[str]] = {}
    for entry in all_menu_entries():
        if not bool(entry.get("enabled", True)):
            continue
        command = _entry_command(entry)
        if not command or command.startswith("submenu:") or command == "submenu:main":
            continue
        seen.setdefault(command, []).append(_entry_label(entry))
    for command, labels in seen.items():
        if len(set(labels)) > 1:
            duplicates[command] = labels
    return duplicates


def _render_all_menus() -> tuple[dict[str, list[str]], list[str]]:
    rendered: dict[str, list[str]] = {}
    failures: list[str] = []
    for menu_name in ["main", *SUBMENU_ITEMS.keys()]:
        menu = make_menu()
        if menu_name != "main":
            open_submenu(menu, f"submenu:{menu_name}")
        text = render_terminal_jungle_menu(menu)
        lines = text.splitlines()
        rendered[menu_name] = lines
        for line_no, line in enumerate(lines, start=1):
            if len(line) > TERMINAL_FRAME_WIDTH:
                failures.append(f"{menu_name} terminal line {line_no} exceeds {TERMINAL_FRAME_WIDTH} chars")
    return rendered, failures


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []
    theme = DEFAULT_JUNGLE_MENU_THEME

    if "jungle" not in theme.border_style or "eucalyptus" not in theme.border_style:
        failures.append("menu theme border style must keep jungle/eucalyptus identity")
    if theme.font_family != theme.item_font_family:
        failures.append("title and item font stacks must stay aligned for a unified menu look")
    if theme.keyboard_input_font_family != theme.item_font_family:
        failures.append("popup keyboard input font stack must use the jungle/Jumanji menu font stack")
    if theme.keyboard_input_fill != theme.title_fill:
        failures.append("popup keyboard input fill color must use the carved jungle title color")
    if theme.keyboard_input_outline != theme.item_outline:
        failures.append("popup keyboard input outline must stay in the jungle item-outline palette")
    if GRAPHICAL_LABEL_MAX_LINES != 1:
        failures.append("graphical labels must fit one line inside menu row borders")
    if GRAPHICAL_DESCRIPTION_MAX_LINES > 2:
        failures.append("graphical descriptions must fit within two lines inside menu row borders")
    if TERMINAL_LABEL_WIDTH > 68 or TERMINAL_DESCRIPTION_WIDTH > 68:
        failures.append("terminal menu text widths must stay inside the 74-character jungle border")

    menu_names = ["main", *SUBMENU_ITEMS.keys()]
    for menu_name in menu_names:
        if not submenu_title(menu_name):
            failures.append(f"menu {menu_name} has no title")
        grouped = grouped_menu_labels(menu_name)
        if not any(grouped.values()):
            failures.append(f"menu {menu_name} has no visible labels")

    for entry in all_menu_entries():
        label = _entry_label(entry)
        description = _entry_description(entry)
        command = _entry_command(entry)
        if not label:
            failures.append(f"menu entry with command {command} has no label")
        if len(label) > MAX_LABEL_CHARS:
            warnings.append(f"long label is auto-fitted by renderer: {label}")
        if len(description) > MAX_DESCRIPTION_CHARS:
            warnings.append(f"long description is wrapped/fitted by renderer: {label}")

    duplicates = _visible_duplicate_commands()
    allowed_duplicate_commands = {
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
    }
    unexpected_duplicates = sorted(set(duplicates) - allowed_duplicate_commands)
    for command in unexpected_duplicates:
        failures.append(f"unexpected duplicate visible command {command}: {duplicates[command]}")

    _rendered, render_failures = _render_all_menus()
    failures.extend(render_failures)

    payload = {
        "status": "MENU_THEME_FIT_READY" if not failures else "MENU_THEME_FIT_INCOMPLETE",
        "theme": {
            "title": theme.title,
            "font_family": theme.font_family,
            "item_font_family": theme.item_font_family,
            "keyboard_input_font_family": theme.keyboard_input_font_family,
            "keyboard_input_fill": theme.keyboard_input_fill,
            "keyboard_input_outline": theme.keyboard_input_outline,
            "keyboard_input_shadow": theme.keyboard_input_shadow,
            "border_style": theme.border_style,
            "graphical_label_max_lines": GRAPHICAL_LABEL_MAX_LINES,
            "graphical_description_max_lines": GRAPHICAL_DESCRIPTION_MAX_LINES,
            "terminal_label_width": TERMINAL_LABEL_WIDTH,
            "terminal_description_width": TERMINAL_DESCRIPTION_WIDTH,
        },
        "menu_names": menu_names,
        "catalog_entry_count": len(all_menu_entries()),
        "visible_duplicate_commands": duplicates,
        "allowed_duplicate_commands": sorted(allowed_duplicate_commands),
        "failures": failures,
        "warnings": warnings,
        "updated_at": time.time(),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "status_path": str(STATUS_PATH), "failures": failures, "warnings": warnings}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
