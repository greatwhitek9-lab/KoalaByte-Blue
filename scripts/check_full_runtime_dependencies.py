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
    "bluez_legacy_lab_optional": ["hciconfig", "hcitool", "rfcomm", "l2ping", "gatttool", "btproxy", "busctl", "sdptool", "btmon"],
    "can_bench_optional": ["ip", "modprobe", "cansend", "candump"],
    "audio_voice": ["aplay"],
    "serial_console": ["picocom"],
    "build_flash": ["git", "cmake", "ninja", "west"],
}

REQUIRED_PROJECT_MODULES = [
    "koalablue.menu_catalog",
    "koalablue.menu_ui",
    "koalablue.menu_action_runner",
    "koalablue.bluez_tools",
    "koalablue.bluez_protected_lab",
    "koalablue.eucalyptus_wigle",
    "koalablue.koala_kombat_kruisin",
    "koalablue.koala_kombat_node_roles",
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
    "scripts/run_eucalyptus_wigle.py",
    "scripts/check_eucalyptus_wigle.py",
    "scripts/run_koala_kombat_kruisin.py",
    "scripts/check_koala_kombat_kruisin.py",
    "docs/KOALA_KOMBAT_NODE_ROLES.md",
    "scripts/run_koala_bluez.py",
    "scripts/run_koala_bluez_manifest.sh",
    "scripts/run_koala_bluez_inventory.sh",
    "scripts/run_koala_bluez_status.sh",
    "scripts/run_koala_bluez_scan.sh",
    "scripts/run_koala_bluez_monitor.sh",
    "scripts/run_koala_bluez_all_safe.sh",
    "scripts/run_koala_bluez_info.sh",
    "scripts/run_koala_bluez_services.sh",
    "scripts/run_koala_bluez_gatt_readiness.sh",
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
    """Check host commands without failing normal CI/check-only runs.

    GitHub-hosted runners are not Raspberry Pi images and usually lack BlueZ,
    Wi-Fi, ALSA, serial, and west tooling. In normal check-only mode those are
    readiness warnings. Use --strict-system or STRICT_FULL_RUNTIME_DEPENDENCIES=1
    on a real Pi image when missing host commands should fail the check.
    """
    results: dict[str, dict[str, bool]] = {}
    warnings: list[str] = []
    for group, commands in groups.items():
        results[group] = {}
        for command in commands:
            present = shutil.which(command) is not None
            results[group][command] = present
            if not present:
                warnings.append(f"missing host command for {group}: {command}")
    return results, warnings


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Check KoalaByte Blue full runtime dependencies and board helper coverage")
    parser.add_argument("--strict-system", action="store_true", help="Fail on missing host system commands too")
    args = parser.parse_args()

    failures: list[str] = []
    py_results, py_failures = _check_imports(PYTHON_IMPORTS)
    file_results, file_failures = _check_files(BOARD_FILES)
    module_results, module_failures = _check_project_imports(REQUIRED_PROJECT_MODULES)
    command_results, command_warnings = _check_commands(BOARD_COMMANDS)
    failures.extend(py_failures)
    failures.extend(file_failures)
    failures.extend(module_failures)

    strict_system = args.strict_system or os.environ.get("STRICT_FULL_RUNTIME_DEPENDENCIES") == "1"
    if strict_system:
        for group, commands in command_results.items():
            for command, present in commands.items():
                if not present:
                    failures.append(f"strict system command missing for {group}: {command}")

    payload = {
        "status": "FULL_RUNTIME_DEPENDENCIES_READY" if not failures else "FULL_RUNTIME_DEPENDENCIES_INCOMPLETE",
        "python_imports": py_results,
        "project_modules": module_results,
        "board_files": file_results,
        "system_commands": command_results,
        "host_command_warnings": command_warnings,
        "strict_system": strict_system,
        "failures": failures,
        "updated_at": time.time(),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
