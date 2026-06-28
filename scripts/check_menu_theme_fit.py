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
from koalablue.menu_theme import DEFAULT_JUNGLE_MENU_THEME, GRAPHICAL_DESCRIPTION_MAX_LINES, GRAPHICAL_LABEL_MAX_LINES, render_terminal_jungle_menu  # noqa: E402
from scripts.run_menu_screen import make_menu, open_submenu  # noqa: E402

OUTPUT_DIR = ROOT / "logs" / "menu_actions"
STATUS_PATH = OUTPUT_DIR / "menu_theme_fit_status.json"
TERMINAL_FRAME_WIDTH = 74


def main() -> int:
    failures: list[str] = []
    theme = DEFAULT_JUNGLE_MENU_THEME
    if "jungle" not in theme.border_style or "eucalyptus" not in theme.border_style:
        failures.append("menu theme identity missing")
    if theme.font_family != theme.item_font_family:
        failures.append("menu font stacks diverged")
    if getattr(theme, "keyboard_input_font_family", theme.item_font_family) != theme.item_font_family:
        failures.append("keyboard input font stack diverged")
    if GRAPHICAL_LABEL_MAX_LINES != 1 or GRAPHICAL_DESCRIPTION_MAX_LINES > 2:
        failures.append("graphical menu text limits changed")
    menu_names = ["main", *SUBMENU_ITEMS.keys()]
    for menu_name in menu_names:
        if not submenu_title(menu_name):
            failures.append(f"menu {menu_name} has no title")
        if not any(grouped_menu_labels(menu_name).values()):
            failures.append(f"menu {menu_name} has no visible labels")
        menu = make_menu()
        if menu_name != "main":
            open_submenu(menu, f"submenu:{menu_name}")
        for line_no, line in enumerate(render_terminal_jungle_menu(menu).splitlines(), start=1):
            if len(line) > TERMINAL_FRAME_WIDTH:
                failures.append(f"{menu_name} terminal line {line_no} exceeds {TERMINAL_FRAME_WIDTH} chars")
    payload = {
        "status": "MENU_THEME_FIT_READY" if not failures else "MENU_THEME_FIT_INCOMPLETE",
        "theme": {"title": theme.title, "font_family": theme.font_family, "item_font_family": theme.item_font_family, "keyboard_input_font_family": getattr(theme, "keyboard_input_font_family", ""), "border_style": theme.border_style},
        "menu_names": menu_names,
        "catalog_entry_count": len(all_menu_entries()),
        "failures": failures,
        "updated_at": time.time(),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "status_path": str(STATUS_PATH), "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
