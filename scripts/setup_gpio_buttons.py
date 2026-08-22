#!/usr/bin/env python3
"""Prepare/check KoalaByte Blue front-panel GPIO button board.

Default hardware is a GODIYMODULES MOD-ST034-1 / ASIN B0FH9C88DJ
8-key module with header pins VCC, GND, and K1-K8. On a Raspberry Pi,
check-only also performs a non-interactive GPIO initialization probe. The
one-shot probe automatically creates a persistent K1-K8 runtime map before
GPIO initialization. If the button GPIO stack cannot initialize, the installer
records touch_speech_only mode and continues unless STRICT_GPIO_BUTTONS=1 is
explicitly set.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

from koalablue.control_mode import load_control_mode, write_control_mode
from koalablue.gpio_buttons import (
    DEFAULT_BUTTONS,
    DEFAULT_BUTTON_MAP_PATH,
    DEFAULT_ELECTRICAL_MODE,
    GPIOButtonManager,
    validate_button_map,
)

DEFAULT_MANIFEST_PATH = Path("logs/gpio_buttons/gpio_button_manifest.json")
DEFAULT_STATUS_PATH = Path("logs/gpio_buttons/gpio_button_status.json")

BCM_TO_PHYSICAL = {
    2: 3,
    3: 5,
    4: 7,
    14: 8,
    15: 10,
    17: 11,
    18: 12,
    27: 13,
    22: 15,
    23: 16,
    24: 18,
    10: 19,
    9: 21,
    25: 22,
    11: 23,
    8: 24,
    7: 26,
    0: 27,
    1: 28,
    5: 29,
    6: 31,
    12: 32,
    13: 33,
    19: 35,
    16: 36,
    26: 37,
    20: 38,
    21: 40,
}


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
        "auto_mapping": {
            "enabled_during_one_shot_probe": True,
            "runtime_map_path": str(DEFAULT_BUTTON_MAP_PATH),
            "default_source": "production K1-K8 wiring",
            "per_key_override_environment": [f"KOALABYTE_K{i}_BCM" for i in range(1, 9)],
            "invalid_or_missing_map_behavior": "regenerate/return to validated production defaults",
            "k7_k8_protection_locked": True,
        },
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


def _requested_pin_overrides() -> Dict[str, int]:
    overrides: Dict[str, int] = {}
    for number in range(1, 9):
        key = f"K{number}"
        env_name = f"KOALABYTE_{key}_BCM"
        raw = os.environ.get(env_name, "").strip()
        if not raw:
            continue
        try:
            pin = int(raw, 10)
        except ValueError as exc:
            raise ValueError(f"{env_name} must be a Raspberry Pi BCM GPIO number, got {raw!r}") from exc
        if pin not in BCM_TO_PHYSICAL:
            raise ValueError(f"{env_name}={pin} is not a supported 40-pin Raspberry Pi GPIO")
        overrides[key] = pin
    return overrides


def _build_mapped_buttons(overrides: Dict[str, int]) -> Dict[str, Dict[str, object]]:
    buttons: Dict[str, Dict[str, object]] = {
        name: dict(cfg) for name, cfg in DEFAULT_BUTTONS.items()
    }
    for cfg in buttons.values():
        number = int(cfg["number"])
        key = f"K{number}"
        if key not in overrides:
            continue
        pin = overrides[key]
        cfg["pin"] = pin
        cfg["physical_pin"] = BCM_TO_PHYSICAL[pin]
    validate_button_map(buttons)
    return buttons


def prepare_auto_map(map_path: Path, *, force: bool = False) -> Dict[str, Any]:
    """Create or preserve the persistent K1-K8 map consumed by GPIOButtonManager."""
    overrides = _requested_pin_overrides()

    if map_path.exists() and not force and not overrides:
        try:
            payload = json.loads(map_path.read_text(encoding="utf-8"))
            buttons = payload.get("buttons", payload)
            if not isinstance(buttons, dict):
                raise ValueError("existing map does not contain a buttons object")
            normalized = {
                str(name): dict(cfg)
                for name, cfg in buttons.items()
                if isinstance(cfg, dict)
            }
            validate_button_map(normalized)
            return {
                **payload,
                "status": "K1_K8_AUTO_MAP_PRESERVED",
                "map_path": str(map_path),
                "buttons": normalized,
                "updated_at": time.time(),
            }
        except Exception:
            # An invalid generated map is replaced by the locked production-safe map.
            pass

    buttons = _build_mapped_buttons(overrides)
    payload: Dict[str, Any] = {
        "status": "K1_K8_AUTO_MAP_READY",
        "mapping_version": 1,
        "map_path": str(map_path),
        "source": "environment_overrides" if overrides else "production_defaults",
        "overrides": overrides,
        "electrical_mode": {
            "pull_up": DEFAULT_ELECTRICAL_MODE.pull_up,
            "idle_state": DEFAULT_ELECTRICAL_MODE.idle_state,
            "pressed_state": DEFAULT_ELECTRICAL_MODE.pressed_state,
        },
        "buttons": buttons,
        "protected_buttons": {
            "K7": {"command": "power_toggle", "hold_seconds": 2.5},
            "K8": {"command": "reset", "hold_seconds": 3.0},
        },
        "updated_at": time.time(),
    }
    write_json(map_path, payload)
    return payload


def running_on_raspberry_pi() -> bool:
    for path in (Path("/proc/device-tree/model"), Path("/sys/firmware/devicetree/base/model")):
        try:
            if "raspberry pi" in path.read_text(encoding="utf-8", errors="ignore").lower():
                return True
        except Exception:
            pass
    return False


def _start_manager_for_probe(log_path: str, map_path: Path) -> GPIOButtonManager:
    # A previous fallback must not block a recovery probe after wiring is repaired.
    previous_mode = os.environ.get("KOALABYTE_CONTROL_MODE")
    previous_map = os.environ.get("KOALABYTE_GPIO_BUTTON_MAP")
    os.environ["KOALABYTE_CONTROL_MODE"] = "auto"
    os.environ["KOALABYTE_GPIO_BUTTON_MAP"] = str(map_path)
    manager = GPIOButtonManager(log_path=log_path)
    try:
        manager.start()
    finally:
        if previous_mode is None:
            os.environ.pop("KOALABYTE_CONTROL_MODE", None)
        else:
            os.environ["KOALABYTE_CONTROL_MODE"] = previous_mode
        if previous_map is None:
            os.environ.pop("KOALABYTE_GPIO_BUTTON_MAP", None)
        else:
            os.environ["KOALABYTE_GPIO_BUTTON_MAP"] = previous_map
    return manager


def run_probe(status_path: Path, map_path: Path, mapping: Dict[str, Any]) -> int:
    manager = _start_manager_for_probe("logs/gpio_buttons/gpio_button_probe_events.jsonl", map_path)
    try:
        if manager.available:
            control = write_control_mode(
                "full_controls",
                reason="K1-K8 GPIO inputs initialized successfully during installer probe using the persistent auto-map.",
                source="setup_gpio_buttons_probe",
                buttons_available=True,
                extra={"button_map_path": str(map_path)},
            )
            status: Dict[str, Any] = {
                "status": "GPIO_8KEY_BUTTON_BOARD_PROBE_READY",
                "gpio_initialized": True,
                "button_press_required": False,
                "button_map_path": str(map_path),
                "button_map_status": mapping.get("status"),
                "button_map_source": mapping.get("source", "preserved"),
                "buttons": mapping.get("buttons", {}),
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
            extra={
                "installer_continues": not _strict(),
                "button_map_path": str(map_path),
            },
        )
        status = {
            "status": "GPIO_BUTTONS_UNAVAILABLE_TOUCH_SPEECH_ONLY",
            "gpio_initialized": False,
            "error": reason,
            "button_map_path": str(map_path),
            "button_map_status": mapping.get("status"),
            "button_map_source": mapping.get("source", "preserved"),
            "buttons": mapping.get("buttons", {}),
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


def run_live_test(seconds: float, status_path: Path, map_path: Path, mapping: Dict[str, Any]) -> int:
    manager = _start_manager_for_probe("logs/gpio_buttons/gpio_button_events.jsonl", map_path)
    started_at = time.time()
    status: Dict[str, Any] = {
        "status": "GPIO_8KEY_BUTTON_BOARD_LIVE_TEST_STARTED",
        "started_at": started_at,
        "seconds": seconds,
        "internal_pull_up_enabled": DEFAULT_ELECTRICAL_MODE.pull_up,
        "not_pressed_raw_level": DEFAULT_ELECTRICAL_MODE.idle_state,
        "pressed_raw_level": DEFAULT_ELECTRICAL_MODE.pressed_state,
        "button_map_path": str(map_path),
        "button_map_status": mapping.get("status"),
        "button_map_source": mapping.get("source", "preserved"),
        "events": [],
    }

    if not manager.available:
        reason = manager.error or "GPIO button board unavailable"
        control = write_control_mode(
            "touch_speech_only",
            reason=reason,
            source="setup_gpio_buttons_live_test",
            buttons_available=False,
            extra={"installer_continues": not _strict(), "button_map_path": str(map_path)},
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
            extra={
                "observed_button_events": len(status["events"]),
                "button_map_path": str(map_path),
            },
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
    parser.add_argument("--map-path", default=str(DEFAULT_BUTTON_MAP_PATH), help="Persistent K1-K8 runtime map written/validated by the installer.")
    parser.add_argument("--auto-map", action="store_true", help="Force regeneration of the K1-K8 map from production defaults plus KOALABYTE_K1_BCM..KOALABYTE_K8_BCM overrides.")
    parser.add_argument("--check-only", action="store_true", help="Write/validate the manifest and K1-K8 map and, on a Raspberry Pi, perform a non-interactive GPIO initialization probe.")
    parser.add_argument("--probe", action="store_true", help="Force a non-interactive GPIO initialization probe without requiring a button press. The map is created automatically first.")
    parser.add_argument("--live-test", action="store_true", help="Initialize gpiozero buttons from the persistent map and watch for button events.")
    parser.add_argument("--seconds", type=float, default=10.0, help="Live-test duration.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest_path)
    status_path = Path(args.status_path)
    map_path = Path(args.map_path)
    manifest = build_manifest()
    write_json(manifest_path, manifest)

    try:
        mapping = prepare_auto_map(map_path, force=args.auto_map)
    except Exception as exc:
        status = {
            "status": "GPIO_K1_K8_AUTO_MAP_ERROR",
            "error": str(exc),
            "button_map_path": str(map_path),
            "strict_gpio_buttons": _strict(),
            "updated_at": time.time(),
        }
        write_json(status_path, status)
        print(json.dumps(status, sort_keys=True))
        return 1

    if args.live_test:
        return run_live_test(args.seconds, status_path, map_path, mapping)
    if args.probe or (args.check_only and running_on_raspberry_pi()):
        return run_probe(status_path, map_path, mapping)

    status: Dict[str, Any] = {
        "status": "GPIO_8KEY_BUTTON_BOARD_MANIFEST_READY",
        "manifest_path": str(manifest_path),
        "button_map_path": str(map_path),
        "button_map_status": mapping.get("status"),
        "button_map_source": mapping.get("source", "preserved"),
        "buttons": mapping.get("buttons", {}),
        "running_on_raspberry_pi": running_on_raspberry_pi(),
        "gpio_probe_performed": False,
        "control_mode": load_control_mode(),
        "note": "K1-K8 map is ready. Non-Pi/check environment: hardware probe skipped; runtime keeps automatic GPIO detection enabled.",
        "updated_at": time.time(),
    }
    write_json(status_path, status)
    print(json.dumps(status, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
