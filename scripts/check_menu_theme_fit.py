#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue.menu_catalog import SUBMENU_ITEMS, all_menu_entries, grouped_menu_labels, submenu_title  # noqa: E402
from koalblue.menu_theme import DEFAULT_JUNGLE_MENU_THEME, GRAPHICAL_DESCRIPTION_MAX_LINES, GRAPHICAL_LABEL_MAX_LINES, TERMINAL_DESCRIPTION_WIDTH, TERMINAL_LABEL_WIDTH, render_terminal_jungle_menu  # noqa: E402
from scripts.run_menu_screen import make_menu, open_submenu  # noqa: E402

OUTPUT_DIR = ROOT / "logs" / "menu_actions"
STATUS_PATH = OUTPUT_DIR / "menu_theme_fit_status.json"
TERMINAL_FRAME_WIDTH = 74
MAX_LABEL_CHARS = 42
MAX_DESCRIPTION_CHARS = 118


def _render_all_menus() -> list[str]:
    failures: list[str] = []
    for menu_name in ["main", *SUBMENU_ITEMS.keys()]:
        menu = make_menu()
        if menu_name != "main":
            open_submenu(menu, f"submenu:{menu_name}")
        for line_no, line in enumerate(render_terminal_jungle_menu(menu).splitlines(), start=1):
            if len(line) > TERMINAL_FRAME_WIDTH:
                failures.append(f"{menu_name} terminal line {line_no} exceeds {TERMINAL_FRAME_WIDTH} chars")
    return failures


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
        label = str(entry.get("label", "")).strip()
        description = str(entry.get("description", "")).strip()
        if not label:
            failures.append("menu entry has no label")
        if len(label) > MAX_LABEL_CHARS:
            warnings.append(f"long label is auto-fitted by renderer: {label}")
        if len(description) > MAX_DESCRIPTION_CHARS:
            warnings.append(f"long description is wrapped/fitted by renderer: {label}")

    failures.extend(_render_all_menus())

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
