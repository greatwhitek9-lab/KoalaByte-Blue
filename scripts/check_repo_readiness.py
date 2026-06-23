#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

CANONICAL_BRANCH = "koalabyte_blue_v2_heltec_edition"

NEEDED = [
    "README.md",
    "docs/CANONICAL_BRANCH.md",
    "docs/FLASHING.md",
    "docs/KOALA_MODE_SWITCHER_REVA21.md",
    "docs/MINED_HELTEC_V2_FEATURES.md",
    "docs/KOALA_KONNECT_HELTEC_T114.md",
    "docs/T114_HARDWARE_VALIDATION.md",
    "docs/T114_BLUEZ_WRAPPER.md",
    "docs/MESHTASTIC_APP_T114.md",
    "docs/GREATWHITE_WIRESHARK_TSHARK.md",
    "firmware/heltec-mouth/boards/heltec_t114.json",
    "firmware/heltec-mouth/platformio.ini",
    "firmware/heltec-mouth/src/main.cpp",
    "pi-companion/requirements.txt",
    "pi-companion/requirements-heltec-v2-extra.txt",
    "pi-companion/koalablue/menu_catalog.py",
    "pi-companion/koalablue/menu_theme.py",
    "pi-companion/koalablue/location_password_gate.py",
    "pi-companion/koalablue/meshtastic_app.py",
    "pi-companion/koalablue/greatwhite.py",
    "scripts/flash_all_components.sh",
    "scripts/prepare_t114_firmware_profiles.sh",
    "scripts/select_t114_startup_mode.py",
    "scripts/koalabyte_blue_boot.sh",
    "scripts/run_menu_screen.py",
    "scripts/run_t114_bluez.py",
    "scripts/run_meshtastic_app.py",
    "scripts/run_location_password_gate.py",
    "scripts/run_gw.py",
    "scripts/setup_nrf_sniffer_ble.sh",
    "scripts/build_koala_konnect_t114.sh",
    "scripts/flash_koala_konnect_t114.sh",
]

SHELL_HELPERS = [
    "scripts/flash_all_components.sh",
    "scripts/prepare_t114_firmware_profiles.sh",
    "scripts/build_firmware_all.sh",
    "scripts/setup_system_packages.sh",
    "scripts/setup_can0.sh",
    "scripts/setup_vcan0.sh",
    "scripts/install_can0_service.sh",
    "scripts/run_can0_service.sh",
    "scripts/install_koalabyte_udev_rules.sh",
    "scripts/preflight_all_hardware.sh",
    "scripts/run_ble_node_manager_service.sh",
    "scripts/install_ble_node_manager_service.sh",
    "scripts/flash_heltec_mouth.sh",
    "scripts/koalabyte_blue_boot.sh",
    "scripts/confirm_t114_board_target.sh",
    "scripts/configure_t114_2g4_antenna.sh",
    "scripts/build_nrf52840_t114_hci_usb.sh",
    "scripts/flash_nrf52840_t114_hci_usb.sh",
    "scripts/build_koala_konnect_t114.sh",
    "scripts/flash_koala_konnect_t114.sh",
    "scripts/setup_nrf_sniffer_ble.sh",
]

REQUIRED_TEXT = {
    "docs/CANONICAL_BRANCH.md": [CANONICAL_BRANCH],
    "docs/FLASHING.md": [
        "KoalaByte Blue Flashing and Installation Guide - Heltec T114 Edition",
        "Heltec Mesh Node T114 v2 onboard nRF52840",
        "firmware/heltec-mouth/",
        "heltec_t114_v2/nrf52840",
        "KOALABYTE_HELTEC_USB_PORT",
        "This branch does **not** use a separate Nordic USB Dongle lab firmware flow.",
    ],
    "docs/KOALA_MODE_SWITCHER_REVA21.md": [
        "Koala Mode Switcher - Heltec T114 Edition",
        "Heltec Mesh Node T114 v2 onboard nRF52840",
        "not for a separate Nordic nRF52840 USB Dongle",
        "firmware/heltec-mouth/",
        "heltec_t114_v2/nrf52840",
        "KOALABYTE_HELTEC_USB_PORT",
        "scripts/flash_heltec_mouth.sh",
        "scripts/flash_koala_konnect_t114.sh",
    ],
    "docs/MINED_HELTEC_V2_FEATURES.md": ["Old-koalabyte-blue-v2-heltec-edition", "Greatwhite"],
    "docs/GREATWHITE_WIRESHARK_TSHARK.md": ["Greatwhite", "run_gw.py", "setup_nrf_sniffer_ble.sh"],
    "pi-companion/koalblue/menu_catalog.py": [],
    "pi-companion/koalablue/menu_catalog.py": ["SUBMENU_ITEMS", "leaf_menu_entries", "Greatwhite Reef Patrol", "AntEater"],
    "pi-companion/koalablue/menu_theme.py": ["JungleMenuTheme", "GREATWHITE REEF", "SNIFFER NEST"],
    "scripts/flash_all_components.sh": ["RUN_T114_PROFILE_PREP", "--prepare-t114-profiles", "scripts/prepare_t114_firmware_profiles.sh", "scripts/select_t114_startup_mode.py"],
    "scripts/prepare_t114_firmware_profiles.sh": ["heltec_lab", "koala_konnect_t114", "BUILD_ONLY=1 bash scripts/flash_heltec_mouth.sh", "scripts/build_koala_konnect_t114.sh"],
    "scripts/select_t114_startup_mode.py": ["Heltec Mesh Node T114 v2 onboard nRF52840", "heltec_lab", "koala_konnect_t114", "startup_selection.json"],
    "scripts/koalabyte_blue_boot.sh": ["T114_STARTUP_SELECTOR", "scripts/select_t114_startup_mode.py", "flash_heltec_mouth.sh", "flash_koala_konnect_t114.sh"],
    "scripts/run_menu_screen.py": ["leaf_menu_entries", "menu.register_handler", "Touchscreen: long press=select"],
    "scripts/run_location_password_gate.py": ["koalablue.location_password_gate", "run_cli"],
}

