#!/usr/bin/env python3
"""Run a simple KoalaByte Blue menu screen loop.

This terminal loop is mainly for validation. On the device, the same
MenuSelectionScreen state machine can be rendered on the ESP32-S3 display or a
Pi touchscreen UI process.
"""

from __future__ import annotations

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


def main() -> int:
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


if __name__ == "__main__":
    raise SystemExit(main())
