#!/usr/bin/env python3
from __future__ import annotations

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
    "docs/MINED_HELTEC_V2_FEATURES.md",
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
    "pi-companion/requirements-heltec-v2-extra.txt",
    "pi-companion/koalablue/ble_event_log.py",
    "pi-companion/koalablue/ble_node_manager.py",
    "pi-companion/koalablue/koala_kan_kommander.py",
    "pi-companion/koalablue/killerkoala_face_bridge.py",
    "pi-companion/koalablue/killerkoala_voice_face_control.py",
    "pi-companion/koalablue/t114_bluez.py",
    "pi-companion/koalablue/location_password_gate.py",
    "pi-companion/koalablue/gnss_location.py",
    "pi-companion/koalablue/meshtastic_app.py",
    "scripts/run_killerkoala_face_demo.py",
    "scripts/flash_heltec_mouth.sh",
    "scripts/flash_all_components.sh",
    "scripts/build_firmware_all.sh",
    "scripts/setup_system_packages.sh",
    "scripts/setup_can0.sh",
    "scripts/setup_vcan0.sh",
    "scripts/install_can0_service.sh",
    "scripts/run_can0_service.sh",
    "scripts/install_koalabyte_udev_rules.sh",
    "scripts/discover_koalabyte_ports.py",
    "scripts/preflight_all_hardware.py",
    "scripts/preflight_all_hardware.sh",
    "scripts/run_koala_kan_kommander.py",
    "scripts/run_ble_node_manager.py",
    "scripts/run_ble_node_manager_service.sh",
    "scripts/install_ble_node_manager_service.sh",
    "scripts/run_t114_bluez.py",
    "scripts/run_meshtastic_app.py",
    "scripts/run_location_password_gate.py",
    "scripts/confirm_t114_board_target.sh",
    "scripts/configure_t114_2g4_antenna.sh",
    "scripts/build_nrf52840_t114_hci_usb.sh",
    "scripts/flash_nrf52840_t114_hci_usb.sh",
]

