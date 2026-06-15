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

REQUIRED_TEXT = {
    "README.md": ["RevA17", "killerkoala_voice", "Koala BlueZ Tools", "build_nrf52840_dongle_lab.sh", "check_repo_readiness.py"],
    "docs/FLASHING.md": ["check_repo_readiness.py", "build_nrf52840_dongle_lab.sh", "run_koala_bluez.py", "EarTag-TX-Lab"],
    "docs/NRF52840_DONGLE_FLASHING.md": ["nrf52840dongle_nrf52840", "flash_nrf52840_dongle_lab_dfu.sh", "EarTag-TX-Lab", "DFU"],
    "docs/KILLERKOALA_VOCABULARY_REVA17.md": ["Australian male", "Noob", "Hacker", "Legend", "KillerKoala Voice"],
    "docs/KOALA_BLUEZ_TOOLS_REVA16.md": ["Koala Blue Controller", "bluetoothctl", "btmon", "--owned-device"],
    "docs/EUCALYPTUS_ALWAYS_ON_BLE_REVA8.md": ["eucalyptus", "/blecaptures", "passive observation", "WiGLE"],
    "docs/EAR_TAG_TX_LAB_REVA15.md": ["EarTag-TX-Lab", "KBTX", "does not replay captured packets"],
    "docs/PRODUCTION_FILES.md": ["production/RevA17-dongle-only/", "BOM_RevA17_DongleOnly.csv", "Safety_Test_Record_RevA17.csv", "No custom PCB"],
    "firmware/esp32-dualeye/include/config.h": ["#define ENABLE_DISPLAY_BOOT_ANIMATION 1", "#define BOOT_ANIMATION_TOTAL_MS", "#define DISPLAY_ROTATION"],
    "firmware/esp32-dualeye/platformio.ini": ["bodmer/TFT_eSPI"],
    "firmware/esp32-dualeye/src/main.cpp": ['#include "boot_animation.h"', "setupDisplay();", "runBootAnimation();", 'doc["boot_animation"] = ENABLE_DISPLAY_BOOT_ANIMATION;'],
    "firmware/esp32-dualeye/src/boot_animation.cpp": ["void setupDisplay()", "void runBootAnimation()", "KoalaByte", "Blue", "BOOTING..."],
    "firmware/esp32-dualeye/include/menu_theme.h": ["drawEucalyptusMenuBorder", "drawJungleMenuTitle", "drawJungleMenuItem"],
    "firmware/esp32-dualeye/src/menu_theme.cpp": ["drawEucalyptusMenuBorder", "drawJungleMenuTitle", "drawJungleMenuItem", "drawBubbleText"],
    "firmware/nrf52840-dongle-ear-tag-tx-lab/CMakeLists.txt": ["find_package(Zephyr REQUIRED", "target_sources(app PRIVATE src/main.c)"],
    "firmware/nrf52840-dongle-ear-tag-tx-lab/prj.conf": ['CONFIG_BT_DEVICE_NAME="EarTag-TX-Lab"', "CONFIG_BT_PERIPHERAL=y"],
    "firmware/nrf52840-dongle-ear-tag-tx-lab/src/main.c": ["Ear Tag TX Lab", "tx_lab_service_data", "KBTX", "sequence", "no captured packet replay", "bt_le_adv_start"],
    "firmware/nrf52840-dongle-ear-tag-tx-lab/README.md": ["nRF52840 Dongle", "nrf52840dongle_nrf52840", "DFU", "EarTag-TX-Lab"],
    "pi-companion/koalablue/boot_animation.py": ["KoalaByte", "Blue"],
    "pi-companion/koalablue/bluez_tools.py": ["BLUEZ_TOOLS", "Koala Blue Controller", "bluetoothctl", "btmon", "owned_device_required"],
    "pi-companion/koalablue/ear_tag_tx_lab.py": ["EarTag-TX-Lab", "synthetic_owned_lab_ble_advertisement", "KBTX"],
    "pi-companion/koalablue/killerkoala_vocabulary.py": ["KillerKoalaVoiceProfile", "Australian male", "RANK_NOOB", "RANK_HACKER", "RANK_LEGEND", "line_for_event", "vocabulary_manifest"],
    "pi-companion/koalablue/koala_kapture.py": ["Koala Kapture", "passive", "run_cli"],
    "pi-companion/koalablue/koala_kry.py": ["Koala Kry", "request_rf_transmit", "KoalaKryTransmitReview", "blocked_no_over_the_air_replay", "--request-rf-transmit"],
    "pi-companion/koalablue/menu_catalog.py": ["Koala Kry RF Review", "Ear Tag TX Lab", "Koala BlueZ Scan", "KillerKoala Voice"],
    "pi-companion/koalablue/menu_theme.py": ["JungleMenuTheme", "JungleMenuRenderer", "render_terminal_jungle_menu", "eucalyptus_branches"],
    "pi-companion/koalablue/menu_ui.py": ["render_terminal_jungle_menu", "RevA14 jungle/eucalyptus theme"],
    "pi-companion/koalablue/menu_screen.py": ["render_terminal_jungle_menu"],
    "pi-companion/config.default.json": ["killerkoala_companion", "Australian male", "Koala BlueZ Tools", "KillerKoala Voice", "EarTag-TX-Lab", "eucalyptus"],
    "production/RevA17-dongle-only/BOM_RevA17_DongleOnly.csv": ["Raspberry Pi 3 Model B+", "PCA10059", "ESP32-S3 DualEye", "18650", "USB-C PD", "5 V 3 A buck", "No custom PCB"],
    "production/RevA17-dongle-only/PRODUCTION_README_RevA17_DongleOnly.md": ["Dongle-Only", "No custom PCB", "build_nrf52840_dongle_lab.sh", "flash_nrf52840_dongle_lab_dfu.sh", "eucalyptus", "Safety boundary"],
    "production/RevA17-dongle-only/Safety_Test_Record_RevA17.csv": ["5 V rail", "nRF52840 Dongle enumerates over USB", "eucalyptus /blecaptures write test", "Six-button GPIO test"],
    "scripts/build_firmware_all.sh": ["pio run", "build_nrf52840_dongle_lab.sh"],
    "scripts/build_nrf52840_dongle_lab.sh": ["west build", "nrf52840dongle_nrf52840", "firmware/nrf52840-dongle-ear-tag-tx-lab"],
    "scripts/flash_nrf52840_dongle_lab_dfu.sh": ["nrfutil", "koalabyte-blue-nrf52840-dongle-dfu.zip", "NRF_DFU_PORT"],
    "scripts/flash_esp32.sh": ["pio run"],
    "scripts/install_pi.sh": ["check_repo_readiness.py", "run_koala_bluez.py inventory", "run_killerkoala_voice.py status"],
    "scripts/run_boot_splash.py": ["run_boot_splash"],
    "scripts/run_ear_tag_tx_lab.py": ["run_cli"],
    "scripts/run_killerkoala_voice.py": ["killerkoala_vocabulary", "run_cli"],
    "scripts/run_koala_bluez.py": ["bluez_tools", "run_cli"],
    "scripts/run_koala_kapture.py": ["koala_kapture", "run_cli"],
    "scripts/run_menu_screen.py": ["--graphical", "JungleMenuRenderer"],
}

