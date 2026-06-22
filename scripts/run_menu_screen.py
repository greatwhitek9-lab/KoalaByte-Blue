#!/usr/bin/env python3
from __future__ import annotations

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
        "message": "Menu leaf item selected and routed. Use the matching documented helper for live hardware workflows.",
    }
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in item.command)[:72] or "menu_leaf"
    path = out_dir / f"{safe}_{int(payload['timestamp'])}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\n🌿 {item.label} routed → {path}\n")
    input("Press Enter to return to the menu...")


def make_menu() -> MenuSelectionScreen:
    menu = MenuSelectionScreen()
    # Register every leaf from every submenu so selecting a submenu action never silently does nothing.
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
            clear(); print(menu.render_text()); print("Keyboard test: w/s/a/d, Enter=select, m=menu, q=quit")
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


def main() -> int:
    return run_terminal()


if __name__ == "__main__":
    raise SystemExit(main())
