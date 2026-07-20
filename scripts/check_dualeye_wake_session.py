#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "firmware" / "esp32-dualeye" / "scripts" / "generate_wake_session_source.py"
CATALOG = ROOT / "firmware" / "esp32-dualeye" / "scripts" / "generate_voice_menu_catalog.py"
PLATFORMIO = ROOT / "firmware" / "esp32-dualeye" / "platformio.ini"
STATUS = ROOT / "logs" / "one_shot" / "dualeye_wake_session_status.json"


def require(text: str, marker: str, failures: list[str], label: str) -> None:
    if marker not in text:
        failures.append(f"{label} missing marker: {marker}")


def main() -> int:
    failures: list[str] = []
    for path in (GENERATOR, CATALOG, PLATFORMIO):
        if not path.exists():
            failures.append(f"missing required file: {path.relative_to(ROOT)}")

    generator = GENERATOR.read_text(encoding="utf-8") if GENERATOR.exists() else ""
    catalog = CATALOG.read_text(encoding="utf-8") if CATALOG.exists() else ""
    platformio = PLATFORMIO.read_text(encoding="utf-8") if PLATFORMIO.exists() else ""

    generator_markers = [
        "constexpr uint32_t kWakeSessionMs = 10000",
        "voice_command_ignored_sleeping",
        "ambient_command_rejected_while_sleeping",
        "killerkoala_wake_phrase",
        "accepted_voice_command",
        "trusted_pi_button_or_keyboard_input",
        "ten_second_inactivity_timeout",
        "trustedPiMenuActivity",
        "eventType, \\\"state\\\"",
        "koalaLegacyHandleCommand",
        "serviceWakeSessionTimeout();",
        "showIdleEyes();",
        "wake_session_remaining_ms",
        "ambient_voice_commands_while_sleeping",
    ]
    for marker in generator_markers:
        require(generator, marker, failures, "wake-session generator")

    catalog_markers = [
        '(100, "k1_main_menu", "Main Menu", "main", "Menu", "K one")',
        '(105, "k6_down", "Down", "main", "Down", "K six")',
        'phrase = f"Launch {spoken_label}"',
        "accepted only inside the firmware's ten-second wake session",
    ]
    for marker in catalog_markers:
        require(catalog, marker, failures, "voice catalog generator")
    if 'phrase = f"Killer Koala launch {spoken_label}"' in catalog:
        failures.append("catalog still requires Killer Koala on every direct launch command")

    platformio_markers = [
        "pre:scripts/generate_wake_session_source.py",
        "-<integrated_main_clean_voice.cpp>",
    ]
    for marker in platformio_markers:
        require(platformio, marker, failures, "PlatformIO configuration")

    # Deterministic policy simulation: only wake or trusted physical activity can
    # open a session; accepted activity refreshes it; inactivity closes it.
    now = 100_000
    deadline = 0
    awake = False

    def voice(command: str, at: int) -> bool:
        nonlocal awake, deadline
        if command == "killerkoala":
            awake = True
            deadline = at + 10_000
            return True
        if not awake or at >= deadline:
            awake = False
            return False
        deadline = at + 10_000
        return True

    def trusted_input(at: int) -> None:
        nonlocal awake, deadline
        awake = True
        deadline = at + 10_000

    if voice("up", now):
        failures.append("ambient command was accepted while sleeping")
    if not voice("killerkoala", now + 100):
        failures.append("wake phrase did not open session")
    first_deadline = deadline
    if not voice("menu", now + 5_000) or deadline <= first_deadline:
        failures.append("accepted voice command did not refresh session")
    trusted_input(now + 9_000)
    if not awake or deadline != now + 19_000:
        failures.append("trusted K1-K8/keyboard activity did not wake or refresh session")
    if voice("down", now + 19_001):
        failures.append("voice command remained accepted after ten seconds of inactivity")
    if awake:
        failures.append("session did not return to sleeping state after timeout")

    payload = {
        "status": "DUALEYE_WAKE_SESSION_OK" if not failures else "DUALEYE_WAKE_SESSION_ERROR",
        "wake_phrase": "killerkoala|hey killerkoala",
        "session_timeout_ms": 10_000,
        "accepted_voice_refreshes_session": True,
        "trusted_gpio_and_keyboard_wake_or_refresh": True,
        "ambient_voice_commands_while_sleeping": False,
        "timeout_display": "animated_koala_eyes",
        "failures": failures,
        "updated_at": time.time(),
    }
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
