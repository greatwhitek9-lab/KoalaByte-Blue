#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = REPO_ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

REQUIRED_FILES = [
    "README.md",
    "docs/MAIN_BLE_NODE_ROLES.md",
    "docs/ANTEATER_BLE_CARD_SKIMMER_DETECTOR.md",
    "docs/FLASHING.md",
    "docs/EUCALYPTUS_ALWAYS_ON_BLE_REVA8.md",
    "docs/CAMERA_AWARENESS_LOGGER.md",
    "docs/THATS_NOT_A_KNIFE_SERVICE.md",
    "docs/KOALA_BLUEZ_TOOLS_REVA16.md",
    "docs/ORDERABLE_PARTS_LIST.md",
    "docs/PRODUCTION_FILES.md",
    "docs/POWER_BANK_WIRING_MAIN.svg",
    "firmware/esp32-dualeye/platformio.ini",
    "firmware/esp32-dualeye/include/config.h",
    "firmware/esp32-dualeye/src/main.cpp",
    "firmware/esp32-dualeye/src/koalagotchi_mode_screens.h",
    "firmware/esp32-dualeye/src/koalagotchi_mode_screens.cpp",
    "pi-companion/config.default.json",
    "pi-companion/requirements.txt",
    "pi-companion/koalablue/__init__.py",
    "pi-companion/koalablue/menu_catalog.py",
    "pi-companion/koalablue/anteater.py",
    "pi-companion/koalablue/ble_event_log.py",
    "pi-companion/koalablue/ble_node_manager.py",
    "pi-companion/koalablue/koala_kan_kommander.py",
    "scripts/discover_koalabyte_ports.py",
    "scripts/preflight_all_hardware.py",
    "scripts/setup_heltec_t114_tools.sh",
    "scripts/install_koalabyte_udev_rules.sh",
    "scripts/check_menu_actions.py",
    "scripts/run_ble_node_manager.py",
    "scripts/run_ble_node_manager_service.sh",
    "scripts/install_ble_node_manager_service.sh",
    "scripts/flash_all_components.sh",
    "scripts/build_firmware_all.sh",
    "scripts/install_pi.sh",
    "scripts/setup_system_packages.sh",
    "scripts/setup_can0.sh",
    "scripts/setup_vcan0.sh",
    "scripts/install_can0_service.sh",
    "scripts/run_can0_service.sh",
    "scripts/run_koala_kan_kommander.py",
    "scripts/run_killerkoala_voice.py",
    "scripts/run_killerkoala_hybrid.py",
    "scripts/set_esp32_eyes.py",
    "scripts/run_anteater.py",
    "scripts/run_menu_screen.py",
]

