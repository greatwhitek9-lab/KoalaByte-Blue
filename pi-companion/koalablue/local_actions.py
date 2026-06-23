from __future__ import annotations

import json
import platform
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

LOG_DIR = Path("logs/local_actions")


@dataclass(frozen=True)
class LocalActionResult:
    action: str
    status: str
    timestamp: float
    artifact_path: str
    payload: Dict[str, Any]


def _write(action: str, payload: Dict[str, Any]) -> LocalActionResult:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"{action}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    result = LocalActionResult(action=action, status="success", timestamp=time.time(), artifact_path=str(path), payload=payload)
    path.write_text(json.dumps(asdict(result), indent=2, sort_keys=True), encoding="utf-8")
    return result


def koala_kapture() -> LocalActionResult:
    payload = {
        "title": "Koala Kapture",
        "purpose": "Create a local authorized observation capture marker for the current KoalaByte session.",
        "captures_rf": False,
        "pairs_with_devices": False,
        "writes_to_devices": False,
        "next_steps": [
            "Run Eucalyptus or BlueZ inventory for passive observations.",
            "Attach notes and reports to this session marker.",
            "Keep work limited to owned devices or written-scope lab systems.",
        ],
    }
    return _write("koala_kapture", payload)


def urban_poaching() -> LocalActionResult:
    payload = {
        "title": "Urban Poaching",
        "purpose": "Authorized BLE RSSI lab-game/session marker for finding your own tagged devices.",
        "scope": "owned devices or written permission only",
        "captures_rf": False,
        "active_transmit": False,
        "recommended_safe_inputs": ["local BLE inventory", "Eucalyptus passive observations", "operator notes"],
    }
    return _write("urban_poaching", payload)


def settings() -> LocalActionResult:
    payload = {
        "title": "KoalaByte Settings Snapshot",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "paths": {
            "logs": "logs/",
            "menu_actions": "logs/menu_actions/",
            "local_actions": str(LOG_DIR),
            "t114_profile_state": "logs/t114_profiles/startup_selection.json",
        },
        "environment_keys": [
            "KOALABYTE_HELTEC_USB_PORT",
            "KOALABYTE_ESP32_FACE_PORT",
            "T114_STARTUP_MODE",
            "T114_STARTUP_DEFAULT_MODE",
            "KOALABYTE_TTS",
            "CAN_INTERFACE",
        ],
    }
    return _write("settings", payload)


def buttons() -> LocalActionResult:
    mapping: List[Dict[str, Any]] = [
        {"button": "B1", "command": "main_menu", "purpose": "Return/open main menu"},
        {"button": "B2", "command": "left/back", "purpose": "Back or previous"},
        {"button": "B3", "command": "select", "purpose": "Select highlighted item"},
        {"button": "B4", "command": "right/forward", "purpose": "Move right/forward"},
        {"button": "B5", "command": "up", "purpose": "Move selection up"},
        {"button": "B6", "command": "down", "purpose": "Move selection down"},
    ]
    payload = {
        "title": "KoalaByte Button Map",
        "mapping": mapping,
        "touchscreen": {"long_press": "select", "drag": "scroll"},
        "gpio_note": "Buttons are expected to be momentary switches to GND with Pi internal pull-ups; GPIO is 3.3 V only.",
    }
    return _write("buttons", payload)


def run_cli(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="KoalaByte local-only menu helper actions")
    parser.add_argument("action", choices=["koala-kapture", "urban-poaching", "settings", "buttons"])
    args = parser.parse_args(argv)
    if args.action == "koala-kapture":
        result = koala_kapture()
    elif args.action == "urban-poaching":
        result = urban_poaching()
    elif args.action == "settings":
        result = settings()
    else:
        result = buttons()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0
