#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = REPO_ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

REQUIRED_TEXT = {
    "README.md": ["RevA17", "killerkoala_voice", "Koala BlueZ Tools", "build_nrf52840_dk_lab.sh", "build_nrf52840_dongle_lab.sh", "check_repo_readiness.py"],
    "docs/FLASHING.md": ["check_repo_readiness.py", "build_nrf52840_dk_lab.sh", "build_nrf52840_dongle_lab.sh", "run_koala_bluez.py", "EarTag-TX-Lab"],
    "docs/NRF52840_DONGLE_FLASHING.md": ["nrf52840dongle_nrf52840", "flash_nrf52840_dongle_lab_dfu.sh", "EarTag-TX-Lab", "DFU"],
    "docs/KILLERKOALA_VOCABULARY_REVA17.md": ["Australian male", "Noob", "Hacker", "Legend", "KillerKoala Voice"],
    "docs/KOALA_BLUEZ_TOOLS_REVA16.md": ["Koala Blue Controller", "bluetoothctl", "btmon", "--owned-device"],
    "docs/EAR_TAG_TX_LAB_REVA15.md": ["EarTag-TX-Lab", "KBTX", "does not replay captured packets"],
    "firmware/esp32-dualeye/include/config.h": ["#define ENABLE_DISPLAY_BOOT_ANIMATION 1", "#define BOOT_ANIMATION_TOTAL_MS", "#define DISPLAY_ROTATION"],
    "firmware/esp32-dualeye/platformio.ini": ["bodmer/TFT_eSPI"],
    "firmware/esp32-dualeye/src/main.cpp": ['#include "boot_animation.h"', "setupDisplay();", "runBootAnimation();", 'doc["boot_animation"] = ENABLE_DISPLAY_BOOT_ANIMATION;'],
    "firmware/esp32-dualeye/src/boot_animation.cpp": ["void setupDisplay()", "void runBootAnimation()", "KoalaByte", "Blue", "BOOTING..."],
    "firmware/esp32-dualeye/include/menu_theme.h": ["drawEucalyptusMenuBorder", "drawJungleMenuTitle", "drawJungleMenuItem"],
    "firmware/esp32-dualeye/src/menu_theme.cpp": ["drawEucalyptusMenuBorder", "drawJungleMenuTitle", "drawJungleMenuItem", "drawBubbleText"],
    "firmware/nrf52840-dk-lab-peripheral/CMakeLists.txt": ["find_package(Zephyr REQUIRED", "target_sources(app PRIVATE src/main.c)"],
    "firmware/nrf52840-dk-lab-peripheral/prj.conf": ['CONFIG_BT_DEVICE_NAME="EarTag-TX-Lab"', "CONFIG_BT_PERIPHERAL=y"],
    "firmware/nrf52840-dk-lab-peripheral/src/main.c": ["Ear Tag TX Lab", "tx_lab_service_data", "KBTX", "sequence", "no captured packet replay", "bt_le_adv_start"],
    "pi-companion/koalablue/boot_animation.py": ["KoalaByte", "Blue"],
    "pi-companion/koalablue/bluez_tools.py": ["BLUEZ_TOOLS", "Koala Blue Controller", "bluetoothctl", "btmon", "owned_device_required"],
    "pi-companion/koalablue/ear_tag_tx_lab.py": ["EarTag-TX-Lab", "synthetic_owned_lab_ble_advertisement", "KBTX"],
    "pi-companion/koalablue/killerkoala_vocabulary.py": ["KillerKoalaVoiceProfile", "Australian male", "RANK_NOOB", "RANK_HACKER", "RANK_LEGEND", "line_for_event", "vocabulary_manifest"],
    "pi-companion/koalablue/koala_kapture.py": ["Koala Kapture", "passive"],
    "pi-companion/koalablue/koala_kry.py": ["Koala Kry", "request_rf_transmit", "KoalaKryTransmitReview", "blocked_no_over_the_air_replay", "--request-rf-transmit"],
    "pi-companion/koalablue/menu_catalog.py": ["Koala Kry RF Review", "Ear Tag TX Lab", "Koala BlueZ Scan", "KillerKoala Voice"],
    "pi-companion/koalablue/menu_theme.py": ["JungleMenuTheme", "JungleMenuRenderer", "render_terminal_jungle_menu", "eucalyptus_branches"],
    "pi-companion/koalablue/menu_ui.py": ["render_terminal_jungle_menu", "RevA14 jungle/eucalyptus theme"],
    "pi-companion/koalablue/menu_screen.py": ["render_terminal_jungle_menu"],
    "pi-companion/config.default.json": ["killerkoala_companion", "Australian male", "Koala BlueZ Tools", "KillerKoala Voice", "EarTag-TX-Lab"],
    "scripts/build_firmware_all.sh": ["pio run", "build_nrf52840_dk_lab.sh", "build_nrf52840_dongle_lab.sh"],
    "scripts/build_nrf52840_dk_lab.sh": ["west build", "nrf52840dk_nrf52840"],
    "scripts/build_nrf52840_dongle_lab.sh": ["west build", "nrf52840dongle_nrf52840"],
    "scripts/flash_nrf52840_dongle_lab_dfu.sh": ["nrfutil", "koalabyte-blue-nrf52840-dongle-dfu.zip", "NRF_DFU_PORT"],
    "scripts/flash_esp32.sh": ["pio run"],
    "scripts/flash_nrf52840_dk_lab.sh": ["west flash", "EarTag-TX-Lab"],
    "scripts/install_pi.sh": ["check_repo_readiness.py", "run_koala_bluez.py inventory", "run_killerkoala_voice.py status"],
    "scripts/run_boot_splash.py": ["run_boot_splash"],
    "scripts/run_ear_tag_tx_lab.py": ["run_cli"],
    "scripts/run_killerkoala_voice.py": ["killerkoala_vocabulary", "run_cli"],
    "scripts/run_koala_bluez.py": ["bluez_tools", "run_cli"],
    "scripts/run_menu_screen.py": ["--graphical", "JungleMenuRenderer"],
}

