#!/usr/bin/env python3
"""Prepare/check KoalaByte Blue front-panel GPIO button board.

Default hardware is a GODIYMODULES MOD-ST034-1 / ASIN B0FH9C88DJ
8-key module with header pins VCC, GND, and K1-K8. On a Raspberry Pi,
check-only also performs a non-interactive GPIO initialization probe. If the
button GPIO stack cannot initialize, the installer records touch_speech_only
mode and continues unless STRICT_GPIO_BUTTONS=1 is explicitly set.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

from koalablue.control_mode import load_control_mode, write_control_mode
from koalablue.gpio_buttons import DEFAULT_BUTTONS, DEFAULT_ELECTRICAL_MODE, GPIOButtonManager

DEFAULT_MANIFEST_PATH = Path("logs/gpio_buttons/gpio_button_manifest.json")
DEFAULT_STATUS_PATH = Path("logs/gpio_buttons/gpio_button_status.json")


def build_manifest() -> Dict[str, Any]:
    return {
        "status": "GPIO_8KEY_BUTTON_BOARD_CONFIGURED",
        "board_type": "8 independent key button module with VCC, GND, K1-K8 header",
        "orderable_reference": "GODIYMODULES MOD-ST034-1 / ASIN B0FH9C88DJ; listing includes 2 modules, KoalaByte uses 1",
        "mode": "active_low_internal_pull_up",
        "power": "VCC must connect to Pi 3.3V only; do not use 5V with Pi GPIO.",
        "internal_pull_up_enabled": DEFAULT_ELECTRICAL_MODE.pull_up,
        "not_pressed_raw_level": DEFAULT_ELECTRICAL_MODE.idle_state,
        "pressed_raw_level": DEFAULT_ELECTRICAL_MODE.pressed_state,
        "wiring": DEFAULT_ELECTRICAL_MODE.wiring,
        "common_ground": "Module GND to Pi GND, recommended physical pin 39 on the 40-pin header/extender",
        "vcc": "Module VCC to Pi physical pin 1 or 17, 3.3V only",
        "do_not_wire_to": ["5V", "raw battery", "ESP32 GPIO", "Heltec GPIO", "Pi RUN/reset pads without a separate documented reset circuit"],
        "debounce_seconds_default": 0.05,
        "buttons": DEFAULT_BUTTONS,
        "wiring_summary": [
            "Use K1-K8 left-to-right across the button board.",
            "K1-K6 replace the previous six separate tactile buttons.",
            "K7 is the Power On/Off position and requests safe software shutdown.",
            "K8 is the Reset / Reboot position and requests safe software reboot.",
            "gpiozero Button(..., pull_up=True) enables the Raspberry Pi internal pull-up resistor.",
            "Idle/not pressed reads HIGH; pressed reads LOW.",
        ],
        "failure_fallback": {
            "mode": "touch_speech_only",
            "touch_enabled": True,
            "speech_enabled": True,
            "keyboard_enabled": True,
            "gpio_buttons_enabled": False,
            "installer_continues": True,
            "strict_override": "Set STRICT_GPIO_BUTTONS=1 only when a GPIO button failure should stop flashing.",
        },
        "power_on_note": "A GPIO key can request a runtime power action while the Pi is running. True power-on from a fully unpowered Pi needs a supported power-control board or the battery bank control.",
        "reset_note": "K8 is a software reboot request. Do not wire it to raw power, 5V, ESP32 GPIO, Heltec GPIO, or Pi RUN/reset pads without a separate documented reset circuit.",
    }


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _strict() -> bool:
    return os.environ.get("STRICT_GPIO_BUTTONS", "0") in {"1", "true", "True", "yes", "YES", "on", "ON"}


def running_on_raspberry_pi() -> bool:
    for path in (Path("/proc/device-tree/model"), Path("/sys/firmware/devicetree/base/model")):
        try:
            if "raspberry pi" in path.read_text(encoding="utf-8", errors="ignore").lower():
                return True
        except Exception:
            pass
    return False


def _start_manager_for_probe(log_path: str) -> GPIOButtonManager:
    # A previous fallback must not block a recovery probe after wiring is repaired.
    previous = os.environ.get("KOALABYTE_CONTROL_MODE")
    os.environ["KOALABYTE_CONTROL_MODE"] = "auto"
    manager = GPIOButtonManager(log_path=log_path)
    try:
        manager.start()
    finally:
        if previous is None:
            os.environ.pop("KOALABYTE_CONTROL_MODE", None)
        else:
            os.environ["KOALABYTE_CONTROL_MODE"] = previous
    return manager


def run_probe(status_path: Path) -> int:
    manager = _start_manager_for_probe("logs/gpio_buttons/gpio_button_probe_events.jsonl")
    try:
        if manager.available:
            control = write_control_mode(
                "full_controls",
                reason="K1-K8 GPIO inputs initialized successfully during installer probe.",
                source="setup_gpio_buttons_probe",
                buttons_available=True,
            )
            status: Dict[str, Any] = {
                "status": "GPIO_8KEY_BUTTON_BOARD_PROBE_READY",
                "gpio_initialized": True,
                "button_press_required": False,
                "control_mode": control,
                "updated_at": time.time(),
            }
            write_json(status_path, status)
            print(json.dumps(status, sort_keys=True))
            return 0

        reason = manager.error or "K1-K8 GPIO inputs could not initialize"
        control = write_control_mode(
            "touch_speech_only",
            reason=reason,
            source="setup_gpio_buttons_probe",
            buttons_available=False,
            extra={"installer_continues": not _strict()},
        )
        status = {
            "status": "GPIO_BUTTONS_UNAVAILABLE_TOUCH_SPEECH_ONLY",
            "gpio_initialized": False,
            "error": reason,
            "control_mode": control,
            "installer_continues": not _strict(),
            "strict_gpio_buttons": _strict(),
            "updated_at": time.time(),
        }
        write_json(status_path, status)
        print(json.dumps(status, sort_keys=True))
        return 1 if _strict() else 0
    finally:
        manager.close()


def run_live_test(seconds: float, status_path: Path) -> int:
    manager = _start_manager_for_probe("logs/gpio_buttons/gpio_button_events.jsonl")
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
        reason = manager.error or "GPIO button board unavailable"
        control = write_control_mode(
            "touch_speech_only",
            reason=reason,
            source="setup_gpio_buttons_live_test",
            buttons_available=False,
            extra={"installer_continues": not _strict()},
        )
        status.update({
            "status": "GPIO_BUTTONS_UNAVAILABLE_TOUCH_SPEECH_ONLY",
            "error": reason,
            "control_mode": control,
            "installer_continues": not _strict(),
        })
        write_json(status_path, status)
        return 1 if _strict() else 0

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
        control = write_control_mode(
            "full_controls",
            reason="GPIO live test initialized successfully. Button-event count is recorded separately.",
            source="setup_gpio_buttons_live_test",
            buttons_available=True,
            extra={"observed_button_events": len(status["events"])},
        )
        status["status"] = "GPIO_8KEY_BUTTON_BOARD_LIVE_TEST_COMPLETE"
        status["finished_at"] = time.time()
        status["control_mode"] = control
        status["note"] = "Zero button events does not prove the passive board is disconnected; press each key during a live test to verify wiring."
        write_json(status_path, status)
        return 0
    finally:
        manager.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare/check KoalaByte Blue 8-key GPIO front-panel button board.")
    parser.add_argument("--manifest-path", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--status-path", default=str(DEFAULT_STATUS_PATH))
    parser.add_argument("--check-only", action="store_true", help="Write/validate the manifest and, on a Raspberry Pi, perform a non-interactive GPIO initialization probe.")
    parser.add_argument("--probe", action="store_true", help="Force a non-interactive GPIO initialization probe without requiring a button press.")
    parser.add_argument("--live-test", action="store_true", help="Initialize gpiozero buttons and watch for button events.")
    parser.add_argument("--seconds", type=float, default=10.0, help="Live-test duration.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest_path)
    status_path = Path(args.status_path)
    manifest = build_manifest()
    write_json(manifest_path, manifest)

    if args.live_test:
        return run_live_test(args.seconds, status_path)
    if args.probe or (args.check_only and running_on_raspberry_pi()):
        return run_probe(status_path)

    status: Dict[str, Any] = {
        "status": "GPIO_8KEY_BUTTON_BOARD_MANIFEST_READY",
        "manifest_path": str(manifest_path),
        "running_on_raspberry_pi": running_on_raspberry_pi(),
        "gpio_probe_performed": False,
        "control_mode": load_control_mode(),
        "note": "Non-Pi/check environment: hardware probe skipped; runtime keeps automatic GPIO detection enabled.",
        "updated_at": time.time(),
    }
    write_json(status_path, status)
    print(json.dumps(status, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
