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
    "Scan",
    "Summary",
    "Show Devices",
    "eucalyptus Status",
    "eucalyptus Start",
    "eucalyptus Stop",
    "eucalyptus Restart",
    "eucalyptus Upload Status",
    "Koala Kapture",
    "Koala Kry",
    "Koala Kry RF Review",
    "Ear Tag",
    "KoalaByte Lab",
    "Koala Mode Switcher",
    "Gumleaf Gear Check",
    "Eucalyptus Bus Scout",
    "Dropbear Discovery Sweep",
    "Billabong HCI Watch",
    "Kookaburra Safe Nest Run",
    "KillerKoala Voice",
    "Urban Poaching",
    "Buttons",
    "Level / Status",
    "Report",
    "Wake killerkoala",
    "Authorized BLE Inventory",
    "GATT Readiness Checklist",
    "Pairing Security Review",
    "Lab Beacon Plan",
    "Packet Capture Notes",
    "Defensive Lab Report",
    "Restricted Placeholder",
    "Settings",
    "Lab",
    "Shutdown",
    "Quit",
]

SELOKY_PD_ITEM = "Seloky USB-C PD Trigger Board Module PD/QC Decoy Fast Charge USB Type-C to 12V"

EXPECTED_BOM_ITEMS = [
    "Raspberry Pi 3 Model B+",
    "Nordic nRF52840 USB Dongle / PCA10059 / NRF52840-DONGLE",
    "ESP32-S3 DualEye module",
    "1.28 inch round LCD display",
    "8 ohm 2 W mini speaker",
    "2.4 GHz external antenna",
    "Adafruit tactile button switch 6mm pack PID 367",
    "KoalaByte Blue front button bezel 6x6mm RevA6",
    "Protected 18650 Li-ion cell",
    "2x18650 holder with protection / BMS",
    SELOKY_PD_ITEM,
    "5 V 3 A buck converter",
    "Inline rated power switch",
    "microSD card",
    "USB and JST power/data cables",
    "M2.5 standoffs / screws / nuts",
    "Acrylic or printed frame plates",
    "3D printed case / stacked frame / rear panel",
    "Cable management / strain relief",
]

REQUIRED_TEXT = {
    "README.md": ["RevA18", "Outback BlueZ Module Deck", "Gumleaf Gear Check", "build_nrf52840_dongle_lab.sh"],
    "docs/FLASHING.md": ["Outback BlueZ Module Deck", "check_repo_readiness.py", "run_koala_bluez.py", "KoalaByte Lab"],
    "docs/KOALA_BLUEZ_TOOLS_REVA16.md": ["RevA18 Outback BlueZ Module Deck", "Gumleaf Gear Check", "Eucalyptus Bus Scout", "--owned-device"],
    "docs/NRF52840_DONGLE_FLASHING.md": ["nrf52840dongle_nrf52840", "flash_nrf52840_dongle_lab_dfu.sh", "DFU"],
    "docs/EAR_TAG_TX_LAB_REVA15.md": ["KoalaByte Lab", "KBTX", "does not replay captured packets"],
    "docs/KOALA_KONNECT_REVA20.md": ["Koala Konnect", "hci_usb", "koala-konnect-nrf52840-dongle-dfu.zip"],
    "docs/ORDERABLE_PARTS_LIST.md": ["Seloky USB-C PD Trigger Board", "12V", "Do not connect 12V directly to the Pi"],
    "docs/POWER_UPDATE_REVA2.md": ["Seloky USB-C PD/QC 12V trigger board", "Replaces the prior USB-C PD breakout reference", "Verify 12V output"],
    "docs/PRODUCTION_FILES.md": ["production/RevA17-dongle-only/", "BOM_RevA17_DongleOnly.csv", "No custom PCB"],
    "production/RevA17-dongle-only/BOM_RevA17_DongleOnly.csv": ["Seloky USB-C PD Trigger Board Module", "12 V PD-QC trigger"],
    "production/RevA17-dongle-only/PRODUCTION_README_RevA17_DongleOnly.md": ["Seloky", "12 V", "5 V buck converter"],
    "firmware/esp32-dualeye/platformio.ini": ["bodmer/TFT_eSPI"],
    "firmware/esp32-dualeye/src/main.cpp": ["runBootAnimation();", "ENABLE_DISPLAY_BOOT_ANIMATION"],
    "firmware/nrf52840-dongle-ear-tag-tx-lab/CMakeLists.txt": ["find_package(Zephyr REQUIRED", "target_sources(app PRIVATE src/main.c)"],
    "firmware/nrf52840-dongle-ear-tag-tx-lab/prj.conf": ["KoalaByte Lab", "CONFIG_BT_PERIPHERAL=y"],
    "firmware/nrf52840-dongle-ear-tag-tx-lab/src/main.c": ["KBTX", "bt_le_adv_start", "no captured packet replay"],
    "pi-companion/koalablue/bluez_tools.py": ["BLUEZ_MODULES", "Gumleaf Gear Check", "Eucalyptus Bus Scout", "Billabong HCI Watch", "owned_device_required"],
    "pi-companion/koalablue/menu_catalog.py": ["Koala Mode Switcher", "KoalaByte Lab", "Gumleaf Gear Check", "Dropbear Discovery Sweep", "Kookaburra Safe Nest Run"],
    "pi-companion/koalablue/koala_mode_switcher.py": ["Koala Mode Switcher", "KoalaByte Lab", "Koala Konnect", "dongle_mode_state.json"],
    "pi-companion/config.default.json": ["Outback BlueZ Module Deck", "Gumleaf Gear Check", "KoalaByte Lab", "Koala Mode Switcher", "killerkoala_companion"],
    "scripts/build_firmware_all.sh": ["pio run", "build_nrf52840_dongle_lab.sh"],
    "scripts/build_nrf52840_dongle_lab.sh": ["west build", "nrf52840dongle_nrf52840", "firmware/nrf52840-dongle-ear-tag-tx-lab"],
    "scripts/build_koala_konnect.sh": ["build_nrf52840_dongle_hci_usb_adapter.sh"],
    "scripts/flash_koala_konnect.sh": ["flash_nrf52840_dongle_koala_konnect_dfu.sh"],
    "scripts/flash_nrf52840_dongle_lab_dfu.sh": ["nrfutil", "koalabyte-blue-nrf52840-dongle-dfu.zip", "NRF_DFU_PORT"],
    "scripts/flash_esp32.sh": ["pio run"],
    "scripts/install_pi.sh": ["check_repo_readiness.py", "run_koala_bluez.py manifest", "Gumleaf Gear Check"],
    "scripts/run_koala_bluez.py": ["bluez_tools", "run_cli"],
    "scripts/run_koala_mode_switcher.py": ["koala_mode_switcher", "run_cli"],
    "scripts/run_koala_bluez_manifest.sh": ["run_koala_bluez.py", "manifest"],
    "scripts/run_koala_bluez_all_safe.sh": ["run_koala_bluez.py", "all-safe"],
    "scripts/run_koala_bluez_gatt_readiness.sh": ["run_koala_bluez.py", "gatt-readiness"],
}

