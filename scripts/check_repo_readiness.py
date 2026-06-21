#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = REPO_ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

EXPECTED_MENU_LABELS = [
    "Scan", "Summary", "Show Devices", "eucalyptus Status", "eucalyptus Start", "eucalyptus Stop", "eucalyptus Restart", "eucalyptus Upload Status",
    "Eucalyptus Mode", "Koala Kapture", "Koala Kry", "Koala Kry RF Review", "Ear Tag", "KoalaByte Lab", "Koala Mode Switcher", "Koala Kan Kommander",
    "Gumleaf Gear Check", "Eucalyptus Bus Scout", "Dropbear Discovery Sweep", "Billabong HCI Watch", "Kookaburra Safe Nest Run",
    "that’s not a knife", "KillerKoala Voice", "Urban Poaching", "Buttons", "Level / Status", "Report", "Boomerang", "Wake killerkoala",
    "Authorized BLE Inventory", "GATT Readiness Checklist", "Pairing Security Review", "Lab Beacon Plan", "Packet Capture Notes", "Defensive Lab Report",
    "Restricted Placeholder", "Settings", "Lab", "Shutdown", "Quit",
]

MAIN_REQUIRED_FILES = [
    "README.md",
    "docs/PRODUCTION_FILES.md",
    "docs/ORDERABLE_PARTS_LIST.md",
    "docs/POWER_BANK_WIRING_MAIN.svg",
    "production/WIRING_DIAGRAM_ANTENNAS.md",
    "production/WIRING_DIAGRAM_ANTENNAS.svg",
    "production/RevA17-dongle-only/BOM_RevA17_DongleOnly.csv",
    "production/RevA17-dongle-only/PRODUCTION_README_RevA17_DongleOnly.md",
    "production/RevA17-dongle-only/BATTERY_POWER_2S_18650.md",
    "production/RevA17-dongle-only/Safety_Test_Record_RevA17.csv",
    "firmware/esp32-dualeye/platformio.ini",
    "firmware/esp32-dualeye/include/config.h",
    "firmware/esp32-dualeye/src/main.cpp",
    "firmware/nrf52840-dongle-ear-tag-tx-lab/CMakeLists.txt",
    "pi-companion/config.default.json",
    "pi-companion/requirements.txt",
    "pi-companion/koalablue/menu_catalog.py",
    "scripts/configure_esp32s3_dualeye_2g4_antenna.sh",
    "scripts/flash_all_components.sh",
    "scripts/build_firmware_all.sh",
    "scripts/install_pi.sh",
    "scripts/run_menu_screen.py",
]

BRANCH_ONLY_PATHS = [
    "docs/" + "DIDGER" + "IDOO_" + "LO" + "RA_SETUP.md",
    "docs/NRF52840_" + "T" + "114_ALT_TARGET.md",
    "docs/" + "T" + "114_WHOLE_FIRMWARE_TEST.md",
    "scripts/run_" + "didgeri" + "doo.py",
    "pi-companion/koalablue/" + "didgeri" + "doo_" + "lo" + "ra.py",
]

BRANCH_ONLY_TERMS = [
    "Hel" + "tec",
    "Mesh" + "tastic",
    "didgeri" + "doo",
    "Lo" + "Ra",
    "lo" + "ra",
    "GN" + "SS",
    "SX" + "1262",
    "UC" + "6580",
    "T" + "114",
    "Wireless " + "Tracker",
]

EXPECTED_BOM_ITEMS = {
    "Raspberry Pi 3 Model B+",
    "Nordic nRF52840 USB Dongle / PCA10059 / NRF52840-DONGLE",
    "ESP32-S3 DualEye module",
    "ESP32-S3 DualEye external 2.4 GHz antenna kit",
    "PIFFA-style 50000 mAh USB portable power bank 22.5 W class",
    "InnoMaker USB to CAN Converter kit",
}