OBSOLETE_PATHS = [
    "docs/BEACON_RECORD_REPLAY_REVA12.md",
    "docs/KOALA_KRY_REVA11.md",
    "docs/MENU_SELECTION_SCREEN_REVA12.md",
    "docs/REVA12_CAPTURE_REPLAY_MENU_UPDATE.md",
    "docs/NRF52840_DK_FLASHING.md",
    "docs/NRF52840_DK_OPTION_REVA4.md",
    "firmware/nrf52840-dk-lab-peripheral/CMakeLists.txt",
    "firmware/nrf52840-dk-lab-peripheral/prj.conf",
    "firmware/nrf52840-dk-lab-peripheral/src/main.c",
    "firmware/nrf52840-dk-lab-peripheral/README.md",
    "scripts/build_nrf52840_dk_lab.sh",
    "scripts/flash_nrf52840_dk_lab.sh",
    "production/RevA1-nrf52840-dongle/BOM_RevA1.csv",
    "production/RevA1-nrf52840-dongle/BOM_RevA2_power_update.csv",
    "production/RevA1-nrf52840-dongle/BOM_RevA4_Dongle_Plus_DK.csv",
    "production/RevA1-nrf52840-dongle/BOM_RevA5_Dongle_DK_Buttons.csv",
    "production/RevA1-nrf52840-dongle/BOM_RevA11_Physical_Build.csv",
    "production/RevA1-nrf52840-dongle/ASSEMBLY_AND_FLASHING_INSTRUCTIONS_RevA5_BUTTONS.md",
    "production/RevA1-nrf52840-dongle/Safety_Test_Record_RevA1.csv",
    "production/RevA11-no-nrf-no-generic-lcd/BOM_RevA11_NoNRF_NoGenericLCD.csv",
    "production/RevA11-no-nrf-no-generic-lcd/README_RevA11_NoNRF_NoGenericLCD.md",
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
    "BOM_RevA1.csv",
    "BOM_RevA11_NoNRF_NoGenericLCD",
]

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
    "Ear Tag TX Lab",
    "Koala BlueZ Inventory",
    "Koala BlueZ Status",
    "Koala BlueZ Scan",
    "Koala BlueZ Monitor",
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
    "USB-C PD charging module",
    "5 V 3 A buck converter",
    "Inline rated power switch",
    "microSD card",
    "USB and JST power/data cables",
    "M2.5 standoffs / screws / nuts",
    "Acrylic or printed frame plates",
    "3D printed case / stacked frame / rear panel",
    "Cable management / strain relief",
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
        if not path.is_file():
            continue
        if any(part in ignored_dirs for part in path.parts):
            continue
        if path.name in ignored_files:
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

    menu_items = config.get("menu_selection", {}).get("items", [])
    if menu_items != EXPECTED_MENU_LABELS:
        failures.append("menu_selection.items does not match the RevA17 expected menu ordering")

    companion = config.get("killerkoala_companion", {})
    if companion.get("display_name") != "killerkoala":
        failures.append("killerkoala companion display_name is not killerkoala")
    if companion.get("voice_profile", {}).get("accent") != "Australian male":
        failures.append("killerkoala voice profile accent is not Australian male")
    if companion.get("xp_ranks", {}).get("Hacker", {}).get("min_xp") != 75:
        failures.append("killerkoala Hacker XP threshold is not 75")
    if companion.get("xp_ranks", {}).get("Legend", {}).get("min_xp") != 250:
        failures.append("killerkoala Legend XP threshold is not 250")

    eucalyptus = config.get("eucalyptus", {})
    if eucalyptus.get("display_name") != "eucalyptus":
        failures.append("eucalyptus display_name is not eucalyptus")
    if eucalyptus.get("enabled") is not True:
        failures.append("eucalyptus must be enabled in the default config")
    if eucalyptus.get("capture_dir") != "/blecaptures":
        failures.append("eucalyptus capture_dir must be /blecaptures")
    if eucalyptus.get("mode") != "passive_ble_observation":
        failures.append("eucalyptus mode must be passive_ble_observation")
    if eucalyptus.get("wigle_upload_enabled") is not False:
        failures.append("default WiGLE upload must remain disabled until configured by the user")

    if config.get("koala_kry", {}).get("rf_transmission") is not False:
        failures.append("Koala Kry must remain offline with rf_transmission=false")
    if config.get("ear_tag_tx_lab", {}).get("device_name") != "EarTag-TX-Lab":
        failures.append("Ear Tag TX Lab device_name must be EarTag-TX-Lab")
    if config.get("ear_tag_tx_lab", {}).get("firmware_path") != "firmware/nrf52840-dongle-ear-tag-tx-lab":
        failures.append("Ear Tag TX Lab firmware_path must point to the dongle-only firmware path")


def check_menu_catalog(failures: list[str]) -> None:
    try:
        from koalablue.menu_catalog import menu_labels
    except Exception as exc:
        failures.append(f"failed to import menu catalog: {exc}")
        return
    labels = menu_labels()
    if labels != EXPECTED_MENU_LABELS:
        failures.append("menu_catalog.menu_labels() does not match RevA17 expected menu ordering")


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

    text = path.read_text(encoding="utf-8")
    for legacy in ("Development BLE board", "3.5 in HDMI/USB touch LCD", "generic touchscreen", "BOM_RevA1"):
        if legacy in text:
            failures.append(f"current BOM contains obsolete production wording: {legacy}")


def main() -> int:
    failures: list[str] = []
    check_required_text(failures)
    check_obsolete_paths(failures)
    check_forbidden_text(failures)
    check_json_config(failures)
    check_menu_catalog(failures)
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
