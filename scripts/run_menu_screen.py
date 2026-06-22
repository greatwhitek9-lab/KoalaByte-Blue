#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Optional

os.environ.setdefault("KOALABYTE_TTS", "1")
from koalablue.menu_catalog import leaf_menu_entries
from koalablue.menu_ui import MenuEvent, MenuItem, MenuSelectionScreen

try:
    from koalablue.gpio_buttons import GPIOButtonManager
except Exception:
    GPIOButtonManager = None  # type: ignore

KEY_MAP = {"w":"up","s":"down","a":"move_left","d":"move_right","":"select","m":"main_menu","q":"quit"}


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


def write_leaf_selection(item: MenuItem) -> None:
    out_dir = Path("logs/menu_actions")
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": time.time(),
        "label": item.label,
        "command": item.command,
        "group": item.group,
        "status": "routed",
        "message": "Menu leaf item selected and routed. Touch long-press, keyboard Enter, and the physical Select button all use this same execution path.",
    }
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in item.command)[:72] or "menu_leaf"
    path = out_dir / f"{safe}_{int(payload['timestamp'])}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\n🌿 {item.label} routed → {path}\n")


def make_menu() -> MenuSelectionScreen:
    menu = MenuSelectionScreen()
    # Register every executable leaf from every submenu so touchscreen long-press,
    # keyboard Enter, and the physical Select button never silently do nothing.
    for entry in leaf_menu_entries():
        command = str(entry.get("command", ""))
        if command:
            menu.register_handler(command, write_leaf_selection)
    return menu


def run_terminal() -> int:
    menu = make_menu()
    buttons = GPIOButtonManager() if GPIOButtonManager is not None else None
    if buttons is not None:
        buttons.start()
    try:
        while True:
            clear(); print(menu.render_text()); print("Keyboard: w/s/a/d, Enter=select, m=menu, q=quit | Touchscreen: long press=select | Button B3/select=select")
            if buttons is not None:
                button_event = buttons.get_event(timeout=0.05)
                if button_event is not None:
                    menu_event = menu.handle_command(button_event.command)
                    emit_selected_action_face(menu_event)
                    if selected_quit(menu_event): return 0
                    continue
            raw = input("> ").strip().lower()
            command = KEY_MAP.get(raw, raw)
            if command == "quit": return 0
            menu_event = menu.handle_command(command)
            emit_selected_action_face(menu_event)
            if selected_quit(menu_event): return 0
            time.sleep(0.05)
    finally:
        if buttons is not None:
            buttons.close()


def run_graphical(*, fullscreen: bool = True, width: int = 800, height: int = 480) -> int:
    try:
        from koalablue.menu_theme import JungleMenuRenderer, JungleMenuUnavailable
    except Exception as exc:
        print(f"Graphical jungle menu unavailable: {exc}")
        return run_terminal()
    try:
        return JungleMenuRenderer(menu=make_menu(), fullscreen=fullscreen, width=width, height=height).run()
    except JungleMenuUnavailable as exc:
        print(f"Graphical jungle menu unavailable: {exc}")
        return run_terminal()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the KoalaByte Blue menu screen")
    parser.add_argument("--graphical", action="store_true", help="Run the touchscreen jungle menu")
    parser.add_argument("--windowed", action="store_true", help="Use a window instead of fullscreen for graphical mode")
    parser.add_argument("--width", type=int, default=800, help="Window width for --windowed")
    parser.add_argument("--height", type=int, default=480, help="Window height for --windowed")
    args = parser.parse_args()
    if args.graphical:
        return run_graphical(fullscreen=not args.windowed, width=args.width, height=args.height)
    return run_terminal()


if __name__ == "__main__":
    raise SystemExit(main())
