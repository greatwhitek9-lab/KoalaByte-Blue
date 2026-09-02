#!/usr/bin/env python3
"""Offline regression gate for button/voice-driven DualEye expressions."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
for path in (ROOT, PI_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from koalablue.killerkoala_face_bridge import build_face_payload
from koalablue.menu_display_sync import (
    _esp32_face_payload,
    _esp32_menu_payload,
    build_ai_face_payload,
    build_menu_sync_payload,
)


@dataclass
class Item:
    label: str = "Bluetooth Inventory"
    command: str = "bluez_inventory"
    description: str = "Inventory nearby authorized Bluetooth devices"
    group: str = "Bluetooth"
    enabled: bool = True


@dataclass
class Event:
    event_type: str
    command: str
    selected_index: int = 0
    selected_label: str = "Bluetooth Inventory"
    selected_group: str = "Bluetooth"
    timestamp: float = 1.0


class Menu:
    menu_name = "main"
    menu_title = "Main Canopy"
    display_mode = "menu"
    selected_index = 0
    scroll_offset = 0
    visible_rows = 6
    idle_face_seconds = 30
    items = [Item()]
    selected_item = items[0]

    @staticmethod
    def _display_item(item: Item) -> Item:
        return item

    def visible_items(self) -> list[tuple[int, Item]]:
        return [(0, self.selected_item)]


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    menu = Menu()

    button_payload = build_menu_sync_payload(menu, Event("move", "down"))
    button_wire = _esp32_menu_payload(button_payload)
    require(button_wire.get("face_state") == "navigation",
            "button navigation did not select the navigation face", failures)
    require(button_wire.get("input_source") == "button_or_menu",
            "button navigation source was lost", failures)
    require(button_wire.get("eye_animation") == "scan",
            "button navigation did not select scanning/curious eyes", failures)
    require(button_wire.get("selected_label") == "Bluetooth Inventory",
            "right-side menu selection label was lost", failures)

    voice_event = Event("voice_select", "voice bluez inventory")
    voice_payload = build_menu_sync_payload(menu, voice_event)
    voice_wire = _esp32_menu_payload(voice_payload)
    require(voice_wire.get("input_source") == "voice",
            "voice menu source was lost", failures)
    require(bool(voice_wire.get("eye_look")) and bool(voice_wire.get("tone")),
            "voice menu payload lost its expression", failures)

    wake = build_ai_face_payload(menu, Event("voice_wake", "voice wake"),
                                 state="wake", message="KillerKoala heard")
    wake_wire = _esp32_face_payload(wake)
    require(wake_wire.get("eye_look") == "star",
            "wake voice state did not select alert/excited eyes", failures)
    require(wake_wire.get("eye_animation") == "pulse",
            "wake voice state did not select a visible pulse", failures)

    thinking = build_face_payload("thinking", "working out the request")
    success = build_face_payload("success", "previous error cleared")
    error = build_face_payload("error", "display fault")
    require(thinking.get("eye_animation") == "scan",
            "thinking face did not change to scanning eyes", failures)
    require(success.get("tone") == "happy",
            "explicit success was overridden by incidental error text", failures)
    require(error.get("eye_look") == "angry" and
            error.get("left_eye") == "#A54BFF" and
            error.get("right_eye") == "#32FF71",
            "error face lost the angry purple/green alarm design", failures)

    firmware = (ROOT / "firmware/esp32-dualeye/src/integrated_main.cpp").read_text(
        encoding="utf-8"
    )
    renderer = (ROOT / "firmware/esp32-dualeye/src/dualeye_video_renderer.cpp").read_text(
        encoding="utf-8"
    )
    for marker in (
        '"eye_style"', '"eye_status"', '"koalagotchi_status"',
        "applyEyeDocument(doc", "drawMenuLeft();", "drawMenuRight();",
        'leftPanel ? "ACTION" : "STATUS"',
    ):
        require(marker in firmware, f"active firmware missing {marker}", failures)
    for marker in (
        "drawKoalaFaceBase", "drawFurTufts", "drawBrow",
        "updateExpressionPose", "renderedLeft", "renderedBrightness",
        "colorFollow",
    ):
        require(marker in renderer, f"eye renderer missing {marker}", failures)

    result: dict[str, Any] = {
        "status": "ESP32_EXPRESSION_CONTROLS_READY" if not failures
                  else "ESP32_EXPRESSION_CONTROLS_FAILED",
        "failures": failures,
        "button_expression": {
            key: button_wire.get(key)
            for key in ("face_state", "tone", "eye_look", "eye_animation",
                        "input_source")
        },
        "voice_expression": {
            key: wake_wire.get(key)
            for key in ("state", "tone", "eye_look", "eye_animation",
                        "input_source")
        },
        "layout": {"right": "menu", "left": "action_status"},
        "expression_coordinator": "raspberry-pi",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