OBSOLETE_PATHS = [
    "docs/BEACON_RECORD_REPLAY_REVA12.md",
    "docs/KOALA_KRY_REVA11.md",
    "docs/MENU_SELECTION_SCREEN_REVA12.md",
    "docs/REVA12_CAPTURE_REPLAY_MENU_UPDATE.md",
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
    if companion.get("voice_profile", {}).get("accent") != "Australian male":
        failures.append("killerkoala voice profile accent is not Australian male")
    if companion.get("xp_ranks", {}).get("Legend", {}).get("min_xp") != 250:
        failures.append("killerkoala Legend XP threshold is not 250")

    if config.get("koala_kry", {}).get("rf_transmission") is not False:
        failures.append("Koala Kry must remain offline with rf_transmission=false")
    if config.get("ear_tag_tx_lab", {}).get("device_name") != "EarTag-TX-Lab":
        failures.append("Ear Tag TX Lab device_name must be EarTag-TX-Lab")


def check_menu_catalog(failures: list[str]) -> None:
    try:
        from koalablue.menu_catalog import menu_labels
    except Exception as exc:
        failures.append(f"failed to import menu catalog: {exc}")
        return
    labels = menu_labels()
    if labels != EXPECTED_MENU_LABELS:
        failures.append("menu_catalog.menu_labels() does not match RevA17 expected menu ordering")


def main() -> int:
    failures: list[str] = []
    check_required_text(failures)
    check_obsolete_paths(failures)
    check_json_config(failures)
    check_menu_catalog(failures)

    if failures:
        print("KoalaByte Blue repo readiness check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("KoalaByte Blue repo readiness check passed.")
    print("Ready-to-flash file wiring is present for ESP32, nRF52840 DK/Zephyr, nRF52840 Dongle/DFU, and Pi companion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