OBSOLETE_PATHS = [
    "docs/NRF52840_DK_FLASHING.md",
    "docs/NRF52840_DK_OPTION_REVA4.md",
    "firmware/nrf52840-dk-lab-peripheral/CMakeLists.txt",
    "firmware/nrf52840-dk-lab-peripheral/prj.conf",
    "firmware/nrf52840-dk-lab-peripheral/src/main.c",
    "firmware/nrf52840-dk-lab-peripheral/README.md",
    "scripts/build_nrf52840_dk_lab.sh",
    "scripts/flash_nrf52840_dk_lab.sh",
    "production/RevA1-nrf52840-dongle/BOM_RevA1.csv",
    "production/RevA1-nrf52840-dongle/ORDERABLE_PARTS_LIST_RevA3.csv",
    "production/RevA11-no-nrf-no-generic-lcd/BOM_RevA11_NoNRF_NoGenericLCD.csv",
]

FORBIDDEN_TEXT = [
    "nrf52840dk_nrf52840",
    "PCA10056",
    "nRF52840 DK",
    "build_nrf52840_dk_lab.sh",
    "flash_nrf52840_dk_lab.sh",
    "firmware/nrf52840-dk-lab-peripheral",
    "production/RevA1-nrf52840-dongle",
    "production/RevA11-no-nrf-no-generic-lcd",
    "HUSB238",
    "USB Type C Power Delivery Dummy Breakout",
    "Adafruit Product ID 5807",
    "EarTag-TX-Lab",
    "Ear Tag TX Lab",
    "USB-C PD charging module",
]


def check_required_text(failures: list[str]) -> None:
    for relative_path, needles in REQUIRED_TEXT.items():
        path = REPO_ROOT / relative_path
        if not path.exists():
            failures.append(f"missing required file: {relative_path}")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                failures.append(f"missing '{needle}' in {relative_path}")


def check_obsolete_paths(failures: list[str]) -> None:
    for relative_path in OBSOLETE_PATHS:
        if (REPO_ROOT / relative_path).exists():
            failures.append(f"obsolete file still present: {relative_path}")


def check_forbidden_text(failures: list[str]) -> None:
    ignored_dirs = {".git", ".pio", "build", "__pycache__", ".venv"}
    ignored_files = {"check_repo_readiness.py"}
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or any(part in ignored_dirs for part in path.parts) or path.name in ignored_files:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = str(path.relative_to(REPO_ROOT))
        for needle in FORBIDDEN_TEXT:
            if needle in text:
                failures.append(f"forbidden legacy reference '{needle}' found in {rel}")


