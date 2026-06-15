#!/usr/bin/env python3
"""Run the KoalaByte Blue menu screen.

Default mode is the terminal validation loop. Use --graphical for the RevA14
large bubbly jungle/eucalyptus touchscreen menu.
"""

from __future__ import annotations

import argparse
import os
import time
from typing import Optional

from koalablue.menu_ui import MenuEvent, MenuSelectionScreen

try:
    from koalablue.gpio_buttons import GPIOButtonManager
except Exception:  # pragma: no cover
    GPIOButtonManager = None  # type: ignore

KEY_MAP = {
    "w": "up",
    "s": "down",
    "a": "move_left",
    "d": "move_right",
    "": "select",
    "m": "main_menu",
    "q": "quit",
}


def clear() -> None:
    os.system("clear" if os.name != "nt" else "cls")


def selected_quit(event: Optional[MenuEvent]) -> bool:
    return event is not None and event.event_type in {"select", "touch_long_press_select"} and event.command == "quit"


def run_terminal() -> int:
    menu = MenuSelectionScreen()
    buttons = GPIOButtonManager() if GPIOButtonManager is not None else None
    if buttons is not None:
        buttons.start()

    try:
        while True:
            clear()
            print(menu.render_text())
            if buttons is not None and buttons.available:
                print("GPIO buttons: active")
            elif buttons is not None and buttons.error:
                print(f"GPIO buttons: {buttons.error}")
            print("Keyboard test: w/s/a/d, Enter=select, m=menu, q=quit")
            print("Graphical jungle menu: python scripts/run_menu_screen.py --graphical --windowed")

            if buttons is not None:
                button_event = buttons.get_event(timeout=0.05)
                if button_event is not None:
                    menu_event = menu.handle_command(button_event.command)
                    if selected_quit(menu_event):
                        return 0
                    continue

            raw = input("> ").strip().lower()
            command = KEY_MAP.get(raw, raw)
            if command == "quit":
                return 0
            menu_event = menu.handle_command(command)
            if selected_quit(menu_event):
                return 0
            time.sleep(0.05)
    finally:
        if buttons is not None:
            buttons.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the KoalaByte Blue menu screen")
    parser.add_argument("--graphical", action="store_true", help="Run the large bubbly jungle/eucalyptus touchscreen menu")
    parser.add_argument("--windowed", action="store_true", help="Run graphical mode in a window instead of fullscreen")
    parser.add_argument("--width", type=int, default=800, help="Window width when --windowed is used")
    parser.add_argument("--height", type=int, default=480, help="Window height when --windowed is used")
    args = parser.parse_args()

    if args.graphical:
        from koalablue.menu_theme import JungleMenuRenderer, JungleMenuUnavailable

        try:
            return JungleMenuRenderer(fullscreen=not args.windowed, width=args.width, height=args.height).run()
        except JungleMenuUnavailable as exc:
            print(f"Graphical jungle menu unavailable: {exc}")
            return run_terminal()
    return run_terminal()


if __name__ == "__main__":
    raise SystemExit(main())
