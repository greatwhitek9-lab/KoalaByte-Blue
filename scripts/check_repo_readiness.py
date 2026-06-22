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
    "that’s not a knife", "AntEater", "KillerKoala Voice", "Urban Poaching", "Buttons", "Level / Status", "Report", "Boomerang", "Wake killerkoala",
    "Authorized BLE Inventory", "GATT Readiness Checklist", "Pairing Security Review", "Lab Beacon Plan", "Packet Capture Notes", "Defensive Lab Report",
    "Restricted Placeholder", "Settings", "Lab", "Shutdown", "Quit",
]

MAIN_REQUIRED_FILES = [
    "README.md",
    "docs/PRODUCTION_FILES.md",
    "docs/ORDERABLE_PARTS_LIST.md",
    "docs/POWER_BANK_WIRING_MAIN.svg",
    "docs/KILLERKOALA_VOCABULARY_REVA17.md",
    "docs/KILLERKOALA_LORA_TRAINING.md",
    "docs/ESP32_CUSTOM_ANIMATED_EYES.md",
    "docs/ANTEATER_BLE_CARD_SKIMMER_DETECTOR.md",
    "docs/MAIN_BLE_NODE_ROLES.md",
    "production/WIRING_DIAGRAM_ANTENNAS.md",
    "production/WIRING_DIAGRAM_ANTENNAS.svg",
    "production/RevA17-dongle-only/BOM_RevA17_DongleOnly.csv",
    "production/RevA17-dongle-only/PRODUCTION_README_RevA17_DongleOnly.md",
    "production/RevA17-dongle-only/BATTERY_POWER_2S_18650.md",
    "production/RevA17-dongle-only/Safety_Test_Record_RevA17.csv",
    "firmware/esp32-dualeye/platformio.ini",
    "firmware/esp32-dualeye/include/config.h",
    "firmware/esp32-dualeye/src/main.cpp",
    "firmware/esp32-dualeye/src/koalagotchi_mode_screens.h",
    "firmware/esp32-dualeye/src/koalagotchi_mode_screens.cpp",
    "firmware/esp32-dualeye/voice_commands/README.md",
    "firmware/esp32-dualeye/voice_commands/killerkoala_multinet_aliases.csv",
    "firmware/nrf52840-dongle-ear-tag-tx-lab/CMakeLists.txt",
    "firmware/nrf52840-dongle-ble-primary/CMakeLists.txt",
    "firmware/nrf52840-dongle-ble-primary/prj.conf",
    "firmware/nrf52840-dongle-ble-primary/src/main.c",
    "pi-companion/config.default.json",
    "pi-companion/requirements.txt",
    "pi-companion/koalablue/__init__.py",
    "pi-companion/koalablue/menu_catalog.py",
    "pi-companion/koalablue/killerkoala_vocabulary.py",
    "pi-companion/koalablue/killerkoala_hybrid_companion.py",
    "pi-companion/koalablue/anteater.py",
    "pi-companion/koalablue/ble_event_log.py",
    "pi-companion/koalablue/ble_node_manager.py",
    "pi-companion/koalablue/koala_kan_kommander.py",
    "scripts/configure_esp32s3_dualeye_2g4_antenna.sh",
    "scripts/flash_all_components.sh",
    "scripts/build_firmware_all.sh",
    "scripts/install_pi.sh",
    "scripts/setup_system_packages.sh",
    "scripts/setup_can0.sh",
    "scripts/setup_vcan0.sh",
    "scripts/install_can0_service.sh",
    "scripts/run_can0_service.sh",
    "scripts/install_koalabyte_udev_rules.sh",
    "scripts/discover_koalabyte_ports.py",
    "scripts/preflight_all_hardware.py",
    "scripts/preflight_all_hardware.sh",
    "scripts/build_nrf52840_dongle_ble_primary.sh",
    "scripts/flash_nrf52840_dongle_ble_primary_dfu.sh",
    "scripts/run_ble_node_manager.py",
    "scripts/run_ble_node_manager_service.sh",
    "scripts/install_ble_node_manager_service.sh",
    "scripts/run_koala_kan_kommander.py",
    "scripts/run_killerkoala_voice.py",
    "scripts/run_killerkoala_hybrid.py",
    "scripts/set_esp32_eyes.py",
    "scripts/run_anteater.py",
    "scripts/run_menu_screen.py",
    "training/killerkoala_lora/Modelfile.killerkoala-tinyllama",
]

BRANCH_ONLY_PATHS = [
    "docs/" + "DIDGER" + "IDOO_" + "LO" + "RA_SETUP.md",
    "docs/NRF52840_" + "T" + "114_ALT_TARGET.md",
    "docs/" + "T" + "114_WHOLE_FIRMWARE_TEST.md",
    "scripts/run_" + "didgeri" + "doo.py",
    "pi-companion/koalblue/killerkoala_hybrid_companion.py",
    "pi-companion/koalablue/koala_kan_firmware.py",
    "scripts/run_koala_kan_firmware.py",
    "firmware/innomaker-can-commander/README.md",
]

