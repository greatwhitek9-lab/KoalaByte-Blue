#!/usr/bin/env python3
"""Prepare/check KoalaByte Blue front-panel GPIO buttons.

This helper is safe for the one-shot installer. By default it writes a manifest
and validates the software mapping without touching GPIO hardware. Use
``--live-test`` on a Raspberry Pi to initialize gpiozero Button objects with
internal pull-ups and read button events.
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
        "status": "GPIO_BUTTONS_CONFIGURED",
        "mode": "active_low_internal_pull_up",
        "internal_pull_up_enabled": DEFAULT_ELECTRICAL_MODE.pull_up,
        "not_pressed_raw_level": DEFAULT_ELECTRICAL_MODE.idle_state,
        "pressed_raw_level": DEFAULT_ELECTRICAL_MODE.pressed_state,
        "wiring": DEFAULT_ELECTRICAL_MODE.wiring,
        "common_ground": "Pi GND, recommended physical pin 39 on the 40-pin header/extender",
        "do_not_wire_to": ["3.3V", "5V"],
        "debounce_seconds_default": 0.05,
        "buttons": DEFAULT_BUTTONS,
        "wiring_summary": [
            "Each normally-open 6x6 tactile switch goes between its assigned BCM GPIO and GND.",
            "gpiozero Button(..., pull_up=True) enables the Raspberry Pi internal pull-up resistor.",
            "Not pressed reads HIGH; pressed shorts to GND and reads LOW.",
            "The gpiozero logical state still reports is_pressed=True while the raw electrical level is LOW.",
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
        "status": "GPIO_BUTTONS_LIVE_TEST_STARTED",
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
        status["status"] = "GPIO_BUTTONS_LIVE_TEST_COMPLETE"
        status["finished_at"] = time.time()
        write_json(status_path, status)
        return 0
    finally:
        manager.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare/check KoalaByte Blue GPIO front-panel buttons.")
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
        "status": "GPIO_BUTTONS_READY",
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
