#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STATUS_PATH = ROOT / "logs" / "one_shot" / "menu_display_sync_status.json"


def _failures_from_menu_payload(payload: dict[str, object]) -> list[str]:
    failures: list[str] = []
    if payload.get("type") != "menu_sync":
        failures.append("menu payload type must be menu_sync")
    controls = payload.get("controls", {})
    if not isinstance(controls, dict):
        failures.append("menu payload controls must be a dict")
    else:
        select_controls = set(controls.get("select", [])) if isinstance(controls.get("select"), list) else set()
        if "B3" not in select_controls:
            failures.append("B3/select must be advertised as a select control")
        if "touch_long_press" not in select_controls:
            failures.append("touch_long_press must be advertised as a select control")
        reopen_controls = set(controls.get("reopen_menu", [])) if isinstance(controls.get("reopen_menu"), list) else set()
        if "B1" not in reopen_controls:
            failures.append("B1/menu must be advertised as a menu reopen control")
        if "touch_double_tap" not in reopen_controls:
            failures.append("touch_double_tap must be advertised as a menu reopen control")
    if "B3/select or touchscreen long-press" not in str(payload.get("execute_hint", "")):
        failures.append("execute hint must mention B3/select or touchscreen long-press")
    if "30 seconds idle" not in str(payload.get("idle_face_rule", "")):
        failures.append("idle face rule must mention 30 seconds idle")
    displays = set(payload.get("synced_displays", [])) if isinstance(payload.get("synced_displays"), list) else set()
    if "heltec-t114" not in displays or "esp32-s3-dualeye" not in displays:
        failures.append("sync payload must target both Heltec T114 and ESP32-S3 DualEye")
    return failures


def _failures_from_ai_payload(payload: dict[str, object]) -> list[str]:
    failures: list[str] = []
    if payload.get("type") != "ai_face_sync":
        failures.append("AI face payload type must be ai_face_sync")
    if payload.get("display_mode") != "ai_face":
        failures.append("AI face payload display_mode must be ai_face")
    if int(payload.get("idle_timeout_seconds", 0)) != 30:
        failures.append("AI face payload idle timeout must be 30 seconds")
    if "B1/menu or double-tap" not in str(payload.get("menu_reopen_hint", "")):
        failures.append("AI face payload must include B1/menu or double-tap reopen hint")
    displays = set(payload.get("synced_displays", [])) if isinstance(payload.get("synced_displays"), list) else set()
    if "heltec-t114" not in displays or "esp32-s3-dualeye" not in displays:
        failures.append("AI face payload must target both Heltec T114 and ESP32-S3 DualEye")
    return failures


def main() -> int:
    os.environ.setdefault("KOALABYTE_MENU_SYNC", "0")

    from koalablue.menu_display_sync import build_ai_face_payload, build_menu_sync_payload, sync_ai_face_display, sync_menu_state
    from koalablue.menu_ui import MenuItem, MenuSelectionScreen

    failures: list[str] = []

    menu = MenuSelectionScreen(visible_rows=4)
    original_label = menu.selected_item.label
    move_event = menu.handle_command("down")
    if move_event is None or move_event.event_type != "move":
        failures.append("down command must move/highlight a menu item")
    if menu.selected_item.label == original_label and len(menu.items) > 1:
        failures.append("down command did not change highlighted item")

    menu_payload = build_menu_sync_payload(menu, move_event)
    failures.extend(_failures_from_menu_payload(menu_payload))
    sync_payload = sync_menu_state(menu, move_event)
    if sync_payload.get("sync_status") != "disabled":
        failures.append("KOALABYTE_MENU_SYNC=0 should make sync_menu_state non-hardware check disabled")

    leaf = MenuSelectionScreen(items=[MenuItem(label="Display Sync Test Action", command="display_sync_test_action", description="Deterministic no-hardware leaf action", group="System / Companion")], visible_rows=1)
    ran: list[str] = []
    leaf.register_handler("display_sync_test_action", lambda item: ran.append(item.command))

    selected_event = leaf.handle_command("select")
    if selected_event is None or selected_event.event_type != "select":
        failures.append("select command must execute the highlighted menu path")
    if ran != ["display_sync_test_action"]:
        failures.append("registered leaf handler did not run from select path")
    if leaf.display_mode != "ai_face" or leaf.face_state != "action_complete":
        failures.append("completed action must return the display to AI face mode")

    ai_payload = build_ai_face_payload(leaf, selected_event, state=leaf.face_state, message=leaf.face_message)
    failures.extend(_failures_from_ai_payload(ai_payload))
    ai_sync = sync_ai_face_display(leaf, selected_event, state=leaf.face_state, message=leaf.face_message)
    if ai_sync.get("sync_status") != "disabled":
        failures.append("KOALABYTE_MENU_SYNC=0 should make sync_ai_face_display non-hardware check disabled")

    waiting_event = leaf.handle_command("select")
    if waiting_event is None or waiting_event.event_type != "ai_face_waiting_for_menu":
        failures.append("select while AI face is active must wait for menu reopen")

    reopen_event = leaf.handle_command("main_menu")
    if reopen_event is None or reopen_event.event_type != "menu_reopen":
        failures.append("B1/main_menu must reopen the menu from AI face mode")
    if leaf.display_mode != "menu":
        failures.append("menu must be visible after B1/main_menu reopen")

    leaf.last_input_at = time.time() - 31
    idle_event = leaf.check_idle_timeout()
    if idle_event is None or idle_event.event_type != "idle_timeout":
        failures.append("menu must return to AI face after 30 seconds idle")
    if leaf.display_mode != "ai_face" or leaf.face_state != "idle":
        failures.append("idle timeout must switch display_mode to AI face idle")

    leaf.on_touch_down(12, now=100.0)
    first_tap = leaf.on_touch_up(12, now=100.05)
    leaf.on_touch_down(12, now=100.20)
    second_tap = leaf.on_touch_up(12, now=100.25)
    if second_tap is None or second_tap.event_type != "menu_reopen":
        failures.append("double-tap while AI face is active must reopen the menu")
    if leaf.display_mode != "menu":
        failures.append("menu must be visible after touchscreen double-tap reopen")

    status = {
        "status": "MENU_DISPLAY_SYNC_READY" if not failures else "MENU_DISPLAY_SYNC_INCOMPLETE",
        "updated_at": time.time(),
        "checked": {
            "highlight_scroll": True,
            "b3_select_path": True,
            "touch_long_press_path_declared": True,
            "idle_face_timeout_seconds": 30,
            "action_complete_returns_to_ai_face": True,
            "b1_menu_reopens": True,
            "touch_double_tap_reopens": True,
            "heltec_sync_payload": True,
            "esp32_dualeye_sync_payload": True,
            "hardware_ports_required_for_check": False,
        },
        "first_tap_event": None if first_tap is None else first_tap.event_type,
        "failures": failures,
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(status, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