REQUIRED_TEXT = {
    "README.md": [
        "KoalaByte Blue V2 Heltec Edition",
        "Heltec Mesh Node T114 nRF52840",
        "primary BLE board",
        "AntEater passive BLE payment-terminal risk triage from the Heltec primary BLE node log",
        "docs/ANTEATER_BLE_CARD_SKIMMER_DETECTOR.md",
        "bash scripts/flash_all_components.sh --menu-check",
    ],
    "docs/MAIN_BLE_NODE_ROLES.md": [
        "Heltec Mesh Node T114 onboard Nordic nRF52840",
        "Primary BLE board",
        "ESP32-S3 DualEye BLE",
        "Raspberry Pi onboard BlueZ",
    ],
    "docs/ANTEATER_BLE_CARD_SKIMMER_DETECTOR.md": [
        "Heltec Edition data path",
        "logs/ble_nodes/ble_events.jsonl",
        "--live-scan",
        "advertisement-only",
    ],
    "docs/FLASHING.md": [
        "scripts/setup_heltec_t114_tools.sh",
        "KOALABYTE_PRIMARY_BLE_PORT",
        "INSTALL_HELTEC_NRF_TOOLS=1",
    ],
    "pi-companion/koalbluelib_missing_guard": [],
    "pi-companion/koalablue/anteater.py": [
        "DEFAULT_NODE_LOG_PATH",
        "logs/ble_nodes/ble_events.jsonl",
        "heltec_primary_node_log_preferred",
        "--live-scan",
    ],
    "pi-companion/koalablue/menu_catalog.py": [
        "AntEater",
        "anteater",
        "leaf_menu_entries",
        "all_menu_entries",
    ],
    "scripts/check_menu_actions.py": [
        "MENU_ACTIONS_READY",
        "all_menu_entries",
        "leaf_menu_entries",
        "menu_action_manifest.json",
        "no_menu_actions_executed",
    ],
    "scripts/run_menu_screen.py": [
        "run_anteater_action",
        "menu.register_handler(\"anteater\"",
    ],
    "pi-companion/koalablue/ble_event_log.py": [
        "PRIMARY_SOURCE = \"heltec-t114-nrf52840\"",
        "LEGACY_PRIMARY_SOURCES",
        "is_primary_source",
    ],
    "pi-companion/koalablue/ble_node_manager.py": [
        "heltec-t114-nrf52840",
        "primary_ble",
        "ESP32-S3 DualEye and Raspberry Pi BlueZ",
        "PiBluezSecondaryScanner",
    ],
    "scripts/setup_heltec_t114_tools.sh": [
        "Heltec Mesh Node T114 dependency setup helper",
        "pyserial",
        "bleak",
        "install_koalabyte_udev_rules.sh",
        "discover_koalabyte_ports.py",
        "INSTALL_HELTEC_NRF_TOOLS",
    ],
    "scripts/run_ble_node_manager.py": [
        "--primary-port",
        "KOALABYTE_PRIMARY_BLE_PORT",
        "KOALABYTE_HELTEC_USB_PORT",
        "--esp32-port",
        "--no-pi-bluez",
    ],
    "scripts/run_ble_node_manager_service.sh": [
        "/dev/koalabyte-heltec",
        "KOALABYTE_PRIMARY_BLE_PORT",
        "KOALABYTE_HELTEC_USB_PORT",
        "--primary-port",
    ],
    "scripts/install_ble_node_manager_service.sh": [
        "--profile heltec",
        "KOALABYTE_PRIMARY_BLE_PORT",
        "Heltec T114 nRF52840 primary BLE board",
    ],
    "scripts/discover_koalabyte_ports.py": [
        "primary_ble",
        "KOALABYTE_PRIMARY_BLE_PORT",
        "KOALABYTE_HELTEC_USB_PORT",
        "heltec-t114-nrf52840",
    ],
    "scripts/preflight_all_hardware.py": [
        "KoalaByte Blue V2 Heltec Edition",
        "primary_ble_architecture",
        "heltec-t114-nrf52840",
    ],
    "scripts/install_koalabyte_udev_rules.sh": [
        "/dev/koalabyte-heltec",
        "/dev/koalabyte-esp32-eyes",
        "99-koalabyte.rules",
    ],
    "scripts/install_pi.sh": [
        "setup_heltec_t114_tools.sh",
        "INSTALL_HELTEC_T114_TOOLS",
        "STRICT_HELTEC_T114_TOOLS",
        "PREPARE_DONGLE_CACHE=",
    ],
    "scripts/flash_all_components.sh": [
        "RUN_MENU_CHECK",
        "--menu-check",
        "setup_menu_items_for_selected_mode",
        "scripts/check_menu_actions.py",
        "menu_action_manifest.json",
        "RUN_ANTEATER",
        "--anteater",
        "setup_anteater_for_selected_mode",
        "ANTEATER_READY",
        "no_live_scan_during_flash",
        "scripts/run_anteater.py status",
        "INSTALL_HELTEC_T114_TOOLS",
        "STRICT_HELTEC_T114_TOOLS",
        "INSTALL_HELTEC_NRF_TOOLS",
    ],
    "scripts/setup_system_packages.sh": [
        "Heltec T114 USB serial",
        "python3-serial",
        "usbutils",
        "udev",
        "bluez",
    ],
}

