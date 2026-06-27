#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

STATUS_PATH = ROOT / "logs" / "one_shot" / "full_runtime_dependencies.json"

PYTHON_IMPORTS = {
    "core_ble_serial": ["serial", "bleak"],
    "menu_ui": ["rich", "pydantic", "pygame"],
    "api_services": ["fastapi", "uvicorn", "requests", "httpx"],
    "gpio_buttons": ["gpiozero"],
    "can_bench": ["can"],
    "voice_ai": ["pyttsx3", "speech_recognition"],
}

BOARD_COMMANDS = {
    "pi_usb_udev": ["lsusb", "udevadm"],
    "pi_wifi": ["iw", "wpa_supplicant"],
    "bluez_ble": ["bluetoothctl", "btmgmt", "rfkill"],
    "can_bench_optional": ["ip", "modprobe", "cansend", "candump"],
    "audio_voice": ["aplay"],
    "serial_console": ["picocom"],
    "build_flash": ["git", "cmake", "ninja", "west"],
}

REQUIRED_PROJECT_MODULES = [
    "koalablue.menu_catalog",
    "koalablue.menu_ui",
    "koalablue.t114_menu_status",
    "koalablue.t114_bluez",
    "koalablue.ble_node_manager",
    "koalablue.gnss_location",
    "koalablue.gpio_buttons",
    "koalablue.killerkoala_voice_control",
    "koalablue.killerkoala_hybrid_companion",
    "koalablue.koala_kan_kommander",
    "koalablue.anteater",
    "koalablue.meshtastic_app",
    "scripts.check_menu_actions",
    "scripts.check_one_shot_controls",
    "scripts.check_t114_status_dashboard",
]

BOARD_FILES = [
    "firmware/t114-combined-safe/CMakeLists.txt",
    "firmware/t114-combined-safe/prj.conf",
    "firmware/t114-combined-safe/src/main.c",
    "firmware/esp32-dualeye/platformio.ini",
    "firmware/heltec-mouth/platformio.ini",
    "scripts/setup_system_packages.sh",
    "scripts/setup_heltec_t114_tools.sh",
    "scripts/setup_nrf_tools.sh",
    "scripts/setup_nrf_connect_sdk_toolchain.sh",
    "scripts/setup_esp32_tools.sh",
    "scripts/flash_t114_when_plugged.sh",
    "scripts/build_t114_combined_safe.sh",
    "scripts/flash_t114_combined_safe.sh",
    "scripts/flash_esp32.sh",
    "scripts/install_ble_node_manager_service.sh",
    "scripts/install_esp32_dualeye_voice_bridge_service.sh",
    "scripts/check_t114_status_dashboard.py",
]


def _check_imports(groups: dict[str, list[str]]) -> tuple[dict[str, dict[str, bool]], list[str]]:
    results: dict[str, dict[str, bool]] = {}
    failures: list[str] = []
    for group, modules in groups.items():
        results[group] = {}
        for module in modules:
            try:
                importlib.import_module(module)
                results[group][module] = True
            except Exception as exc:
                results[group][module] = False
                failures.append(f"missing Python dependency for {group}: {module} ({exc})")
    return results, failures


def _check_commands(groups: dict[str, list[str]]) -> tuple[dict[str, dict[str, bool]], list[str]]:
    results: dict[str, dict[str, bool]] = {}
    failures: list[str] = []
    for group, commands in groups.items():
        results[group] = {}
        for command in commands:
            present = shutil.which(command) is not None
            results[group][command] = present
            if not present and not group.endswith("_optional"):
                failures.append(f"missing system command for {group}: {command}")
    return results, failures


def _check_files(paths: Iterable[str]) -> tuple[dict[str, bool], list[str]]:
    results: dict[str, bool] = {}
    failures: list[str] = []
    for relative in paths:
        present = (ROOT / relative).exists()
        results[relative] = present
        if not present:
            failures.append(f"missing board/helper file: {relative}")
    return results, failures


def _check_project_imports(modules: list[str]) -> tuple[dict[str, bool], list[str]]:
    results: dict[str, bool] = {}
    failures: list[str] = []
    for module in modules:
        try:
            importlib.import_module(module)
            results[module] = True
        except Exception as exc:
            results[module] = False
            failures.append(f"project module import failed: {module} ({exc})")
    return results, failures


def _check_menu_manifest() -> tuple[dict[str, object], list[str]]:
    from scripts.check_menu_actions import build_manifest

    manifest, failures = build_manifest()
    if manifest.get("status") != "MENU_ACTIONS_READY":
        failures.append("menu action manifest is not ready")
    if int(manifest.get("status_row_count", 0)) < 3:
        failures.append("T114 status rows are not registered as display-only rows")
    return manifest, failures


def build_status(*, strict_commands: bool = False) -> dict[str, object]:
    import_results, import_failures = _check_imports(PYTHON_IMPORTS)
    project_results, project_failures = _check_project_imports(REQUIRED_PROJECT_MODULES)
    command_results, command_failures = _check_commands(BOARD_COMMANDS)
    file_results, file_failures = _check_files(BOARD_FILES)
    menu_manifest, menu_failures = _check_menu_manifest()

    failures = [*import_failures, *project_failures, *file_failures, *menu_failures]
    if strict_commands:
        failures.extend(command_failures)

    return {
        "status": "FULL_RUNTIME_DEPENDENCIES_READY" if not failures else "FULL_RUNTIME_DEPENDENCIES_INCOMPLETE",
        "updated_at": time.time(),
        "python_imports": import_results,
        "project_imports": project_results,
        "system_commands": command_results,
        "system_command_failures": command_failures,
        "board_files": file_results,
        "menu_status": menu_manifest.get("status"),
        "menu_names": menu_manifest.get("menu_names", []),
        "enabled_leaf_count": menu_manifest.get("enabled_leaf_count", 0),
        "status_row_count": menu_manifest.get("status_row_count", 0),
        "strict_commands": strict_commands,
        "optional_can_default_non_failing": True,
        "one_shot_installer_check": True,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check KoalaByte Blue full runtime dependencies for one-shot install")
    parser.add_argument("--output", default=str(STATUS_PATH), help="Path for the dependency status JSON artifact")
    parser.add_argument("--strict-commands", action="store_true", help="Fail if required system commands are missing")
    args = parser.parse_args()

    strict_commands = args.strict_commands or os.getenv("STRICT_FULL_RUNTIME_DEPENDENCIES", "0") == "1"
    payload = build_status(strict_commands=strict_commands)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "output": str(output), "failures": payload["failures"]}, indent=2, sort_keys=True))
    return 1 if payload["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