REQUIRED_TEXT = {
    "firmware/esp32-dualeye/include/config.h": ["ESP32S3_DUALEYE_EXTERNAL_2G4_ANTENNA", "external_connector", "IPEX1/U.FL/MHF1"],
    "firmware/esp32-dualeye/src/main.cpp": ["antenna_status", "ESP32S3_DUALEYE_2G4_ANTENNA_MODE", "esp32_external_antenna"],
    "scripts/configure_esp32s3_dualeye_2g4_antenna.sh": ["ESP32-S3 DualEye", "external 2.4 GHz antenna", "logs/esp32s3_dualeye_2g4_antenna_status.json"],
    "scripts/flash_esp32.sh": ["configure_esp32s3_dualeye_2g4_antenna.sh", "esp32_external_antenna"],
    "production/WIRING_DIAGRAM_ANTENNAS.md": ["ESP32-S3 DualEye 2.4 GHz", "IPEX/U.FL/MHF1 coax pigtail", "external 2.4 GHz WiFi/Bluetooth antenna"],
    "docs/PRODUCTION_FILES.md": ["production/WIRING_DIAGRAM_ANTENNAS.md", "ESP32-S3 DualEye antenna rule", "external 2.4 GHz"],
    "production/RevA17-dongle-only/PRODUCTION_README_RevA17_DongleOnly.md": ["ESP32-S3 DualEye external 2.4 GHz antenna path", "production/WIRING_DIAGRAM_ANTENNAS.md", "esp32_external_antenna"],
}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def check_required_files(failures: list[str]) -> None:
    for relative_path in MAIN_REQUIRED_FILES:
        if not (REPO_ROOT / relative_path).exists():
            failures.append(f"missing required main file: {relative_path}")
    for relative_path in BRANCH_ONLY_PATHS:
        if (REPO_ROOT / relative_path).exists():
            failures.append(f"branch-only file still present on main: {relative_path}")


def check_required_text(failures: list[str]) -> None:
    for relative_path, needles in REQUIRED_TEXT.items():
        path = REPO_ROOT / relative_path
        text = read_text(path)
        for needle in needles:
            if needle not in text:
                failures.append(f"{relative_path} missing expected text: {needle}")


def check_no_branch_terms(failures: list[str]) -> None:
    ignored_dirs = {".git", ".pio", "build", "__pycache__", ".venv"}
    ignored_files = {"check_repo_readiness.py"}
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or path.name in ignored_files or any(part in ignored_dirs for part in path.parts):
            continue
        text = read_text(path)
        if not text:
            continue
        rel = str(path.relative_to(REPO_ROOT))
        for term in BRANCH_ONLY_TERMS:
            if term in text:
                failures.append(f"branch-only term still present in {rel}")
                break


def check_config(failures: list[str]) -> None:
    path = REPO_ROOT / "pi-companion" / "config.default.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"config.default.json is invalid JSON: {exc}")
        return
    menu = config.get("menu_selection", {})
    if menu.get("groups") != ["Bluetooth Tools", "CAN Bench Tools", "Reports & Reviews", "System / Companion"]:
        failures.append("menu groups do not match main branch layout")
    if menu.get("items") != EXPECTED_MENU_LABELS:
        failures.append("menu items do not match main branch ordering")
    if "killerkoala_companion" not in config or "koala_kan_kommander" not in config:
        failures.append("main config missing required companion or CAN plug-in section")


def check_menu_catalog(failures: list[str]) -> None:
    try:
        from koalablue.menu_catalog import MENU_GROUPS, menu_labels
    except Exception as exc:
        failures.append(f"failed to import menu catalog: {exc}")
        return
    if MENU_GROUPS != ["Bluetooth Tools", "CAN Bench Tools", "Reports & Reviews", "System / Companion"]:
        failures.append("menu catalog groups do not match main branch layout")
    if menu_labels() != EXPECTED_MENU_LABELS:
        failures.append("menu catalog labels do not match main branch ordering")


def check_bom(failures: list[str]) -> None:
    path = REPO_ROOT / "production" / "RevA17-dongle-only" / "BOM_RevA17_DongleOnly.csv"
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    except Exception as exc:
        failures.append(f"failed to read current BOM: {exc}")
        return
    actual = {row.get("Item", "").strip() for row in rows}
    missing = sorted(EXPECTED_BOM_ITEMS - actual)
    if missing:
        failures.append(f"current BOM missing items: {missing}")


def check_helpers(failures: list[str]) -> None:
    for helper in ["scripts/flash_all_components.sh", "scripts/build_firmware_all.sh", "scripts/setup_system_packages.sh", "scripts/configure_esp32s3_dualeye_2g4_antenna.sh"]:
        path = REPO_ROOT / helper
        if path.exists() and "set -euo pipefail" not in path.read_text(encoding="utf-8"):
            failures.append(f"shell helper missing strict shell mode: {helper}")


def main() -> int:
    failures: list[str] = []
    check_required_files(failures)
    check_required_text(failures)
    check_no_branch_terms(failures)
    check_config(failures)
    check_menu_catalog(failures)
    check_bom(failures)
    check_helpers(failures)

    if failures:
        print("KoalaByte Blue repo readiness check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("KoalaByte Blue repo readiness check passed.")
    print("Main branch is scoped to ESP32-S3 DualEye with external 2.4 GHz antenna support, Nordic nRF52840 Dongle, Raspberry Pi companion, optional InnoMaker USB-to-CAN, and USB power-bank production power.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
