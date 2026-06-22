#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

NEEDED = [
    "README.md",
    "firmware/esp32-dualeye/src/killerkoala_ai_face.h",
    "firmware/esp32-dualeye/src/killerkoala_ai_face.cpp",
    "firmware/heltec-mouth/README.md",
    "firmware/heltec-mouth/boards/heltec_t114.json",
    "firmware/heltec-mouth/variants/Heltec_T114_Board/variant.h",
    "firmware/heltec-mouth/variants/Heltec_T114_Board/variant.cpp",
    "firmware/heltec-mouth/platformio.ini",
    "firmware/heltec-mouth/include/config.h",
    "firmware/heltec-mouth/src/main.cpp",
    "docs/HELTEC_BLE_NODE_ROLES.md",
    "pi-companion/requirements.txt",
    "pi-companion/koalablue/ble_event_log.py",
    "pi-companion/koalablue/ble_node_manager.py",
    "pi-companion/koalablue/koala_kan_kommander.py",
    "pi-companion/koalablue/killerkoala_face_bridge.py",
    "pi-companion/koalablue/killerkoala_voice_face_control.py",
    "scripts/run_killerkoala_face_demo.py",
    "scripts/flash_heltec_mouth.sh",
    "scripts/flash_all_components.sh",
    "scripts/build_firmware_all.sh",
    "scripts/setup_system_packages.sh",
    "scripts/setup_can0.sh",
    "scripts/run_koala_kan_kommander.py",
    "scripts/run_ble_node_manager.py",
    "scripts/run_ble_node_manager_service.sh",
    "scripts/install_ble_node_manager_service.sh",
]

TEXT = {
    "README.md": ["Heltec Mesh Node T114 v2", "USB-C data cable", "KOALABYTE_HELTEC_USB_PORT", "--heltec-t114"],
    "firmware/esp32-dualeye/src/killerkoala_ai_face.cpp": ["drawEye", "eyes only"],
    "firmware/heltec-mouth/README.md": ["USB-C data cable", "Do not wire", "L76K GNSS", "gnss_nmea"],
    "firmware/heltec-mouth/platformio.ini": ["board = heltec_t114", "board_build.variants_dir = variants", "Adafruit ST7735 and ST7789"],
    "firmware/heltec-mouth/boards/heltec_t114.json": ["HT-n5262", "Heltec Mesh Node T114 v2", "Heltec_T114_Board"],
    "firmware/heltec-mouth/variants/Heltec_T114_Board/variant.h": ["PIN_TFT_CS", "SX126X_DIO1", "PIN_SERIAL1_RX"],
    "firmware/heltec-mouth/include/config.h": ["KOALA_GNSS_ENABLED", "KOALA_GNSS_BAUD", "KOALA_GNSS_REPORT_MS"],
    "firmware/heltec-mouth/src/main.cpp": ["Adafruit_ST7789", "Serial.begin", "Serial1.begin", "gnss_nmea", "drawSnout", "drawSolidMouth", "ble_adv_seen", "ble_start", "ble_status"],
    "docs/HELTEC_BLE_NODE_ROLES.md": ["Heltec T114", "primary", "BLE node manager", "service"],
    "pi-companion/requirements.txt": ["python-can"],
    "pi-companion/koalablue/ble_event_log.py": ["BleEventLog", "BleEventDeduper", "normalize_ble_event", "source"],
    "pi-companion/koalablue/ble_node_manager.py": ["heltec-t114", "discover_heltec_port", "BleEventDeduper", "ble_adv_seen"],
    "pi-companion/koalablue/koala_kan_kommander.py": ["Koala Kan Kommander", "InnoMaker USB to CAN Converter kit", "manifest", "inventory", "status", "transmit_requires_bench_simulator"],
    "pi-companion/koalablue/killerkoala_face_bridge.py": ["KOALABYTE_HELTEC_USB_PORT", "heltec_connection", "usb-cdc"],
    "scripts/run_killerkoala_face_demo.py": ["Heltec T114 color TFT", "emit_face"],
    "scripts/flash_heltec_mouth.sh": ["KOALABYTE_HELTEC_USB_PORT", "heltec_t114.json", "firmware/heltec-mouth"],
    "scripts/flash_all_components.sh": ["--install-firmware", "git checkout heltec", "PREFLIGHT_BUILD", "--heltec-t114", "RUN_HELTEC_T114", "scripts/flash_heltec_mouth.sh", "RUN_BLE_NODE_MANAGER", "--ble-node-manager", "RUN_CAN_CHECK", "--can-check", "setup_can0.sh", "run_koala_kan_kommander.py manifest", "run_koala_kan_kommander.py inventory", "run_koala_kan_kommander.py status", "CAN_INTERFACE", "CAN_BITRATE", "STRICT_CAN_SETUP"],
    "scripts/build_firmware_all.sh": ["firmware/heltec-mouth", "Heltec Mesh Node T114 v2"],
    "scripts/setup_system_packages.sh": ["can-utils", "python3-can", "cansend"],
    "scripts/setup_can0.sh": ["for module in can can_raw can_dev", "ip link set \"${INTERFACE}\" type can bitrate", "firmware_flash_required", "Koala Kan Kommander CAN setup"],
    "scripts/run_koala_kan_kommander.py": ["koalablue.koala_kan_kommander", "run_cli"],
    "scripts/run_ble_node_manager.py": ["--heltec-port", "--esp32-port", "BleNodeManager"],
    "scripts/run_ble_node_manager_service.sh": ["KOALABYTE_HELTEC_USB_PORT", "--duration", "0", "run_ble_node_manager.py"],
    "scripts/install_ble_node_manager_service.sh": ["koalabyte-ble-node-manager.service", "run_ble_node_manager_service.sh", "KOALABYTE_HELTEC_USB_PORT"],
    "scripts/run_menu_screen.py": ["emit_selected_action_face"],
}

