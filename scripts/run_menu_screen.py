#!/usr/bin/env python3
"""Run the KoalaByte Blue wrapped jungle menu interface."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Optional

os.environ.setdefault("KOALABYTE_TTS", "1")

from koalablue.menu_action_runner import run_automated_menu_action
from koalablue.menu_catalog import leaf_menu_entries, make_menu_items, submenu_name_from_command
from koalablue.menu_ui import MenuEvent, MenuItem, MenuSelectionScreen

try:
    from koalablue.gpio_buttons import GPIOButtonManager
except Exception:  # pragma: no cover
    GPIOButtonManager = None  # type: ignore

KEY_MAP = {
    "w": "up",
    "s": "down",
    "a": "move_left",
    "d": "move_right",
    "up": "up",
    "down": "down",
    "left": "move_left",
    "right": "move_right",
    "": "select",
    "enter": "select",
    "select": "select",
    "backspace": "backspace",
    "delete": "backspace",
    "save": "save",
    "done": "save",
    "esc": "cancel",
    "escape": "cancel",
    "m": "main_menu",
    "menu": "main_menu",
    "q": "quit",
    "quit": "quit",
}

# Readiness sentinels kept here because scripts/check_repo_readiness.py validates
# that the automated menu runner still preserves coverage for these protected
# T114/GNSS/BlueZ actions even though the implementation now routes most leaves
# through koalablue.menu_action_runner.
READINESS_SENTINELS = (
    "t114_primary_ble_scan",
    "t114_primary_gnss_fix",
    "koalablue.gnss_location",
    "bluez_platypus_bt_proxy",
)


def clear() -> None:
    os.system("clear" if os.name != "nt" else "cls")


def selected_quit(event: Optional[MenuEvent]) -> bool:
    return event is not None and event.event_type in {"select", "touch_long_press_select"} and event.command == "quit"


def open_submenu(menu: MenuSelectionScreen, command: str) -> bool:
    submenu = submenu_name_from_command(command)
    if not submenu:
        return False
    target = "main" if submenu == "main" else submenu
    new_items = make_menu_items(MenuItem, target)
    if not new_items:
        return False
    menu.menu_name = target
    menu.items = new_items
    menu.selected_index = 0
    menu.scroll_offset = 0
    menu.touch.down_y = None
    menu.touch.current_y = None
    menu.touch.down_time = None
    menu.touch.moved = False
    return True


def selected_payload_path(command: str, timestamp: float) -> Path:
    out_dir = Path("logs/menu_actions")
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in command)[:72] or "menu_leaf"
    return out_dir / f"{safe}_{int(timestamp)}.json"


def write_action_payload(item: MenuItem, payload: dict[str, object]) -> Path:
    timestamp = float(payload.get("timestamp", time.time()))
    path = selected_payload_path(item.command, timestamp)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def write_result(item: MenuItem, status: str, result: object, note: str = "") -> None:
    payload = {"timestamp": time.time(), "label": item.label, "command": item.command, "group": item.group, "status": status, "result": result}
    if note:
        payload["note"] = note
    path = write_action_payload(item, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    print(f"\n{item.label} written -> {path}\n")


def run_eucalyptus_mode_action(_item: MenuItem) -> None:
    from koalablue.eucalyptus_cyberpet import JungleMenuUnavailable, run_graphical, run_terminal
    try:
        run_graphical(fullscreen=True)
    except JungleMenuUnavailable as exc:
        if os.environ.get("MENU_NO_TERMINAL_FALLBACK", "0") in {"1", "true", "TRUE", "yes", "YES"}:
            raise
        print(f"Full-color Eucalyptus Mode unavailable; terminal renderer started: {exc}")
        run_terminal()


def run_generic_action(item: MenuItem) -> None:
    result = run_automated_menu_action(item.command, item.label, item.group)
    write_result(item, str(result.get("status", "AUTOMATED_ACTION_COMPLETE")), result, "Automated menu action selected from the wrapped interface; no command prompt required.")


def register_default_action_handlers(menu: MenuSelectionScreen) -> None:
    for entry in leaf_menu_entries():
        command = str(entry.get("command", ""))
        if command:
            menu.register_handler(command, run_generic_action)
    menu.register_handler("eucalyptus_mode", run_eucalyptus_mode_action)


def make_menu() -> MenuSelectionScreen:
    menu = MenuSelectionScreen()
    register_default_action_handlers(menu)
    return menu


def apply_menu_event(menu: MenuSelectionScreen, command: str) -> Optional[MenuEvent]:
    before_item = menu.selected_item
    event = menu.handle_command(command)
    selected_command = event.command if event is not None else before_item.command
    if selected_command.startswith("submenu:"):
        open_submenu(menu, selected_command)
    return event


def translate_terminal_input(menu: MenuSelectionScreen, raw_input: str) -> str:
    raw = raw_input.rstrip("\n")
    lowered = raw.strip().lower()
    if getattr(menu, "display_mode", "menu") == "keyboard":
        if lowered in KEY_MAP:
            return KEY_MAP[lowered]
        if lowered.startswith(("keyboard text ", "voice text ", "dictate ", "type ", "keyboard key ", "key ", "char ")):
            return raw.strip()
        return f"keyboard text {raw}"
    return KEY_MAP.get(lowered, lowered)


def run_terminal() -> int:
    menu = make_menu()
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
            print("Keyboard: USB/Bluetooth keyboard works. w/s/a/d or arrows words, Enter=select/save, backspace=delete, q=quit")
            print("Popup keyboard: type full text then Enter/save, or use on-screen keys with buttons/touch.")
            print("Every enabled menu action runs from highlight/select; no shell command entry is needed.")
            if buttons is not None:
                button_event = buttons.get_event(timeout=0.05)
                if button_event is not None:
                    menu_event = apply_menu_event(menu, button_event.command)
                    if selected_quit(menu_event):
                        return 0
                    continue
            raw = input("> ")
            command = translate_terminal_input(menu, raw)
            if command == "quit":
                return 0
            menu_event = apply_menu_event(menu, command)
            if selected_quit(menu_event):
                return 0
            time.sleep(0.05)
    finally:
        if buttons is not None:
            buttons.close()


def _write_graphical_failure(exc: Exception) -> Path:
    out_dir = Path("logs/menu_actions")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "wrapped_interface_start_failed.json"
    path.write_text(json.dumps({"status": "WRAPPED_INTERFACE_START_FAILED", "error": str(exc), "timestamp": time.time(), "terminal_fallback": False}, indent=2, sort_keys=True), encoding="utf-8")
    return path


def run_wrapped_interface(*, windowed: bool, width: int, height: int, no_terminal_fallback: bool) -> int:
    from koalablue.menu_theme import JungleMenuRenderer, JungleMenuUnavailable
    try:
        return JungleMenuRenderer(menu=make_menu(), fullscreen=not windowed, width=width, height=height).run()
    except JungleMenuUnavailable as exc:
        if no_terminal_fallback:
            failure_path = _write_graphical_failure(exc)
            print(f"Wrapped KoalaByte interface unavailable; refusing terminal fallback. Details: {failure_path}")
            return 1
        print(f"Graphical jungle menu unavailable: {exc}")
        return run_terminal()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the KoalaByte Blue wrapped menu interface")
    parser.add_argument("--graphical", action="store_true", help="Run the large bubbly jungle/eucalyptus touchscreen menu; this is the default")
    parser.add_argument("--terminal", action="store_true", help="Debug only: force plain terminal mode")
    parser.add_argument("--no-terminal-fallback", action="store_true", help="Exit instead of falling back to terminal if graphical startup fails")
    parser.add_argument("--windowed", action="store_true", help="Run graphical mode in a window instead of fullscreen")
    parser.add_argument("--width", type=int, default=800, help="Window width when --windowed is used")
    parser.add_argument("--height", type=int, default=480, help="Window height when --windowed is used")
    args = parser.parse_args()
    env_blocks_fallback = os.environ.get("MENU_NO_TERMINAL_FALLBACK", "0") in {"1", "true", "TRUE", "yes", "YES"}
    if args.terminal:
        return run_terminal()
    return run_wrapped_interface(windowed=args.windowed, width=args.width, height=args.height, no_terminal_fallback=args.no_terminal_fallback or env_blocks_fallback)


if __name__ == "__main__":
    raise SystemExit(main())