FORBIDDEN_ARCHITECTURE_TEXT = {
    "README.md": [
        "ESP32-S3 DualEye BLE | Primary",
        "nRF52840 USB Dongle | Primary",
        "The `main` branch uses the Nordic nRF52840 USB Dongle",
    ],
    "docs/MAIN_BLE_NODE_ROLES.md": [
        "The `main` branch uses the Nordic nRF52840 USB Dongle",
        "nRF52840 USB Dongle | Primary",
        "resolves duplicate observations in favor of the nRF52840 Dongle",
    ],
    "pi-companion/koalablue/ble_node_manager.py": [
        "The Nordic nRF52840 USB Dongle is the primary BLE source",
    ],
    "scripts/run_ble_node_manager.py": [
        "with nRF52840 Dongle as the primary BLE node",
    ],
    "scripts/install_ble_node_manager_service.sh": [
        "nRF52840 Dongle primary BLE node",
    ],
}

SHELL_HELPERS = [
    "scripts/flash_all_components.sh",
    "scripts/build_firmware_all.sh",
    "scripts/setup_system_packages.sh",
    "scripts/setup_esp32_tools.sh",
    "scripts/setup_heltec_t114_tools.sh",
    "scripts/configure_esp32s3_dualeye_2g4_antenna.sh",
    "scripts/setup_can0.sh",
    "scripts/setup_vcan0.sh",
    "scripts/install_can0_service.sh",
    "scripts/run_can0_service.sh",
    "scripts/install_koalabyte_udev_rules.sh",
    "scripts/preflight_all_hardware.sh",
    "scripts/run_ble_node_manager_service.sh",
    "scripts/install_ble_node_manager_service.sh",
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def check_required_files(failures: list[str]) -> None:
    for relative_path in REQUIRED_FILES:
        if not (REPO_ROOT / relative_path).exists():
            failures.append(f"missing required file: {relative_path}")


def check_required_text(failures: list[str]) -> None:
    for relative_path, needles in REQUIRED_TEXT.items():
        if not needles:
            continue
        path = REPO_ROOT / relative_path
        text = read_text(path)
        for needle in needles:
            if needle not in text:
                failures.append(f"{relative_path} missing expected text: {needle}")


def check_forbidden_architecture_text(failures: list[str]) -> None:
    for relative_path, needles in FORBIDDEN_ARCHITECTURE_TEXT.items():
        path = REPO_ROOT / relative_path
        text = read_text(path)
        for needle in needles:
            if needle in text:
                failures.append(f"{relative_path} still contains stale architecture text: {needle}")


def check_config(failures: list[str]) -> None:
    path = REPO_ROOT / "pi-companion" / "config.default.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"config.default.json is invalid JSON: {exc}")
        return
    for section in ["killerkoala_companion", "koala_kan_kommander", "anteater"]:
        if section not in config:
            failures.append(f"config missing required section: {section}")


def check_menu_catalog(failures: list[str]) -> None:
    try:
        from koalablue.menu_catalog import MENU_GROUPS, SUBMENU_ITEMS, leaf_menu_entries, menu_labels
    except Exception as exc:
        failures.append(f"failed to import menu catalog: {exc}")
        return
    if "Bluetooth Tools" not in MENU_GROUPS:
        failures.append("menu catalog missing Bluetooth Tools group")
    if "System / Companion" not in MENU_GROUPS:
        failures.append("menu catalog missing System / Companion group")
    if "eucalyptus" not in SUBMENU_ITEMS:
        failures.append("menu catalog missing eucalyptus submenu")
    if "Bluetooth Tools" not in menu_labels("main"):
        failures.append("main menu labels missing Bluetooth Tools")
    if "AntEater" not in menu_labels("bluetooth"):
        failures.append("Bluetooth submenu missing AntEater")
    if not leaf_menu_entries():
        failures.append("menu catalog has no enabled leaf menu entries")


def check_helpers(failures: list[str]) -> None:
    for helper in SHELL_HELPERS:
        path = REPO_ROOT / helper
        if path.exists() and "set -euo pipefail" not in path.read_text(encoding="utf-8"):
            failures.append(f"shell helper missing strict shell mode: {helper}")


def main() -> int:
    failures: list[str] = []
    check_required_files(failures)
    check_required_text(failures)
    check_forbidden_architecture_text(failures)
    check_config(failures)
    check_menu_catalog(failures)
    check_helpers(failures)

    if failures:
        print("KoalaByte Blue V2 Heltec Edition repo readiness check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("KoalaByte Blue V2 Heltec Edition repo readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())