#!/usr/bin/env python3
"""Prepare/check KoalaByte Blue front-panel GPIO button board.

Default hardware is now an 8-key module with header pins VCC, GND, and K1-K8.
The helper writes a manifest and validates the software mapping without touching
GPIO hardware unless ``--live-test`` is used on a Raspberry Pi.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

from koalablue.gpio_buttons import DEFAULT_BUTTONS, DEFAULT_ELECTRICAL_MODE, GPIOButtonManager

DEFAULT_MANIFEST_PATH = Path("logs/gpio_buttons/gpio_button_manifest.json")
DEFAULT_STATUS_PATH = Path("logs/gpio_buttons/gpio_button_status.json")


def build_manifest() -> Dict[str, Any]:
    return {
        "status": "GPIO_8KEY_BUTTON_BOARD_CONFIGURED",
        "board_type": "8 independent key button module with VCC, GND, K1-K8 header",
        "mode": "active_low_internal_pull_up",
        "power": "VCC must connect to Pi 3.3V only; do not use 5V with Pi GPIO.",
        "internal_pull_up_enabled": DEFAULT_ELECTRICAL_MODE.pull_up,
        "not_pressed_raw_level": DEFAULT_ELECTRICAL_MODE.idle_state,
        "pressed_raw_level": DEFAULT_ELECTRICAL_MODE.pressed_state,
        "wiring": DEFAULT_ELECTRICAL_MODE.wiring,
        "common_ground": "Module GND to Pi GND, recommended physical pin 39 on the 40-pin header/extender",
        "vcc": "Module VCC to Pi physical pin 1 or 17, 3.3V only",
        "do_not_wire_to": ["5V", "raw battery", "ESP32 GPIO", "Heltec GPIO"],
        "debounce_seconds_default": 0.05,
        "buttons": DEFAULT_BUTTONS,
        "wiring_summary": [
            "Use K1-K8 left-to-right across the button board.",
            "K1-K6 replace the previous six separate tactile buttons.",
            "K7 is the dedicated Shutdown button.",
            "K8 is the dedicated Reset/Reboot button.",
            "gpiozero Button(..., pull_up=True) enables the Raspberry Pi internal pull-up resistor.",
            "Idle/not pressed reads HIGH; pressed reads LOW.",
        ],
    }


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_live_test(seconds: float, status_path: Path) -> int:
    manager = GPIOButtonManager(log_path="logs/gpio_buttons/gpio_button_events.jsonl")
    manager.start()
    started_at = time.time()
    status: Dict[str, Any] = {
        "status": "GPIO_8KEY_BUTTON_BOARD_LIVE_TEST_STARTED",
        "started_at": started_at,
        "seconds": seconds,
        "internal_pull_up_enabled": DEFAULT_ELECTRICAL_MODE.pull_up,
        "not_pressed_raw_level": DEFAULT_ELECTRICAL_MODE.idle_state,
        "pressed_raw_level": DEFAULT_ELECTRICAL_MODE.pressed_state,
        "events": [],
    }

    if not manager.available:
        status.update({"status": "GPIO_BUTTONS_UNAVAILABLE", "error": manager.error})
        write_json(status_path, status)
        strict = os.environ.get("STRICT_GPIO_BUTTONS", "0") in {"1", "true", "True", "yes", "YES"}
        return 1 if strict else 0

    try:
        deadline = started_at + seconds
        while time.time() < deadline:
            event = manager.get_event(timeout=0.25)
            if event is None:
                continue
            status["events"].append(
                {
                    "button_number": event.number,
                    "name": event.name,
                    "label": event.label,
                    "command": event.command,
                    "event_type": event.event_type,
                    "pin_bcm": event.pin_bcm,
                    "timestamp": event.timestamp,
                }
            )
        status["status"] = "GPIO_8KEY_BUTTON_BOARD_LIVE_TEST_COMPLETE"
        status["finished_at"] = time.time()
        write_json(status_path, status)
        return 0
    finally:
        manager.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare/check KoalaByte Blue 8-key GPIO front-panel button board.")
    parser.add_argument("--manifest-path", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--status-path", default=str(DEFAULT_STATUS_PATH))
    parser.add_argument("--check-only", action="store_true", help="Write/validate manifest only; do not touch GPIO hardware.")
    parser.add_argument("--live-test", action="store_true", help="Initialize gpiozero buttons and watch for button events.")
    parser.add_argument("--seconds", type=float, default=10.0, help="Live-test duration.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest_path)
    status_path = Path(args.status_path)
    manifest = build_manifest()
    write_json(manifest_path, manifest)

    status: Dict[str, Any] = {
        "status": "GPIO_8KEY_BUTTON_BOARD_READY",
        "manifest_path": str(manifest_path),
        "internal_pull_up_enabled": DEFAULT_ELECTRICAL_MODE.pull_up,
        "not_pressed_raw_level": DEFAULT_ELECTRICAL_MODE.idle_state,
        "pressed_raw_level": DEFAULT_ELECTRICAL_MODE.pressed_state,
        "live_gpio_initialized": False,
        "updated_at": time.time(),
    }
    write_json(status_path, status)

    print(json.dumps(status, sort_keys=True))

    if args.live_test and not args.check_only:
        return run_live_test(args.seconds, status_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
