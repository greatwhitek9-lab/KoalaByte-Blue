#!/usr/bin/env python3
"""Validate the Raspberry Pi OS Lite runtime dependency contract."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
STATUS_PATH = ROOT / "logs" / "one_shot" / "full_runtime_dependencies.json"
VENV_BIN = PI_ROOT / ".venv" / "bin"

for path in (ROOT, PI_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

REQUIRED_PYTHON_IMPORT_GROUPS: dict[str, tuple[str, ...]] = {
    "core_serial_ble": ("serial", "bleak"),
    "menu_and_gpio": ("rich", "pydantic", "pygame", "gpiozero"),
    "api_services": ("fastapi", "uvicorn", "requests", "httpx"),
    "voice_ai": ("pyttsx3", "speech_recognition", "pocketsphinx"),
}
OPTIONAL_PYTHON_IMPORT_GROUPS: dict[str, tuple[str, ...]] = {
    "optional_can_runtime": ("can",),
    "optional_obd_review": ("obd",),
}

PROJECT_MODULES = (
    "koalablue.bounded_log",
    "koalablue.serial_command_bus",
    "koalablue.runtime_serial_ownership",
    "koalablue.gpio_buttons",
    "koalablue.menu_catalog",
    "koalablue.menu_ui",
    "koalablue.menu_theme",
    "koalablue.menu_action_runner",
    "koalablue.menu_display_sync",
    "koalablue.dualeye_tts",
    "koalablue.killerkoala_hybrid_companion",
    "koalablue.killerkoala_face_bridge",
    "koalablue.esp32_dualeye_latched_koalagotchi_bridge",
    "koalablue.esp32_dualeye_error_dig_bridge",
    "koalablue.ble_node_manager",
    "koalablue.t114_bluez",
    "koalablue.gnss_location",
    "koalablue.meshtastic_app",
    "koalablue.koala_kan_kommander",
)

CURRENT_RUNTIME_FILES = (
    "install.sh",
    "one-shot-install.sh",
    "scripts/run_headless_menu.py",
    "scripts/run_ble_node_manager.py",
    "scripts/run_esp32_dualeye_voice_bridge.py",
    "scripts/setup_pi_hardware_stage.sh",
    "scripts/setup_system_packages.sh",
    "scripts/setup_killerkoala_ollama.sh",
    "scripts/setup_mopidy_player.sh",
    "scripts/setup_gpio_buttons.py",
    "scripts/test_gpio_buttons.py",
    "scripts/pi_hardware_doctor.py",
    "scripts/discover_koalabyte_ports.py",
    "scripts/install_power_controls.sh",
    "scripts/install_koalabyte_udev_rules.sh",
    "scripts/install_koalabyte_boot_services.sh",
    "scripts/install_runtime_log_rotation.sh",
    "scripts/install_ble_node_manager_service.sh",
    "scripts/install_esp32_dualeye_voice_bridge_service.sh",
    "scripts/provision_esp32_wifi_env.sh",
    "scripts/configure_pi_audio_output.sh",
    "scripts/configure_shared_alsa_output.sh",
    "scripts/check_serial_command_bus.py",
    "scripts/check_confirmed_wake_audio.py",
    "scripts/check_live_runtime_services.py",
    "scripts/check_one_shot_controls.py",
    "scripts/check_menu_actions.py",
    "scripts/check_menu_display_sync.py",
    "scripts/check_killerkoala_face_mouth_sync.py",
    "training/killerkoala_lora/Modelfile.killerkoala-tinyllama",
    "systemd/koalabyte-menu.service",
    "systemd/koalabyte-doctor.service",
    "udev/99-koalabyte-blue.rules",
)

CURRENT_FIRMWARE_SOURCE_FILES = (
    "firmware/esp32-dualeye/platformio.ini",
    "firmware/esp32-dualeye/include/config.h",
    "firmware/esp32-dualeye/src/integrated_main.cpp",
    "firmware/esp32-dualeye/src/integrated_main_wake_session.cpp",
    "firmware/esp32-dualeye/scripts/patch_complex_capture_preroll.py",
    "firmware/t114-combined-safe/CMakeLists.txt",
    "firmware/t114-combined-safe/prj.conf",
    "firmware/t114-combined-safe/src/main.c",
    "firmware/t114-combined-safe/src/original_texture_warp_renderer.c",
)

CORE_COMMANDS = ("python3", "git")
PI_RUNTIME_COMMANDS = (
    "ip",
    "lsusb",
    "udevadm",
    "bluetoothctl",
    "rfkill",
    "aplay",
    "arecord",
    "ffmpeg",
    "espeak-ng",
)
REQUIRED_PI_RUNTIME_COMMANDS = {
    "ip",
    "lsusb",
    "udevadm",
    "bluetoothctl",
    "rfkill",
    "aplay",
    "ffmpeg",
    "espeak-ng",
}
OPTIONAL_COMMAND_GROUPS: dict[str, tuple[str, ...]] = {
    "socketcan": ("modprobe", "candump", "cansend"),
    "pipewire_pulseaudio": ("wpctl", "pactl"),
    "firmware_source_build": ("cmake", "ninja", "west", "pio"),
    "packet_review": ("tshark", "wireshark"),
}


def command_path(command: str) -> str | None:
    found = shutil.which(command)
    if found:
        return found
    candidate = VENV_BIN / command
    return str(candidate) if candidate.exists() else None


def inspect_import_groups(
    groups: dict[str, tuple[str, ...]],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    results: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for group, modules in groups.items():
        group_results: dict[str, Any] = {}
        for module in modules:
            try:
                imported = importlib.import_module(module)
                version = getattr(imported, "__version__", None)
                group_results[module] = {
                    "available": True,
                    "version": str(version) if version else None,
                }
            except Exception as exc:
                group_results[module] = {"available": False, "error": str(exc)}
                missing.append(f"{group}:{module} ({exc})")
        results[group] = group_results
    return results, missing


def project_import_checks() -> tuple[dict[str, Any], list[str]]:
    results: dict[str, Any] = {}
    failures: list[str] = []
    for module in PROJECT_MODULES:
        try:
            importlib.import_module(module)
            results[module] = {"available": True}
        except Exception as exc:
            results[module] = {"available": False, "error": str(exc)}
            failures.append(f"current project module import failed: {module} ({exc})")
    return results, failures


def file_checks(
    paths: tuple[str, ...], label: str
) -> tuple[dict[str, bool], list[str]]:
    results: dict[str, bool] = {}
    failures: list[str] = []
    for relative in paths:
        present = (ROOT / relative).exists()
        results[relative] = present
        if not present:
            failures.append(f"missing current {label} file: {relative}")
    return results, failures


def command_checks(commands: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    return {
        command: {
            "available": command_path(command) is not None,
            "path": command_path(command),
        }
        for command in commands
    }


def can_required() -> bool:
    value = os.getenv("INSTALL_INNOMAKER_CAN", "auto").strip().lower()
    return value in {"1", "true", "yes", "on", "required"}


def import_available(
    results: dict[str, dict[str, Any]], group: str, module: str
) -> bool:
    return bool(results.get(group, {}).get(module, {}).get("available"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check current KoalaByte Pi OS Lite runtime dependencies"
    )
    parser.add_argument(
        "--strict-system",
        "--strict-commands",
        dest="strict_system",
        action="store_true",
        help="Promote optional host warnings to failures",
    )
    args = parser.parse_args()

    failures: list[str] = []
    warnings: list[str] = []

    required_imports, required_missing = inspect_import_groups(
        REQUIRED_PYTHON_IMPORT_GROUPS
    )
    optional_imports, optional_missing = inspect_import_groups(
        OPTIONAL_PYTHON_IMPORT_GROUPS
    )
    failures.extend(
        f"missing required Python runtime dependency: {item}"
        for item in required_missing
    )
    warnings.extend(
        f"missing optional Python runtime dependency: {item}"
        for item in optional_missing
    )

    project_results, project_failures = project_import_checks()
    runtime_files, runtime_file_failures = file_checks(
        CURRENT_RUNTIME_FILES, "runtime"
    )
    firmware_files, firmware_file_failures = file_checks(
        CURRENT_FIRMWARE_SOURCE_FILES, "firmware source"
    )
    failures.extend(project_failures)
    failures.extend(runtime_file_failures)
    failures.extend(firmware_file_failures)

    core_commands = command_checks(CORE_COMMANDS)
    pi_commands = command_checks(PI_RUNTIME_COMMANDS)
    optional_commands = {
        group: command_checks(commands)
        for group, commands in OPTIONAL_COMMAND_GROUPS.items()
    }
    edge_tts = {
        "available": command_path("edge-tts") is not None,
        "path": command_path("edge-tts"),
    }

    for command, result in core_commands.items():
        if not result["available"]:
            failures.append(f"missing core host command: {command}")
    if not edge_tts["available"]:
        failures.append("missing William TTS command: edge-tts")
    for command, result in pi_commands.items():
        if result["available"]:
            continue
        message = f"missing Pi host command: {command}"
        if command in REQUIRED_PI_RUNTIME_COMMANDS:
            failures.append(message)
        else:
            warnings.append(message)
    for group, commands in optional_commands.items():
        for command, result in commands.items():
            if not result["available"]:
                warnings.append(
                    f"missing optional host command for {group}: {command}"
                )

    required_can = can_required()
    if required_can:
        if not import_available(optional_imports, "optional_can_runtime", "can"):
            failures.append("SocketCAN is required but python-can is unavailable")
        for command in ("ip", "modprobe", "candump"):
            available = (
                pi_commands.get(command, {}).get("available")
                or optional_commands.get("socketcan", {})
                .get(command, {})
                .get("available")
            )
            if not available:
                failures.append(
                    f"SocketCAN is required but host command is missing: {command}"
                )

    strict_system = (
        args.strict_system
        or os.getenv("STRICT_FULL_RUNTIME_DEPENDENCIES", "0") == "1"
    )
    if strict_system:
        failures.extend(
            f"strict system dependency: {warning}" for warning in warnings
        )

    python_results = {**required_imports, **optional_imports}
    payload = {
        "status": (
            "FULL_RUNTIME_DEPENDENCIES_READY"
            if not failures
            else "FULL_RUNTIME_DEPENDENCIES_INCOMPLETE"
        ),
        "runtime_mode": "headless_pi_os_lite",
        "canonical_installer": "one-shot-install.sh",
        "firmware_flashing": False,
        "can_required": required_can,
        "offline_stt_required": True,
        "offline_stt_backend": "pocketsphinx",
        "william_tts_required": True,
        "audible_pi_playback_required": True,
        "required_pi_commands": sorted(REQUIRED_PI_RUNTIME_COMMANDS),
        "python_imports": python_results,
        "project_modules": project_results,
        "runtime_files": runtime_files,
        "firmware_source_files": firmware_files,
        "commands": {
            "core": core_commands,
            "pi_runtime": pi_commands,
            "edge_tts": edge_tts,
            "optional": optional_commands,
        },
        "warnings": warnings,
        "strict_system": strict_system,
        "failures": failures,
        "updated_at": time.time(),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "status_path": str(STATUS_PATH),
                "warning_count": len(warnings),
                "failures": failures,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
