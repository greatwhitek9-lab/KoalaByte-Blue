#!/usr/bin/env python3
"""Run the KoalaByte Blue menu screen."""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional

os.environ.setdefault("KOALABYTE_TTS", "1")

from koalablue.menu_catalog import leaf_menu_entries, make_menu_items, submenu_name_from_command
from koalablue.menu_ui import MenuEvent, MenuItem, MenuSelectionScreen

try:
    from koalablue.gpio_buttons import GPIOButtonManager
except Exception:  # pragma: no cover
    GPIOButtonManager = None  # type: ignore

KEY_MAP = {"w": "up", "s": "down", "a": "move_left", "d": "move_right", "": "select", "m": "main_menu", "q": "quit"}


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


def route_leaf(item: MenuItem) -> None:
    payload = {
        "timestamp": time.time(),
        "label": item.label,
        "command": item.command,
        "group": item.group,
        "status": "routed",
        "message": "Menu leaf item selected and routed. Touch long-press, keyboard Enter, and the physical Select button all use this same execution path.",
    }
    path = write_action_payload(item, payload)
    print(f"\n🌿 {item.label} routed → {path}\n")


def _write_result(item: MenuItem, status: str, result: object, note: str = "") -> None:
    payload = {"timestamp": time.time(), "label": item.label, "command": item.command, "group": item.group, "status": status, "result": result}
    if note:
        payload["note"] = note
    path = write_action_payload(item, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    print(f"\n{item.label} written → {path}\n")


def _asdict_result(result: object) -> object:
    if isinstance(result, list):
        return [asdict(item) for item in result]
    return asdict(result)


def run_boomerang_action(_item: MenuItem) -> None:
    from koalablue import boomerang

    boomerang.run_interactive()


def run_eucalyptus_mode_action(_item: MenuItem) -> None:
    from koalablue.eucalyptus_cyberpet import JungleMenuUnavailable, run_graphical, run_terminal

    try:
        run_graphical(fullscreen=True)
    except JungleMenuUnavailable as exc:
        print(f"Full-color Eucalyptus Mode unavailable, falling back to terminal renderer: {exc}")
        run_terminal()


def run_eucalyptus_control_action(item: MenuItem) -> None:
    from koalablue.eucalyptus_wigle import control_status

    action = item.command.split(" ", 1)[1] if " " in item.command else "status"
    result = control_status(action)
    _write_result(item, str(result.get("status", "complete")), result, "Eucalyptus passive BLE/GPS/WiGLE helper. Upload requires explicit WiGLE env enablement and credentials.")


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
    _write_result(item, str(result.get("status", "complete")), result, "Automated Koala Kombat Kruisin’ action: defaults node ports, checks status, then runs the selected survey/upload action.")


def run_anteater_action(_item: MenuItem) -> None:
    from koalablue.anteater import render_summary, run_once

    print("\n== AntEater ==")
    report = run_once(scan_seconds=12.0)
    print(render_summary(report))


def run_koala_bluez_manifest(item: MenuItem) -> None:
    from koalablue.bluez_tools import module_manifest

    _write_result(item, "complete", asdict(module_manifest()))


def run_koala_bluez_inventory(item: MenuItem) -> None:
    from koalablue.bluez_tools import inventory

    _write_result(item, "complete", asdict(inventory()))


def run_koala_bluez_status(item: MenuItem) -> None:
    from koalablue.bluez_tools import status

    _write_result(item, "complete", asdict(status()))


def run_koala_bluez_scan(item: MenuItem) -> None:
    from koalablue.bluez_tools import scan

    _write_result(item, "complete", asdict(scan(duration_seconds=15)))


def run_koala_bluez_monitor(item: MenuItem) -> None:
    from koalablue.bluez_tools import monitor

    _write_result(item, "complete", asdict(monitor(duration_seconds=20)))


def run_koala_bluez_all_safe(item: MenuItem) -> None:
    from koalablue.bluez_tools import all_safe

    _write_result(item, "complete", _asdict_result(all_safe(duration_seconds=15)))


def run_protected_bluez_menu_action(item: MenuItem) -> None:
    from koalablue import bluez_protected_lab

    handlers = {
        "koala_bluez_info": bluez_protected_lab.protected_target_info,
        "koala_bluez_services": bluez_protected_lab.protected_target_services,
        "koala_bluez_gatt_readiness": bluez_protected_lab.protected_gatt_readiness,
        "bluez_outback_radio_ledger": bluez_protected_lab.outback_radio_ledger,
        "bluez_classic_track_finder": bluez_protected_lab.classic_track_finder,
        "bluez_treehouse_rfcomm_wiremap": bluez_protected_lab.treehouse_rfcomm_wiremap,
        "bluez_pouch_link_echo": bluez_protected_lab.pouch_link_echo,
        "bluez_gumnut_gatt_ghostmap": bluez_protected_lab.gumnut_gatt_ghostmap,
        "bluez_platypus_bt_proxy": bluez_protected_lab.platypus_bt_proxy,
    }
    result = handlers[item.command]()
    _write_result(item, "complete" if not result.results or not result.results[0].skipped else "blocked", asdict(result), "Protected BlueZ lab action; unlock protected actions and set owned-device target env when required.")


def run_t114_primary_controller_check(item: MenuItem) -> None:
    from koalablue.t114_bluez import check_controller

    result = check_controller()
    _write_result(item, result.status, asdict(result), "Checks the default combined-safe USB CDC JSON controller path.")


def run_t114_primary_status(item: MenuItem) -> None:
    from koalablue.t114_bluez import run_wrapped_bluez

    result = run_wrapped_bluez("status", duration_seconds=10)
    _write_result(item, result.status, asdict(result), "Shows primary T114 BLE/TX/mouth status; GNSS is also ingested by the node manager.")


def run_t114_primary_ble_scan(item: MenuItem) -> None:
    from koalablue.t114_bluez import run_wrapped_bluez

    result = run_wrapped_bluez("scan", duration_seconds=30)
    _write_result(item, result.status, asdict(result), "Bounded passive BLE scan through the T114 primary radio.")


def run_t114_ble_tx_status(item: MenuItem) -> None:
    from koalablue.t114_bluez import run_wrapped_bluez

    result = run_wrapped_bluez("tx-status", duration_seconds=5)
    _write_result(item, result.status, asdict(result), "Checks bounded non-connectable lab beacon TX status.")


def run_t114_primary_gnss_fix(item: MenuItem) -> None:
    from koalablue.gnss_location import current_fix, fix_to_dict

    fix = current_fix(authorized=None, prompt=False)
    _write_result(item, "complete", {"fix": fix_to_dict(fix), "source_priority": "heltec-t114-gnss"}, "Protected location gate still controls coordinate visibility.")


def run_meshtastic_status(item: MenuItem) -> None:
    from koalablue.meshtastic_app import status

    _write_result(item, "complete", status())


def run_meshtastic_nodes(item: MenuItem) -> None:
    from koalablue.meshtastic_app import nodes

    _write_result(item, "complete", nodes())


def run_meshtastic_gps(item: MenuItem) -> None:
    from koalablue.meshtastic_app import gps_info

    _write_result(item, "complete", gps_info())


def run_location_gate_status(item: MenuItem) -> None:
    from koalablue.location_password_gate import PASSWORD_FILE, UNLOCK_ENV, password_exists

    payload = {
        "configured": password_exists(),
        "unlocked": os.environ.get(UNLOCK_ENV) in {"1", "true", "TRUE", "yes", "YES"},
        "path": str(PASSWORD_FILE),
    }
    _write_result(item, "complete", payload)


def run_gnss_current_fix(item: MenuItem) -> None:
    from koalablue.gnss_location import current_fix, fix_to_dict

    fix = current_fix(authorized=None, prompt=False)
    _write_result(item, "complete", {"fix": fix_to_dict(fix), "source_priority": "heltec-t114-gnss"})


def register_default_action_handlers(menu: MenuSelectionScreen) -> None:
    for entry in leaf_menu_entries():
        command = str(entry.get("command", ""))
        if command and not command.startswith("status:"):
            menu.register_handler(command, route_leaf)
    menu.register_handler("boomerang", run_boomerang_action)
    menu.register_handler("eucalyptus_mode", run_eucalyptus_mode_action)
    for command in [
        "eucalyptus status",
        "eucalyptus start",
        "eucalyptus stop",
        "eucalyptus restart",
        "eucalyptus upload-status",
        "eucalyptus gps-trail",
        "eucalyptus wigle-upload",
    ]:
        menu.register_handler(command, run_eucalyptus_control_action)
    for command in [
        "kruisin status",
        "kruisin wifi-survey",
        "kruisin ble-survey",
        "kruisin survey",
        "kruisin gps-status",
        "kruisin export",
        "kruisin wigle-upload",
    ]:
        menu.register_handler(command, run_kruisin_action)
    menu.register_handler("anteater", run_anteater_action)
    menu.register_handler("koala_bluez_manifest", run_koala_bluez_manifest)
    menu.register_handler("koala_bluez_inventory", run_koala_bluez_inventory)
    menu.register_handler("koala_bluez_status", run_koala_bluez_status)
    menu.register_handler("koala_bluez_scan", run_koala_bluez_scan)
    menu.register_handler("koala_bluez_monitor", run_koala_bluez_monitor)
    menu.register_handler("koala_bluez_all_safe", run_koala_bluez_all_safe)
    for command in [
        "koala_bluez_info",
        "koala_bluez_services",
        "koala_bluez_gatt_readiness",
        "bluez_outback_radio_ledger",
        "bluez_classic_track_finder",
        "bluez_treehouse_rfcomm_wiremap",
        "bluez_pouch_link_echo",
        "bluez_gumnut_gatt_ghostmap",
        "bluez_platypus_bt_proxy",
    ]:
        menu.register_handler(command, run_protected_bluez_menu_action)
    menu.register_handler("t114_primary_controller_check", run_t114_primary_controller_check)
    menu.register_handler("t114_primary_status", run_t114_primary_status)
    menu.register_handler("t114_primary_ble_scan", run_t114_primary_ble_scan)
    menu.register_handler("t114_ble_tx_status", run_t114_ble_tx_status)
    menu.register_handler("t114_primary_gnss_fix", run_t114_primary_gnss_fix)
    menu.register_handler("t114_bluez_controller_check", run_t114_primary_controller_check)
    menu.register_handler("t114_bluez_status", run_t114_primary_status)
    menu.register_handler("meshtastic_status", run_meshtastic_status)
    menu.register_handler("meshtastic_nodes", run_meshtastic_nodes)
    menu.register_handler("meshtastic_gps", run_meshtastic_gps)
    menu.register_handler("location_gate_status", run_location_gate_status)
    menu.register_handler("gnss_current_fix", run_gnss_current_fix)


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
            print("Graphical jungle menu: python scripts/run_menu_screen.py --graphical --windowed")

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
