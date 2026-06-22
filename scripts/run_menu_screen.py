#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import time
from typing import Optional

os.environ.setdefault("KOALABYTE_TTS", "1")
from koalablue.menu_ui import MenuEvent, MenuItem, MenuSelectionScreen

try:
    from koalablue.gpio_buttons import GPIOButtonManager
except Exception:
    GPIOButtonManager = None  # type: ignore

KEY_MAP = {"w": "up", "s": "down", "a": "move_left", "d": "move_right", "": "select", "m": "main_menu", "q": "quit"}


def clear() -> None:
    os.system("clear" if os.name != "nt" else "cls")


def selected_quit(event: Optional[MenuEvent]) -> bool:
    return event is not None and event.event_type in {"select", "touch_long_press_select"} and event.command == "quit"


def emit_selected_action_face(event: Optional[MenuEvent]) -> None:
    if event is None or event.event_type not in {"select", "touch_long_press_select"}:
        return
    try:
        from koalablue.killerkoala_face_bridge import emit_action_for_menu_item
        emit_action_for_menu_item(event.selected_label, event.command)
    except Exception:
        pass


def run_boomerang_action(_item: MenuItem) -> None:
    from koalablue import boomerang
    boomerang.KILLERKOALA_BOOMERANG_ALERTS["boomerang_start"] = "BOOMerang!"
    boomerang.run_interactive()


def run_eucalyptus_mode_action(_item: MenuItem) -> None:
    from koalblue.eucalyptus_cyberpet import JungleMenuUnavailable, run_graphical, run_terminal
    try:
        run_graphical(fullscreen=True)
    except JungleMenuUnavailable:
        run_terminal()


def run_anteater_action(_item: MenuItem) -> None:
    from koalablue.anteater import render_summary, run_once
    report = run_once(scan_seconds=12.0)
    print(render_summary(report))
    input("\nPress Enter to return to the KoalaByte Blue menu...")


def register_default_action_handlers(menu: MenuSelectionScreen) -> None:
    menu.register_handler("boomerang", run_boomerang_action)
    menu.register_handler("eucalyptus_mode", run_eucalyptus_mode_action)
    menu.register_handler("anteater", run_anteater_action)


def make_menu() -> MenuSelectionScreen:
    menu = MenuSelectionScreen()
    register_default_action_handlers(menu)
    return menu


def run_terminal() -> int:
    menu = make_menu()
    buttons = GPIOButtonManager() if GPIOButtonManager is not None else None
    if buttons is not None:
        buttons.start()
    try:
        while True:
            clear()
            print(menu.render_text())
            print("Keyboard test: w/s/a/d, Enter=select, m=menu, q=quit")
            if buttons is not None:
                button_event = buttons.get_event(timeout=0.05)
                if button_event is not None:
                    menu_event = menu.handle_command(button_event.command)
                    emit_selected_action_face(menu_event)
                    if selected_quit(menu_event):
                        return 0
                    continue
            raw = input("> ").strip().lower()
            command = KEY_MAP.get(raw, raw)
            if command == "quit":
                return 0
            menu_event = menu.handle_command(command)
            emit_selected_action_face(menu_event)
            if selected_quit(menu_event):
                return 0
            time.sleep(0.05)
    finally:
        if buttons is not None:
            buttons.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the KoalaByte Blue menu screen")
    parser.add_argument("--graphical", action="store_true")
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=480)
    args = parser.parse_args()
    if args.graphical:
        from koalablue.menu_theme import JungleMenuRenderer, JungleMenuUnavailable
        try:
            return JungleMenuRenderer(menu=make_menu(), fullscreen=not args.windowed, width=args.width, height=args.height).run()
        except JungleMenuUnavailable:
            return run_terminal()
    return run_terminal()


if __name__ == "__main__":
    raise SystemExit(main())