BRANCH_ONLY_TERMS = [
    "Hel" + "tec",
    "Mesh" + "tastic",
    "didgeri" + "doo",
    "LoRa antenna",
    "LoRa/GNSS",
    "LoRa / Mesh",
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
    "firmware/esp32-dualeye/include/config.h": ["ESP32S3_DUALEYE_EXTERNAL_2G4_ANTENNA", "ESP32S3_VOICE_FRONTEND_STACK", "MultiNet7 Q8 English"],
    "firmware/esp32-dualeye/src/main.cpp": ["voice_stack", "custom_animated_eyes", "eye_style_ack", "setKoalagotchiEyeStyle"],
    "firmware/esp32-dualeye/src/koalagotchi_mode_screens.h": ["setKoalagotchiEyeStyle", "tickKoalagotchiEyes", "getKoalagotchiLeftEyeHex"],
    "firmware/esp32-dualeye/src/koalagotchi_mode_screens.cpp": ["EyeState", "drawOneEye", "tickKoalagotchiEyes", "scan", "glitch"],
    "firmware/esp32-dualeye/voice_commands/README.md": ["WakeNet9", "MultiNet7 Q8 English", "Large Aussie/cyberpunk vocabulary pack"],
    "firmware/esp32-dualeye/voice_commands/killerkoala_multinet_aliases.csv": ["give the air a squiz", "suss the bluetooth stack", "bag the beacons"],
    "firmware/nrf52840-dongle-ble-primary/CMakeLists.txt": ["project(koalabyte_blue_nrf52840_dongle_ble_primary)", "target_sources(app PRIVATE src/main.c)"],
    "firmware/nrf52840-dongle-ble-primary/prj.conf": ["CONFIG_BT=y", "CONFIG_BT_OBSERVER=y", "CONFIG_USB_DEVICE_STACK=y", "CONFIG_USB_CDC_ACM=y"],
    "firmware/nrf52840-dongle-ble-primary/src/main.c": ["nRF52840 Dongle BLE-primary observer", "bt_le_scan_start", "ble_adv_seen", "memcmp(&a->a, &b->a"],
    "pi-companion/requirements.txt": ["python-can"],
    "pi-companion/koalablue/killerkoala_vocabulary.py": ["RECENT_HISTORY_WINDOW", "AUSSIE_TERMS", "anti_repeat_policy", "estimated_total_lines"],
    "pi-companion/koalablue/killerkoala_hybrid_companion.py": ["killerkoala-tinyllama:latest", "phrase_engine", "fallback_reason", "KILLERKOALA_LLM_MODE"],
    "pi-companion/koalablue/anteater.py": ["ACTION_NAME = \"AntEater\"", "BLEAK", "advertisement", "skimmer"],
    "pi-companion/koalablue/ble_event_log.py": ["BleEventLog", "BleEventDeduper", "normalize_ble_event", "source"],
    "pi-companion/koalablue/ble_node_manager.py": ["nrf52840-dongle", "PiBluezSecondaryScanner", "BleEventDeduper", "ble_adv_seen"],
    "pi-companion/koalablue/koala_kan_kommander.py": ["Koala Kan Kommander", "InnoMaker USB to CAN Converter kit", "manifest", "inventory", "status", "transmit_requires_bench_simulator"],
    "scripts/run_anteater.py": ["koalablue.anteater", "run_cli"],
    "scripts/run_koala_kan_kommander.py": ["koalablue.koala_kan_kommander", "run_cli"],
    "scripts/run_ble_node_manager.py": ["--dongle-port", "--esp32-port", "--no-pi-bluez", "BleNodeManager"],
    "scripts/run_ble_node_manager_service.sh": ["/dev/koalabyte-nrf-ble", "koalabyte_ports.env", "run_ble_node_manager.py"],
    "scripts/install_ble_node_manager_service.sh": ["systemd-udev-settle.service", "koalabyte_ports.env", "KOALABYTE_NRF_BLE_PORT"],
    "scripts/build_nrf52840_dongle_ble_primary.sh": ["nrf52840-dongle-ble-primary", "west build", "firmware/nrf52840-dongle-ble-primary"],
    "scripts/flash_nrf52840_dongle_ble_primary_dfu.sh": ["koalabyte-blue-nrf52840-dongle-ble-primary-dfu.zip", "NRF_DFU_PORT", "STRICT_NRF_DFU_PORT", "nrf52840_dongle_ble_primary_dfu_status.json"],
    "docs/MAIN_BLE_NODE_ROLES.md": ["nRF52840 Dongle", "primary", "ESP32-S3", "Raspberry Pi"],
    "docs/ANTEATER_BLE_CARD_SKIMMER_DETECTOR.md": ["AntEater", "BLE Card Skimmer", "advertisement-only", "no pairing"],
    "docs/ESP32_CUSTOM_ANIMATED_EYES.md": ["Supported looks", "Supported animations", "scripts/set_esp32_eyes.py", "PlatformIO"],
    "docs/KILLERKOALA_VOCABULARY_REVA17.md": ["large vocabulary engine", "anti-repeat phrase rotation", "killerkoala_multinet_aliases.csv"],
    "docs/KILLERKOALA_LORA_TRAINING.md": ["does **not** rely only on an LLM", "anti-repeat phrase engine", "KILLERKOALA_LLM_MODE"],
    "scripts/run_killerkoala_voice.py": ["killerkoala_voice_control", "run_cli"],
    "scripts/run_killerkoala_hybrid.py": ["killerkoala_hybrid_companion", "run_cli"],
    "scripts/set_esp32_eyes.py": ["PRESETS", "pyserial", "eye_style", "preview-only"],
    "scripts/flash_all_components.sh": ["RUN_AI_VOICE", "--ai-voice", "setup_esp32_tools.sh", "flash_all_ai_voice_preview.json", "RUN_NRF_BLE_PRIMARY", "--nrf-ble-primary", "RUN_BLE_NODE_MANAGER", "--ble-node-manager", "RUN_CAN_CHECK", "--can-check", "setup_can0.sh", "run_koala_kan_kommander.py manifest", "run_koala_kan_kommander.py inventory", "run_koala_kan_kommander.py status"],
    "scripts/setup_can0.sh": ["for module in can can_raw can_dev", "ip link set \"${INTERFACE}\" type can bitrate", "firmware_flash_required", "Koala Kan Kommander CAN setup"],
    "scripts/setup_system_packages.sh": ["can-utils", "python3-can", "cansend", "udev", "iproute2"],
    "scripts/install_koalabyte_udev_rules.sh": ["/dev/koalabyte-nrf-ble", "/dev/koalabyte-esp32-eyes", "/dev/koalabyte-heltec", "99-koalabyte.rules"],
    "scripts/discover_koalabyte_ports.py": ["KOALABYTE_NRF_BLE_PORT", "KOALABYTE_ESP32_FACE_PORT", "CAN_INTERFACE", "koalabyte_ports.env"],
    "scripts/install_can0_service.sh": ["koalabyte-can0.service", "run_can0_service.sh", "CAN_INTERFACE", "CAN_BITRATE"],
    "scripts/run_can0_service.sh": ["setup_can0.sh", "koalabyte_ports.env", "CAN_INTERFACE", "CAN_BITRATE"],
    "scripts/setup_vcan0.sh": ["vcan0", "modprobe vcan", "Koala Kan local software self-test"],
    "scripts/preflight_all_hardware.py": ["hardware_report.json", "discover_koalabyte_ports.py", "setup_vcan0.sh", "python_can_present"],
    "scripts/preflight_all_hardware.sh": ["preflight_all_hardware.py"],
    "training/killerkoala_lora/Modelfile.killerkoala-tinyllama": ["FROM tinyllama:1.1b", "PARAMETER num_ctx 1024", "KillerKoala"],
    "scripts/flash_esp32.sh": ["configure_esp32s3_dualeye_2g4_antenna.sh", "voice_stack", "MultiNet7 Q8 English"],
    "scripts/setup_esp32_tools.sh": ["PlatformIO", "pip install", "platformio"],
    "scripts/configure_esp32s3_dualeye_2g4_antenna.sh": ["ESP32-S3 DualEye", "external 2.4 GHz antenna", "logs/esp32s3_dualeye_2g4_antenna_status.json"],
    "production/WIRING_DIAGRAM_ANTENNAS.md": ["ESP32-S3 DualEye 2.4 GHz", "IPEX/U.FL/MHF1 coax pigtail", "external 2.4 GHz WiFi/Bluetooth antenna"],
    "docs/PRODUCTION_FILES.md": ["production/WIRING_DIAGRAM_ANTENNAS.md", "ESP32-S3 DualEye antenna rule", "external 2.4 GHz"],
    "production/RevA17-dongle-only/PRODUCTION_README_RevA17_DongleOnly.md": ["ESP32-S3 DualEye external 2.4 GHz antenna path", "production/WIRING_DIAGRAM_ANTENNAS.md", "esp32_external_antenna"],
    "pi-companion/koalablue/menu_catalog.py": ["AntEater", "anteater"],
    "scripts/run_menu_screen.py": ["run_anteater_action", "anteater"],
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
            failures.append(f"experimental/branch-only file still present on main: {relative_path}")


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
    for section in ["killerkoala_companion", "koala_kan_kommander", "anteater"]:
        if section not in config:
            failures.append(f"main config missing required section: {section}")


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
    shell_helpers = [
        "scripts/flash_all_components.sh",
        "scripts/build_firmware_all.sh",
        "scripts/setup_system_packages.sh",
        "scripts/setup_esp32_tools.sh",
        "scripts/configure_esp32s3_dualeye_2g4_antenna.sh",
        "scripts/setup_can0.sh",
        "scripts/setup_vcan0.sh",
        "scripts/install_can0_service.sh",
        "scripts/run_can0_service.sh",
        "scripts/install_koalabyte_udev_rules.sh",
        "scripts/preflight_all_hardware.sh",
        "scripts/build_nrf52840_dongle_ble_primary.sh",
        "scripts/flash_nrf52840_dongle_ble_primary_dfu.sh",
        "scripts/run_ble_node_manager_service.sh",
        "scripts/install_ble_node_manager_service.sh",
    ]
    for helper in shell_helpers:
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
