#!/usr/bin/env python3
from __future__ import annotations

import argparse

from koalablue.menu_theme import JungleMenuRenderer, JungleMenuUnavailable
from koalablue.menu_ui import MenuSelectionScreen


def main() -> int:
    parser = argparse.ArgumentParser(description="Run KoalaByte menu with popup keyboard support")
    parser.add_argument("--graphical", action="store_true")
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=480)
    args = parser.parse_args()
    menu = MenuSelectionScreen()
    if args.graphical:
        try:
            return JungleMenuRenderer(menu=menu, fullscreen=not args.windowed, width=args.width, height=args.height).run()
        except JungleMenuUnavailable:
            pass
    while True:
        print(menu.render_text())
        raw = input("> ")
        lowered = raw.strip().lower()
        if lowered in {"q", "quit"}:
            return 0
        if getattr(menu, "display_mode", "menu") == "keyboard" and lowered not in {"w", "a", "s", "d", "enter", "save", "backspace", "esc", "escape"}:
            command = f"keyboard text {raw}"
        else:
            command = {"w": "up", "s": "down", "a": "move_left", "d": "move_right", "enter": "select", "save": "save", "backspace": "backspace", "esc": "cancel", "escape": "cancel"}.get(lowered, lowered or "select")
        menu.handle_command(command)


if __name__ == "__main__":
    raise SystemExit(main())