def check_json_config(failures: list[str]) -> None:
    path = REPO_ROOT / "pi-companion" / "config.default.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"config.default.json is invalid JSON: {exc}")
        return

    if config.get("menu_selection", {}).get("items", []) != EXPECTED_MENU_LABELS:
        failures.append("menu_selection.items does not match the RevA21 expected menu ordering")

    koala_bluez = config.get("koala_bluez", {})
    if koala_bluez.get("display_name") != "Outback BlueZ Module Deck":
        failures.append("koala_bluez display_name must be Outback BlueZ Module Deck")
    if koala_bluez.get("redact_addresses_by_default") is not True:
        failures.append("Outback BlueZ Module Deck must redact/hash addresses by default")
    expected_tools = {
        "inventory": "Gumleaf Gear Check",
        "status": "Eucalyptus Bus Scout",
        "scan": "Dropbear Discovery Sweep",
        "monitor": "Billabong HCI Watch",
        "gatt-readiness": "Gumnut GATT Readiness",
        "all-safe": "Kookaburra Safe Nest Run",
    }
    for key, label in expected_tools.items():
        if koala_bluez.get("tools", {}).get(key) != label:
            failures.append(f"koala_bluez.tools.{key} must be {label}")

    companion = config.get("killerkoala_companion", {})
    if companion.get("display_name") != "killerkoala":
        failures.append("killerkoala companion display_name is not killerkoala")
    if companion.get("voice_profile", {}).get("accent") != "Australian male":
        failures.append("killerkoala voice profile accent is not Australian male")
    if config.get("koala_kry", {}).get("rf_transmission") is not False:
        failures.append("Koala Kry must remain offline with rf_transmission=false")
    lab_mode = config.get("ear_tag_tx_lab", {})
    if lab_mode.get("firmware_path") != "firmware/nrf52840-dongle-ear-tag-tx-lab":
        failures.append("KoalaByte Lab firmware_path must point to the dongle-only firmware path")
    if lab_mode.get("display_name") != "KoalaByte Lab" or lab_mode.get("device_name") != "KoalaByte Lab":
        failures.append("KoalaByte Lab display_name/device_name must be KoalaByte Lab")
    switcher = config.get("koala_mode_switcher", {})
    if switcher.get("display_name") != "Koala Mode Switcher":
        failures.append("koala_mode_switcher display_name must be Koala Mode Switcher")
    if switcher.get("default_mode") != "koalabyte_lab":
        failures.append("Koala Mode Switcher default_mode must be koalabyte_lab")


def check_menu_catalog(failures: list[str]) -> None:
    try:
        from koalablue.menu_catalog import menu_labels
    except Exception as exc:
        failures.append(f"failed to import menu catalog: {exc}")
        return
    if menu_labels() != EXPECTED_MENU_LABELS:
        failures.append("menu_catalog.menu_labels() does not match RevA21 expected menu ordering")


def check_bluez_module_registry(failures: list[str]) -> None:
    try:
        from koalablue.bluez_tools import BLUEZ_MODULES, BLUEZ_TOOLS, redact_addresses
    except Exception as exc:
        failures.append(f"failed to import Outback BlueZ Module Deck: {exc}")
        return
    titles = {module.theme_title for module in BLUEZ_MODULES}
    for title in {"Gumleaf Gear Check", "Eucalyptus Bus Scout", "Dropbear Discovery Sweep", "Billabong HCI Watch", "Kookaburra Safe Nest Run"}:
        if title not in titles:
            failures.append(f"Outback BlueZ module registry missing title: {title}")
    helper_names = {tool.koala_name for tool in BLUEZ_TOOLS}
    if "Eucalyptus D-Bus Scout" not in helper_names:
        failures.append("BlueZ helper registry missing Eucalyptus D-Bus Scout")
    if "AA:BB:CC:DD:EE:FF" in redact_addresses("AA:BB:CC:DD:EE:FF"):
        failures.append("BlueZ address redaction did not hash a sample address")


def check_current_bom(failures: list[str]) -> None:
    path = REPO_ROOT / "production" / "RevA17-dongle-only" / "BOM_RevA17_DongleOnly.csv"
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    except Exception as exc:
        failures.append(f"failed to read current BOM: {exc}")
        return
    actual_items = {row.get("Item", "").strip() for row in rows}
    for item in EXPECTED_BOM_ITEMS:
        if item not in actual_items:
            failures.append(f"current BOM missing item: {item}")
    if len(rows) != len(EXPECTED_BOM_ITEMS):
        failures.append(f"current BOM should have {len(EXPECTED_BOM_ITEMS)} item rows; found {len(rows)}")


def main() -> int:
    failures: list[str] = []
    check_required_text(failures)
    check_obsolete_paths(failures)
    check_forbidden_text(failures)
    check_json_config(failures)
    check_menu_catalog(failures)
    check_bluez_module_registry(failures)
    check_current_bom(failures)

    if failures:
        print("KoalaByte Blue repo readiness check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("KoalaByte Blue repo readiness check passed.")
    print("Ready-to-flash file wiring is present for ESP32, nRF52840 Dongle/DFU, and Pi companion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
