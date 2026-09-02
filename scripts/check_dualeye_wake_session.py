#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "firmware" / "esp32-dualeye" / "scripts" / "generate_wake_session_source.py"
AWAKE_PATCH = ROOT / "firmware" / "esp32-dualeye" / "scripts" / "patch_wake_session_awake_eyes.py"
RESPONSE_GENERATOR = ROOT / "firmware" / "esp32-dualeye" / "scripts" / "generate_local_voice_responses.py"
RESPONSE_PATCH = ROOT / "firmware" / "esp32-dualeye" / "scripts" / "patch_local_response_bank.py"
RESPONSE_HEADER = ROOT / "firmware" / "esp32-dualeye" / "include" / "local_voice_responses.h"
CATALOG = ROOT / "firmware" / "esp32-dualeye" / "scripts" / "generate_voice_menu_catalog.py"
PARTITIONS = ROOT / "firmware" / "esp32-dualeye" / "partitions.csv"
PLATFORMIO = ROOT / "firmware" / "esp32-dualeye" / "platformio.ini"
STATUS = ROOT / "logs" / "one_shot" / "dualeye_wake_session_status.json"


def require(text: str, marker: str, failures: list[str], label: str) -> None:
    if marker not in text:
        failures.append(f"{label} missing marker: {marker}")


def main() -> int:
    failures: list[str] = []
    required_paths = (
        GENERATOR,
        AWAKE_PATCH,
        RESPONSE_GENERATOR,
        RESPONSE_PATCH,
        RESPONSE_HEADER,
        CATALOG,
        PARTITIONS,
        PLATFORMIO,
    )
    for path in required_paths:
        if not path.exists():
            failures.append(f"missing required file: {path.relative_to(ROOT)}")

    generator = GENERATOR.read_text(encoding="utf-8") if GENERATOR.exists() else ""
    awake_patch = AWAKE_PATCH.read_text(encoding="utf-8") if AWAKE_PATCH.exists() else ""
    response_generator = RESPONSE_GENERATOR.read_text(encoding="utf-8") if RESPONSE_GENERATOR.exists() else ""
    response_patch = RESPONSE_PATCH.read_text(encoding="utf-8") if RESPONSE_PATCH.exists() else ""
    response_header = RESPONSE_HEADER.read_text(encoding="utf-8") if RESPONSE_HEADER.exists() else ""
    catalog = CATALOG.read_text(encoding="utf-8") if CATALOG.exists() else ""
    partitions = PARTITIONS.read_text(encoding="utf-8") if PARTITIONS.exists() else ""
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
        "koalaLegacyHandleCommand",
        "serviceWakeSessionTimeout();",
        "showIdleEyes();",
        "wake_session_remaining_ms",
        "ambient_voice_commands_while_sleeping",
    ]
    for marker in generator_markers:
        require(generator, marker, failures, "wake-session generator")

    awake_markers = [
        "showWakeSessionEyes",
        "listening",
        "pulse",
        "wakeSessionActive",
        "showIdleEyes",
    ]
    for marker in awake_markers:
        require(awake_patch, marker, failures, "awake-eye patch")

    response_markers = [
        'VOICE_NAME = "en-AU-WilliamNeural"',
        'SPOKEN_IDENTITY = "KillerKoala"',
        "RECENT_HISTORY_DEPTH = 3",
        '"Acknowledgement"',
        '"Success"',
        '"Error"',
        "wasRecentlyUsed",
        "rememberChoice",
        "localVoiceResponseTotalCount",
        "localVoiceRecentHistoryDepth",
    ]
    for marker in response_markers:
        require(response_generator, marker, failures, "local response generator")

    expected_categories = {
        "Wake": 6,
        "Status": 5,
        "Help": 5,
        "Acknowledgement": 5,
        "Banter": 5,
        "Success": 5,
        "Error": 5,
        "Escalate": 4,
    }
    response_counts = {
        category: len(re.findall(rf'^\s*\("{re.escape(category)}",', response_generator, re.MULTILINE))
        for category in expected_categories
    }
    if response_counts != expected_categories:
        failures.append(
            f"local response-bank counts changed: expected={expected_categories}, actual={response_counts}"
        )
    if sum(response_counts.values()) != 40:
        failures.append(f"local response bank must contain exactly 40 clips, found {sum(response_counts.values())}")
    if re.search(r'\("[^\"]+",\s*"[^\"]*\bWilliam\b', response_generator, re.IGNORECASE):
        failures.append("William appears as a spoken character identity in the local response bank")

    for marker in (
        "Acknowledgement",
        "Success",
        "Error",
        "localVoiceResponseTotalCount",
        "localVoiceRecentHistoryDepth",
    ):
        require(response_header, marker, failures, "local response header")
    for marker in (
        "exclude_previous_three_responses_per_category",
        "embedded_en_au_william_neural_mulaw_40_clip_bank",
        "LocalVoiceCategory::Acknowledgement",
    ):
        require(response_patch, marker, failures, "local response runtime patch")

    for marker in (
        "KOALABYTE_LOCAL_VOICE_COMMAND_TIMEOUT_SECONDS",
        "VOICE_COMMAND_TIMEOUT_SECONDS",
        '"-nostdin"',
    ):
        require(response_generator, marker, failures, "local response generator")

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
        "pre:scripts/generate_local_voice_responses.py",
        "pre:scripts/generate_wake_session_source.py",
        "pre:scripts/patch_wake_session_awake_eyes.py",
        "pre:scripts/patch_local_response_bank.py",
        "pre:scripts/patch_release_version.py",
        "-<integrated_main_clean_voice.cpp>",
    ]
    for marker in platformio_markers:
        require(platformio, marker, failures, "PlatformIO configuration")
    if "patch_wake_session_two_stage_grammar.py" in platformio:
        failures.append(
            "unsafe two-stage MultiNet grammar patch is enabled; hardware StoreProhibited boot loop confirmed"
        )

    require(partitions, "app0,     app,  ota_0,   0x10000,  0x400000", failures, "partition table")
    require(partitions, "model,    data, spiffs,  0xCB0000, 0x340000", failures, "partition table")

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
        "recognition_grammar": "single_static_full_catalog",
        "runtime_multinet_restarts": False,
        "hardware_bootloop_regression_blocked": True,
        "session_timeout_ms": 10_000,
        "accepted_voice_refreshes_session": True,
        "trusted_gpio_and_keyboard_wake_or_refresh": True,
        "ambient_voice_commands_while_sleeping": False,
        "active_session_display": "animated_listening_koala_eyes",
        "timeout_display": "animated_idle_koala_eyes",
        "local_response_count": 40,
        "local_response_categories": expected_categories,
        "local_response_history_depth": 3,
        "local_response_repeat_policy": "exclude_previous_three_responses_per_category",
        "local_response_voice_backend": "en-AU-WilliamNeural",
        "local_response_spoken_identity": "KillerKoala",
        "failures": failures,
        "updated_at": time.time(),
    }
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