FORBIDDEN_TEXT = {
    "docs/FLASHING.md": [
        "nRF52840 Dongle KoalaByte Lab firmware",
        "Nordic nRF52840 Dongle / PCA10059 / NRF52840-DONGLE",
        "bash scripts/build_nrf52840_dongle_lab.sh",
        "firmware/nrf52840-dongle-ear-tag-tx-lab",
        "nrf52840dongle_nrf52840",
    ],
    "docs/KOALA_MODE_SWITCHER_REVA21.md": [
        "switching the nRF52840 USB Dongle",
        "KoalaByte Blue dongle firmware profiles",
        "Only one firmware can be installed on the dongle at a time",
        "logs/dongle_mode_state.json",
        "NRF_DFU_PORT",
        "nrf52840-dongle",
        "dongle DFU flow",
    ],
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def check_required_files(failures: list[str]) -> None:
    for relative_path in NEEDED:
        if not (ROOT / relative_path).exists():
            failures.append(f"missing required Heltec Edition file: {relative_path}")


def check_required_text(failures: list[str]) -> None:
    for relative_path, words in REQUIRED_TEXT.items():
        if not words:
            continue
        body = read_text(ROOT / relative_path)
        for word in words:
            if word not in body:
                failures.append(f"{relative_path} missing expected text: {word}")


def check_forbidden_text(failures: list[str]) -> None:
    for relative_path, words in FORBIDDEN_TEXT.items():
        body = read_text(ROOT / relative_path)
        for word in words:
            if word in body:
                failures.append(f"{relative_path} still contains stale dongle-only wording: {word}")


def check_config(failures: list[str]) -> None:
    config_path = ROOT / "pi-companion" / "config.default.json"
    if not config_path.exists():
        return
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"config.default.json is invalid JSON: {exc}")
        return
    if "koala_kan_kommander" not in config:
        failures.append("config.default.json missing koala_kan_kommander section")


def check_shell_helpers(failures: list[str]) -> None:
    for helper in SHELL_HELPERS:
        body = read_text(ROOT / helper)
        if body and "set -euo pipefail" not in body:
            failures.append(f"shell helper missing strict shell mode: {helper}")


def check_executable_submenus(failures: list[str]) -> None:
    try:
        from koalablue.menu_catalog import SUBMENU_ITEMS, leaf_menu_entries
    except Exception as exc:
        failures.append(f"failed to import submenu catalog: {exc}")
        return

    leaf_commands: set[str] = set()
    for submenu_name, entries in SUBMENU_ITEMS.items():
        if not entries:
            failures.append(f"submenu has no items: {submenu_name}")
            continue
        for idx, entry in enumerate(entries, start=1):
            label = str(entry.get("label", "")).strip()
            command = str(entry.get("command", "")).strip()
            enabled = bool(entry.get("enabled", True))
            if not label:
                failures.append(f"submenu {submenu_name} item {idx} has no label")
            if enabled and not command:
                failures.append(f"submenu {submenu_name} item {label or idx} has no executable command")
            if enabled and command and not command.startswith("submenu:"):
                leaf_commands.add(command)

    catalog_leaf_commands = {str(entry.get("command", "")).strip() for entry in leaf_menu_entries()}
    missing_from_leaf_helper = sorted(leaf_commands - catalog_leaf_commands)
    if missing_from_leaf_helper:
        failures.append(f"enabled submenu leaf commands missing from leaf_menu_entries(): {missing_from_leaf_helper}")

    runner_path = ROOT / "scripts" / "run_menu_screen.py"
    spec = importlib.util.spec_from_file_location("koalabyte_menu_runner_readiness", runner_path)
    if spec is None or spec.loader is None:
        failures.append("failed to load run_menu_screen.py for menu handler validation")
        return
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        menu = module.make_menu()
    except Exception as exc:
        failures.append(f"failed to build menu runner for handler validation: {exc}")
        return

    registered = set(getattr(menu, "_handlers", {}).keys())
    missing_handlers = sorted(catalog_leaf_commands - registered)
    if missing_handlers:
        failures.append(f"submenu leaf commands missing registered execution handlers: {missing_handlers}")


def main() -> int:
    failures: list[str] = []
    check_required_files(failures)
    check_required_text(failures)
    check_forbidden_text(failures)
    check_config(failures)
    check_executable_submenus(failures)
    check_shell_helpers(failures)

    if failures:
        print("KoalaByte readiness issues:")
        for failure in failures:
            print("- " + failure)
        return 1
    print("KoalaByte Blue repo readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