TEXT = {
    "README.md": ["Heltec Mesh Node T114 v2", "USB-C data cable", "KOALABYTE_HELTEC_USB_PORT", "--heltec-t114"],
    "docs/CANONICAL_BRANCH.md": [CANONICAL_BRANCH, "Delete command for maintainers", "git push origin --delete heltec"],
    "docs/MINED_HELTEC_V2_FEATURES.md": ["koalabyte-blue-v2-heltec-edition", "not a blind merge", "--nrf-konnect", "build_nrf52840_t114_hci_usb.sh"],
    "firmware/esp32-dualeye/src/killerkoala_ai_face.cpp": ["drawEye", "eyes only"],
    "firmware/heltec-mouth/README.md": ["USB-C data cable", "Do not wire", "L76K GNSS", "gnss_nmea"],
    "firmware/heltec-mouth/platformio.ini": ["board = heltec_t114", "board_build.variants_dir = variants", "Adafruit ST7735 and ST7789"],
    "firmware/heltec-mouth/boards/heltec_t114.json": ["HT-n5262", "Heltec Mesh Node T114 v2", "Heltec_T114_Board"],
    "firmware/heltec-mouth/variants/Heltec_T114_Board/variant.h": ["PIN_TFT_CS", "SX126X_DIO1", "PIN_SERIAL1_RX"],
    "firmware/heltec-mouth/include/config.h": ["KOALA_GNSS_ENABLED", "KOALA_GNSS_BAUD", "KOALA_GNSS_REPORT_MS"],
    "firmware/heltec-mouth/src/main.cpp": ["Adafruit_ST7789", "Serial.begin", "Serial1.begin", "gnss_nmea", "drawSnout", "drawSolidMouth", "ble_adv_seen", "ble_start", "ble_status"],
    "docs/HELTEC_BLE_NODE_ROLES.md": ["Heltec T114", "primary", "BLE node manager", "service"],
    "pi-companion/requirements.txt": ["python-can"],
    "pi-companion/requirements-heltec-v2-extra.txt": ["meshtastic[cli]", "prompt-toolkit", "spidev"],
    "pi-companion/koalablue/ble_event_log.py": ["BleEventLog", "BleEventDeduper", "normalize_ble_event", "source"],
    "pi-companion/koalablue/ble_node_manager.py": ["heltec-t114", "discover_heltec_port", "BleEventDeduper", "ble_adv_seen"],
    "pi-companion/koalablue/koala_kan_kommander.py": ["Koala Kan Kommander", "InnoMaker USB to CAN Converter kit", "manifest", "inventory", "status"],
    "pi-companion/koalablue/killerkoala_face_bridge.py": ["KOALABYTE_HELTEC_USB_PORT", "heltec_connection", "usb-cdc"],
    "pi-companion/koalablue/t114_bluez.py": ["T114BluezResult", "controller-check", "blocked_missing_hci_controller", "authorized_lab_use_only"],
    "pi-companion/koalablue/location_password_gate.py": ["KOALABYTE_LOCATION_UNLOCKED", "password_sha256", "ensure_unlocked"],
    "pi-companion/koalablue/gnss_location.py": ["authorized password-protected location logging only", "parse_meshtastic_info_text", "write_current_fix"],
    "pi-companion/koalablue/meshtastic_app.py": ["--confirm-send is required", "protected-actions password required", "MeshtasticProfile"],
    "scripts/run_killerkoala_face_demo.py": ["Heltec T114 color TFT", "emit_face"],
    "scripts/flash_heltec_mouth.sh": ["KOALABYTE_HELTEC_USB_PORT", "heltec_t114.json", "firmware/heltec-mouth"],
    "scripts/flash_all_components.sh": ["--install-firmware", "CANONICAL_HELTEC_BRANCH", CANONICAL_BRANCH, "KOALABYTE_HELTEC_BRANCH", "--nrf-konnect", "build_nrf52840_t114_hci_usb.sh", "flash_nrf52840_t114_hci_usb.sh", "PREFLIGHT_BUILD", "--heltec-t114", "RUN_HELTEC_T114", "scripts/flash_heltec_mouth.sh", "RUN_BLE_NODE_MANAGER", "--ble-node-manager", "RUN_CAN_CHECK", "--can-check", "setup_can0.sh", "run_koala_kan_kommander.py manifest", "run_koala_kan_kommander.py inventory", "run_koala_kan_kommander.py status", "CAN_INTERFACE", "CAN_BITRATE", "STRICT_CAN_SETUP"],
    "scripts/build_firmware_all.sh": ["firmware/heltec-mouth", "Heltec Mesh Node T114 v2", "BUILD_KOALA_KONNECT", "build_nrf52840_t114_hci_usb.sh", "setup_nrf_connect_sdk_toolchain.sh"],
    "scripts/setup_system_packages.sh": ["can-utils", "python3-can", "cansend", "udev", "iproute2"],
    "scripts/install_koalabyte_udev_rules.sh": ["/dev/koalabyte-nrf-ble", "/dev/koalabyte-esp32-eyes", "/dev/koalabyte-heltec", "99-koalabyte.rules"],
    "scripts/discover_koalabyte_ports.py": ["KOALABYTE_HELTEC_USB_PORT", "KOALABYTE_ESP32_FACE_PORT", "CAN_INTERFACE", "koalabyte_ports.env"],
    "scripts/install_can0_service.sh": ["koalabyte-can0.service", "run_can0_service.sh", "CAN_INTERFACE", "CAN_BITRATE"],
    "scripts/run_can0_service.sh": ["setup_can0.sh", "koalabyte_ports.env", "CAN_INTERFACE", "CAN_BITRATE"],
    "scripts/setup_vcan0.sh": ["vcan0", "modprobe vcan", "Koala Kan local software self-test"],
    "scripts/preflight_all_hardware.py": ["hardware_report.json", "discover_koalabyte_ports.py", "setup_vcan0.sh", "python_can_present"],
    "scripts/preflight_all_hardware.sh": ["preflight_all_hardware.py"],
    "scripts/setup_can0.sh": ["for module in can can_raw can_dev", "ip link set \"${INTERFACE}\" type can bitrate", "firmware_flash_required", "Koala Kan Kommander CAN setup"],
    "scripts/run_koala_kan_kommander.py": ["koalablue.koala_kan_kommander", "run_cli"],
    "scripts/run_ble_node_manager.py": ["--heltec-port", "--esp32-port", "BleNodeManager"],
    "scripts/run_ble_node_manager_service.sh": ["/dev/koalabyte-heltec", "koalabyte_ports.env", "run_ble_node_manager.py"],
    "scripts/install_ble_node_manager_service.sh": ["systemd-udev-settle.service", "koalabyte_ports.env", "KOALABYTE_HELTEC_USB_PORT"],
    "scripts/run_menu_screen.py": ["emit_selected_action_face"],
    "scripts/run_t114_bluez.py": ["koalablue.t114_bluez", "run_cli"],
    "scripts/run_meshtastic_app.py": ["koalablue.meshtastic_app", "run_cli"],
    "scripts/run_location_password_gate.py": ["koalablue.location_password_gate", "run_cli"],
    "scripts/confirm_t114_board_target.sh": ["heltec_t114_v2/nrf52840", "ALLOW_T114_BOARD_SMOKE_FALLBACK", "t114_board_target.json"],
    "scripts/configure_t114_2g4_antenna.sh": ["T114_2G4_ANTENNA", "Do not guess an RF-switch pin", "t114_2g4_antenna_status.json"],
    "scripts/build_nrf52840_t114_hci_usb.sh": ["samples/bluetooth/hci_usb", "t114_hci_usb", "west build"],
    "scripts/flash_nrf52840_t114_hci_usb.sh": ["T114_FLASH_METHOD", "west flash", "t114_active_ble_mode.json"],
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
    "scripts/setup_vcan0.sh",
    "scripts/install_can0_service.sh",
    "scripts/run_can0_service.sh",
    "scripts/install_koalabyte_udev_rules.sh",
    "scripts/preflight_all_hardware.sh",
    "scripts/run_ble_node_manager_service.sh",
    "scripts/install_ble_node_manager_service.sh",
    "scripts/flash_heltec_mouth.sh",
    "scripts/confirm_t114_board_target.sh",
    "scripts/configure_t114_2g4_antenna.sh",
    "scripts/build_nrf52840_t114_hci_usb.sh",
    "scripts/flash_nrf52840_t114_hci_usb.sh",
]

FORBIDDEN_BRANCH_REFERENCES = [
    "git checkout heltec",
    "git fetch origin heltec",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def main() -> int:
    failures: list[str] = []
    for relative_path in NEEDED:
        if not (ROOT / relative_path).exists():
            failures.append(f"missing required Heltec Edition file: {relative_path}")
    for relative_path in EXPERIMENTAL_TRACK_PATHS:
        if (ROOT / relative_path).exists():
            failures.append(f"experimental CAN firmware track should stay on its own branch: {relative_path}")
    for relative_path, words in TEXT.items():
        body = read_text(ROOT / relative_path)
        for word in words:
            if word not in body:
                failures.append(f"{relative_path} missing expected text: {word}")
    flash_helper = read_text(ROOT / "scripts" / "flash_all_components.sh")
    for forbidden in FORBIDDEN_BRANCH_REFERENCES:
        if forbidden in flash_helper:
            failures.append(f"flash_all_components.sh still references removable branch alias: {forbidden}")
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
