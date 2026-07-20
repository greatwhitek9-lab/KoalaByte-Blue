#!/usr/bin/env python3
"""Safe live test for the KoalaByte Blue K1-K8 front-panel board.

This script never executes menu, shutdown, or reboot actions. It only reads the
GPIO lines, prints press/release events, and records whether each physical key
was observed at least once.
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path

from gpiozero import Button


BUTTONS = {
    "K1": {"number": 1, "pin": 5, "physical_pin": 29, "label": "Main Menu", "command": "main_menu"},
    "K2": {"number": 2, "pin": 6, "physical_pin": 31, "label": "Move Left / Back", "command": "move_left"},
    "K3": {"number": 3, "pin": 13, "physical_pin": 33, "label": "Enter / Select", "command": "select"},
    "K4": {"number": 4, "pin": 19, "physical_pin": 35, "label": "Move Right / Forward", "command": "move_right"},
    "K5": {"number": 5, "pin": 26, "physical_pin": 37, "label": "Up", "command": "up"},
    "K6": {"number": 6, "pin": 21, "physical_pin": 40, "label": "Down", "command": "down"},
    "K7": {"number": 7, "pin": 20, "physical_pin": 38, "label": "Power On/Off", "command": "power_toggle", "protected_hold_seconds": 2.5},
    "K8": {"number": 8, "pin": 16, "physical_pin": 36, "label": "Reset / Reboot", "command": "reset", "protected_hold_seconds": 3.0},
}

running = True


def stop(*_: object) -> None:
    global running
    running = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely validate the KoalaByte K1-K8 GPIO board")
    parser.add_argument("--timeout", type=float, default=120.0, help="Maximum test duration in seconds")
    parser.add_argument(
        "--report",
        default="logs/pi_hardware/gpio_button_test.json",
        help="JSON report path",
    )
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Return success even when not every key was observed",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    print("KoalaByte Blue K1-K8 hardware test")
    print("VCC -> Pi 3.3V only (physical pin 1 or 17)")
    print("GND -> Pi GND (physical pin 39 recommended)")
    print("Inputs use internal pull-ups: idle=HIGH, pressed=LOW")
    print("K7 and K8 are TEST ONLY here; this script will not shut down or reboot the Pi.")
    print("")

    seen: set[str] = set()
    events: list[dict[str, object]] = []
    devices: list[Button] = []
    start = time.monotonic()

    def record(key: str, event: str) -> None:
        cfg = BUTTONS[key]
        row = {
            "timestamp": time.time(),
            "key": key,
            "button_number": cfg["number"],
            "event": event,
            "pin_bcm": cfg["pin"],
            "physical_pin": cfg["physical_pin"],
            "label": cfg["label"],
            "command": cfg["command"],
        }
        events.append(row)
        if event == "press":
            seen.add(key)
        print(
            f"{event.upper():7s} {key}  BCM{cfg['pin']} / pin {cfg['physical_pin']}  "
            f"{cfg['label']} -> {cfg['command']}",
            flush=True,
        )

    try:
        for key, cfg in BUTTONS.items():
            button = Button(int(cfg["pin"]), pull_up=True, bounce_time=0.05)
            button.when_pressed = lambda k=key: record(k, "press")
            button.when_released = lambda k=key: record(k, "release")
            devices.append(button)

        stuck_low = [key for key, button in zip(BUTTONS, devices) if button.is_pressed]
        if stuck_low:
            print("WARNING: key line(s) already LOW at startup: " + ", ".join(stuck_low))
            print("Check for reversed wiring, solder bridges, or a held key before continuing.")

        print("Press and release K1 through K8 once, left-to-right. Ctrl+C ends the test.")
        deadline = start + max(args.timeout, 1.0)
        while running and time.monotonic() < deadline and len(seen) < len(BUTTONS):
            time.sleep(0.05)
    except Exception as exc:
        print(f"GPIO test failed: {exc}", file=sys.stderr)
        result = {
            "status": "GPIO_TEST_ERROR",
            "error": str(exc),
            "seen_keys": sorted(seen),
            "events": events,
            "updated_at": time.time(),
        }
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        return 2
    finally:
        for button in devices:
            try:
                button.close()
            except Exception:
                pass

    missing = [key for key in BUTTONS if key not in seen]
    status = "GPIO_ALL_KEYS_PASS" if not missing else "GPIO_KEYS_INCOMPLETE"
    result = {
        "status": status,
        "electrical_mode": {"vcc": "3.3V", "idle": "HIGH", "pressed": "LOW", "pull_up": True},
        "seen_keys": sorted(seen),
        "missing_keys": missing,
        "events": events,
        "duration_seconds": round(time.monotonic() - start, 3),
        "protected_runtime_actions": {"K7": "hold 2.5 seconds", "K8": "hold 3.0 seconds"},
        "updated_at": time.time(),
    }
    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    print("")
    print(status)
    print(f"Seen: {', '.join(sorted(seen)) or 'none'}")
    print(f"Missing: {', '.join(missing) if missing else 'none'}")
    print(f"Report: {path}")
    return 0 if (not missing or args.allow_incomplete) else 1


if __name__ == "__main__":
    raise SystemExit(main())