EXPERIMENTAL_TRACK_PATHS = [
    "pi-companion/koalablue/koala_kan_firmware.py",
    "scripts/run_koala_kan_firmware.py",
    "firmware/innomaker-can-commander/README.md",
]

SHELL_HELPERS = [
    "scripts/flash_all_components.sh",
    "scripts/build_firmware_all.sh",
    "scripts/setup_system_packages.sh",
    "scripts/setup_can0.sh",
    "scripts/run_ble_node_manager_service.sh",
    "scripts/install_ble_node_manager_service.sh",
    "scripts/flash_heltec_mouth.sh",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def main() -> int:
    failures: list[str] = []
    for relative_path in NEEDED:
        if not (ROOT / relative_path).exists():
            failures.append(f"missing required Heltec branch file: {relative_path}")
    for relative_path in EXPERIMENTAL_TRACK_PATHS:
        if (ROOT / relative_path).exists():
            failures.append(f"experimental CAN firmware track should stay on its own branch: {relative_path}")
    for relative_path, words in TEXT.items():
        body = read_text(ROOT / relative_path)
        for word in words:
            if word not in body:
                failures.append(f"{relative_path} missing expected text: {word}")
    config_path = ROOT / "pi-companion" / "config.default.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            if "koala_kan_kommander" not in config:
                failures.append("config.default.json missing koala_kan_kommander section")
        except json.JSONDecodeError as exc:
            failures.append(f"config.default.json is invalid JSON: {exc}")
    for helper in SHELL_HELPERS:
        body = read_text(ROOT / helper)
        if body and "set -euo pipefail" not in body:
            failures.append(f"shell helper missing strict shell mode: {helper}")
    if failures:
        print("KoalaByte readiness issues:")
        for failure in failures:
            print("- " + failure)
        return 1
    print("KoalaByte Blue repo readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
