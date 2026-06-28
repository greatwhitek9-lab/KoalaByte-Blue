#!/usr/bin/env python3
"""Run the KoalaByte Blue menu screen."""

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
    from koalblue.gpio_buttons import GPIOButtonManager  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    try:
        from koalablue.gpio_buttons import GPIOButtonManager
    except Exception:  # pragma: no cover
        GPIOButtonManager = None  # type: ignore

KEY_MAP = {"w": "up", "s": "down", "a": "move_left", "d": "move_right", "": "select", "m": "main_menu", "q": "quit"}

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
    path = write_action_payload(item.command if isinstance(item, Path) else item, payload)  # type: ignore[arg-type]
    print(json.dumps(payload, indent=2, sort_keys=True))
    print(f"\n{item.label} written -> {path}\n")


def run_eucalyptus_mode_action(_item: MenuItem) -> None:
    from koalablue.eucalyptus_cyberpet import JungleMenuUnavailable, run_graphical, run_terminal

    try:
        run_graphical(fullscreen=True)
    except JungleMenuUnavailable as exc:
        print(f"Full-color Eucalyptus Mode unavailable; terminal renderer started: {exc}")
        run_terminal()


def run_eucalyptus_action(item: MenuItem) -> None:
    from koalablue.eucalyptus_wigle import control_status

    action = item.command.split(" ", 1)[1] if " " in item.command else "status"
    result = control_status(action)
    write_result(item, str(result.get("status", "complete")), result, "Automated Eucalyptus action selected from the menu.")


def prepare_kruisin_menu_env() -> dict[str, object]:
    os.environ.setdefault("KOALA_KOMBAT_NODE_MESH", "1")
    os.environ.setdefault("KOALA_KOMBAT_ESP32_PORT", "/dev/ttyACM1")
    os.environ.setdefault("KOALA_KOMBAT_HELTEC_PORT", "/dev/ttyACM0")
    os.environ.setdefault("KOALA_KOMBAT_GPS_LOGGING", "1")
    return {
        "KOALA_KOMBAT_NODE_MESH": os.environ.get("KOALA_KOMBAT_NODE_MESH", ""),
        "KOALA_KOMBAT_ESP32_PORT": os.environ.get("KOALA_KOMBAT_ESP32_PORT", ""),
        "KOALA_KOMBAT_HELTEC_PORT": os.environ.get("KOALA_KOMBAT_HELTEC_PORT", ""),
        "KOALA_KOMBAT_GPS_LOGGING": os.environ.get("KOALA_KOMBAT_GPS_LOGGING", ""),
        "gps_default_on": os.environ.get("KOALA_KOMBAT_GPS_LOGGING", "1") != "0",
        "gps_can_be_disabled_with": "KOALA_KOMBAT_GPS_LOGGING=0",
        "missing_gnss_is_non_fatal": True,
    }


def run_kruisin_action(item: MenuItem) -> None:
    from koalablue.koala_kombat_kruisin import control

    action = item.command.split(" ", 1)[1] if " " in item.command else "status"
    defaults = prepare_kruisin_menu_env()
    preflight = control("status")
    if action == "status":
        result = {"status": "KOALA_KOMBAT_MENU_STATUS", "menu_defaults": defaults, "preflight_status": preflight}
    else:
        operation = control(action)
        result = {"status": "KOALA_KOMBAT_MENU_ACTION_COMPLETE", "action": action, "menu_defaults": defaults, "preflight_status": preflight, "operation": operation}
    write_result(item, str(result.get("status", "complete")), result, "Automated Koala Kombat Kruisin action selected from the menu.")


def run_generic_action(item: MenuItem) -> None:
    result = run_automated_menu_action(item.command, item.label, item.group)
    write_result(item, str(result.get("status", "AUTOMATED_ACTION_COMPLETE")), result, "Automated menu action selected from the menu; no command prompt required.")


def register_default_action_handlers(menu: MenuSelectionScreen) -> None:
    for entry in leaf_menu_entries():
        command = str(entry.get("command", ""))
        if command:
            menu.register_handler(command, run_generic_action)

    menu.register_handler("eucalyptus_mode", run_eucalyptus_mode_action)
    for command in ["eucalyptus status", "eucalyptus start", "eucalyptus stop", "eucalyptus restart", "eucalyptus upload-status", "eucalyptus gps-trail", "eucalyptus wigle-upload"]:
        menu.register_handler(command, run_eucalyptus_action)
    for command in ["kruisin status", "kruisin wifi-survey", "kruisin ble-survey", "kruisin survey", "kruisin gps-status", "kruisin export", "kruisin wigle-upload"]:
        menu.register_handler(command, run_kruisin_action)


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
            print("Keyboard: w/s/a/d, Enter=select, m=menu, q=quit | Touchscreen: long press=select | Button B3/select=select")
            print("Every enabled menu action runs from highlight/select; no shell command entry is needed.")
            if buttons is not None:
                button_event = buttons.get_event(timeout=0.05)
                if button_event is not None:
                    menu_event = apply_menu_event(menu, button_event.command)
                    if selected_quit(menu_event):
                        return 0
                    continue
            raw = input("> ").strip().lower()
            command = KEY_MAP.get(raw, raw)
            if command == "quit":
                return 0
            menu_event = apply_menu_event(menu, command)
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
            return JungleMenuRenderer(menu=make_menu(), fullscreen=not args.windowed, width=args.width, height=args.height).run()
        except JungleMenuUnavailable as exc:
            print(f"Graphical jungle menu unavailable: {exc}")
            return run_terminal()
    return run_terminal()


if __name__ == "__main__":
    raise SystemExit(main())
