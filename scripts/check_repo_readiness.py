#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = REPO_ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

REQUIRED_FILES = [
    "README.md",
    "install.sh",
    "pi-companion/config.default.json",
    "pi-companion/requirements.txt",
    "pi-companion/koalablue/menu_catalog.py",
    "pi-companion/koalablue/menu_ui.py",
    "pi-companion/koalablue/menu_display_sync.py",
    "pi-companion/koalablue/menu_theme.py",
    "pi-companion/koalablue/menu_prompt_state.py",
    "pi-companion/koalablue/popup_keyboard.py",
    "pi-companion/koalablue/greatwhite_reef.py",
    "pi-companion/koalablue/bluez_lab_scope.py",
    "pi-companion/koalablue/esp32_touch_menu_bridge.py",
    "pi-companion/koalablue/t114_menu_status.py",
    "pi-companion/koalablue/meshtastic_app.py",
    "pi-companion/koalablue/meshtastic_menu_items.py",
    "pi-companion/koalablue/location_password_gate.py",
    "pi-companion/koalablue/gpio_buttons.py",
    "pi-companion/koalablue/killerkoala_vocabulary.py",
    "pi-companion/koalablue/killerkoala_voice_control.py",
    "scripts/check_deployability.sh",
    "scripts/check_menu_actions.py",
    "scripts/check_menu_theme_fit.py",
    "scripts/check_menu_prompt_ui.py",
    "scripts/check_koala_kry_menu.py",
    "scripts/check_esp32_touch_menu.py",
    "scripts/check_full_runtime_dependencies.py",
    "scripts/check_one_shot_controls.py",
    "scripts/run_menu_screen.py",
    "scripts/run_location_password_gate.py",
    "scripts/run_esp32_touch_menu_bridge.py",
    "scripts/install_koalabyte_one_shot.sh",
    "scripts/koalabyte_blue_boot.sh",
    "systemd/koalabyte-menu.service",
    "firmware/esp32-dualeye/platformio.ini",
    "firmware/esp32-dualeye/include/config.h",
    "firmware/esp32-dualeye/src/main.cpp",
    "firmware/esp32-dualeye/src/esp32_touch_menu.h",
    "firmware/esp32-dualeye/src/esp32_touch_menu.cpp",
    "firmware/t114-combined-safe/CMakeLists.txt",
    "firmware/t114-combined-safe/prj.conf",
    "docs/ESP32_TOUCH_MENU_CALIBRATION.md",
    "docs/GREATWHITE_REEF.md",
    "docs/FRONT_PANEL_BUTTONS_REVA5.md",
    "docs/BUTTON_WIRING_REVA5.md",
]

SHELL_HELPERS = [
    "install.sh",
    "scripts/check_deployability.sh",
    "scripts/install_pi.sh",
    "scripts/install_koalabyte_one_shot.sh",
    "scripts/setup_wifi_first_boot.sh",
    "scripts/setup_system_packages.sh",
    "scripts/setup_esp32_tools.sh",
    "scripts/setup_heltec_t114_tools.sh",
    "scripts/setup_nrf_tools.sh",
    "scripts/setup_nrf_connect_sdk_toolchain.sh",
    "scripts/setup_bluez_gatttool.sh",
    "scripts/setup_killerkoala_ollama.sh",
    "scripts/configure_koalabyte_external_antennas.sh",
    "scripts/configure_esp32s3_dualeye_2g4_antenna.sh",
    "scripts/configure_t114_2g4_antenna.sh",
    "scripts/configure_t114_lora_external_antenna.sh",
    "scripts/flash_all_components.sh",
    "scripts/flash_t114_when_plugged.sh",
    "scripts/build_t114_combined_safe.sh",
    "scripts/flash_t114_combined_safe.sh",
    "scripts/flash_heltec_mouth.sh",
    "scripts/flash_esp32.sh",
    "scripts/preflight_all_hardware.sh",
    "scripts/install_koalabyte_udev_rules.sh",
    "scripts/install_koalabyte_boot_services.sh",
    "scripts/install_koalabyte_logrotate.sh",
    "scripts/koalabyte_doctor.sh",
    "scripts/koalabyte_safe_mode.sh",
    "scripts/export_koalabyte_logs.sh",
    "scripts/build_koalabyte_release_package.sh",
]

REQUIRED_RUNTIME_REQUIREMENTS = ["bleak", "pyserial", "rich", "pydantic", "fastapi", "uvicorn", "requests", "httpx", "gpiozero", "pygame", "python-can", "pyttsx3", "SpeechRecognition", "meshtastic"]


def _file_contains(path: Path, needles: list[str]) -> list[str]:
    if not path.exists():
        return [f"missing file: {path.relative_to(REPO_ROOT)}"]
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [f"{path.relative_to(REPO_ROOT)} missing {needle}" for needle in needles if needle not in text]


def check_required_files(failures: list[str]) -> None:
    for relative_path in REQUIRED_FILES:
        if not (REPO_ROOT / relative_path).exists():
            failures.append(f"missing required file: {relative_path}")


def check_readme(failures: list[str]) -> None:
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for needle in [
        "bash scripts/install_koalabyte_one_shot.sh",
        "InnoMaker CAN kit is optional",
        "ESP32-S3 DualEye",
        "Heltec Mesh Node T114",
        "Koala Kombat Kruisin",
        "Meshtastic App",
        "jungle/eucalyptus",
        "Didgeridoo",
        "GNSS",
        "TinyLlama",
        "Ollama",
        "GreatWhite Reef",
        "TigerShark",
        "Great Wire Shark",
        "logs/greatwhite_reef/pcaps/",
        "HT-n5262",
        "Press the RST key twice",
        "8 independent key button module",
        "K7 Power On/Off",
        "K8 Reset / Reboot",
    ]:
        if needle not in text:
            failures.append(f"README.md missing expected deployment text: {needle}")


def check_config(failures: list[str]) -> None:
    path = REPO_ROOT / "pi-companion" / "config.default.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"config.default.json is invalid JSON: {exc}")
        return
    for section in ["killerkoala_companion", "koala_kan_kommander", "anteater", "front_panel_buttons"]:
        if section not in config:
            failures.append(f"config missing required section: {section}")
    buttons = config.get("front_panel_buttons", {}).get("buttons", {}) if isinstance(config.get("front_panel_buttons"), dict) else {}
    if len(buttons) != 8:
        failures.append("front_panel_buttons must define exactly eight K1-K8 buttons")
    expected_commands = {"power_toggle", "reset"}
    found_commands = {str(item.get("press_command")) for item in buttons.values() if isinstance(item, dict)}
    for command in sorted(expected_commands - found_commands):
        failures.append(f"front_panel_buttons missing command: {command}")


def check_requirements(failures: list[str]) -> None:
    requirements_path = REPO_ROOT / "pi-companion" / "requirements.txt"
    text = requirements_path.read_text(encoding="utf-8") if requirements_path.exists() else ""
    lowered = text.lower()
    for requirement in REQUIRED_RUNTIME_REQUIREMENTS:
        if requirement.lower() not in lowered:
            failures.append(f"pi-companion/requirements.txt missing runtime dependency: {requirement}")


def check_menu_catalog(failures: list[str]) -> None:
    try:
        import koalablue  # noqa: F401 - triggers GreatWhite Reef menu extension
        from koalablue.menu_catalog import MENU_GROUPS, SUBMENU_ITEMS, leaf_menu_entries, menu_labels
        from scripts.check_menu_actions import build_manifest
    except Exception as exc:
        failures.append(f"failed to import menu readiness helpers: {exc}")
        return
    main_labels = set(menu_labels("main"))
    for label in ["Eucalyptus", "Koala Kombat Kruisin’", "Bluetooth Tools", "Didgeridoo", "CAN Bench Tools", "GreatWhite Reef", "Reports & Reviews", "System / Companion", "Lab", "Power & Exit"]:
        if label not in main_labels:
            failures.append(f"main menu labels missing {label}")
    if "Keyboard / Text Entry" in main_labels:
        failures.append("main menu should not expose standalone keyboard page")
    for group in ["Didgeridoo", "GreatWhite Reef"]:
        if group not in MENU_GROUPS:
            failures.append(f"menu catalog missing {group} group")
    for submenu in ["eucalyptus", "kruisin", "bluetooth", "didgeridoo", "meshtastic", "can_bench", "greatwhite_reef", "reports", "system", "lab", "power"]:
        if submenu not in SUBMENU_ITEMS:
            failures.append(f"menu catalog missing {submenu} submenu")
    if "keyboard" in SUBMENU_ITEMS:
        failures.append("keyboard submenu should be hidden; keyboard opens only from text input items")

    didgeridoo_labels = set(menu_labels("didgeridoo"))
    expected_didgeridoo = {"Heltec Link", "Radio/GPS", "T114 BLE Check", "Lab TX Status", "Sextant", "Create Location Password", "Unlock Current Process", "Meshtastic App", "Protected Location Gate Status", "Protected GNSS Current Fix"}
    for label in sorted(expected_didgeridoo - didgeridoo_labels):
        failures.append(f"Didgeridoo submenu missing {label}")

    greatwhite_labels = set(menu_labels("greatwhite_reef"))
    expected_greatwhite = {"Reef Status", "TigerShark Install Check", "TigerShark Interfaces", "TigerShark PCAP Folder", "TigerShark Read Latest PCAP", "Great Wire Shark Launch Notes", "Great Wire Shark Folder Notes", "GreatWhite Reef Report"}
    for label in sorted(expected_greatwhite - greatwhite_labels):
        failures.append(f"GreatWhite Reef submenu missing {label}")

    meshtastic_labels = set(menu_labels("meshtastic"))
    expected_meshtastic = {"Meshtastic Profile", "Meshtastic Compatibility", "Phone App Pairing", "ESP32 Device Link", "Use Heltec USB Serial", "Use Network TCP", "Use BLE Link", "Meshtastic Status", "Meshtastic Nodes", "Meshtastic GPS Info", "Type Mesh Message", "Type Mesh Destination"}
    for label in sorted(expected_meshtastic - meshtastic_labels):
        failures.append(f"Meshtastic submenu missing {label}")

    bluetooth_labels = set(menu_labels("bluetooth"))
    for label in ["Koala Kapture", "Koala Kry", "KoalaByte Lab", "Dropbear Discovery Sweep", "Platypus BT-Proxy", "AntEater", "Urban Poaching"]:
        if label not in bluetooth_labels:
            failures.append(f"Bluetooth submenu missing {label}")
    lab_labels = set(menu_labels("lab"))
    for label in ["BlueZ Lab Scope Status", "Type BlueZ Lab Target", "Owned Device Scope ON", "Owned Device Scope OFF", "Clear BlueZ Lab Scope"]:
        if label not in lab_labels:
            failures.append(f"Lab submenu missing {label}")
    power_labels = set(menu_labels("power"))
    for label in ["Power On/Off", "Reset / Reboot"]:
        if label not in power_labels:
            failures.append(f"Power submenu missing {label}")
    if not leaf_menu_entries():
        failures.append("menu catalog has no enabled leaf menu entries")
    manifest, menu_failures = build_manifest()
    if manifest.get("status") != "MENU_ACTIONS_READY":
        failures.append("menu action manifest is not ready")
    for failure in menu_failures:
        failures.append(f"menu action readiness: {failure}")


def check_project_markers(failures: list[str]) -> None:
    checks = {
        "scripts/check_deployability.sh": ["DEPLOYABILITY_READY", "flash_all_components", "install_koalabyte_one_shot.sh", "flash_t114_when_plugged.sh"],
        "pi-companion/koalablue/popup_keyboard.py": ["bluez_lab_target", "Create Location Password", "Unlock Current Process"],
        "pi-companion/koalablue/greatwhite_reef.py": ["GreatWhite Reef", "TigerShark", "Great Wire Shark", "greatwhite_pcap_read:", "logs/greatwhite_reef"],
        "pi-companion/koalablue/bluez_lab_scope.py": ["BLUEZ_LAB_SCOPE_READY", "apply_env", "set_owned", "set_target"],
        "pi-companion/koalablue/esp32_touch_menu_bridge.py": ["menu_touch", "calibration_command", "logs/esp32_touch_menu_events.jsonl"],
        "pi-companion/koalablue/menu_action_runner.py": ["_bluez_lab_scope", "bluez_lab_scope.apply_env", "manual_prompt_required", "reset_confirm", "power_toggle"],
        "pi-companion/koalablue/menu_screen.py": ["power_toggle", "reset_confirm", "K8 reset/reboot"],
        "scripts/setup_system_packages.sh": ["tshark", "wireshark", "GreatWhite Reef"],
        "scripts/flash_t114_when_plugged.sh": ["HT-n5262", "T114_UF2_MOUNT", "T114_FLASH_METHOD", "bootloader_volume_detected", "mount_uf2_block_if_needed", "lsblk", "UF2_MOUNTPOINT"],
        "scripts/flash_t114_combined_safe.sh": ["HT-n5262", "T114_UF2_VOLUME_NAME", "find_uf2_mount", "T114_FLASH_METHOD", "mount_uf2_block_if_needed", "lsblk", "UF2_MOUNTPOINT"],
        "firmware/t114-combined-safe/prj.conf": ["CONFIG_BUILD_OUTPUT_UF2=y", "CONFIG_USB_CDC_ACM=y", "KoalaByte Blue Heltec T114 combined-safe firmware"],
        "scripts/check_menu_prompt_ui.py": ["bluez_lab_target", "Create Location Password", "Unlock Current Process"],
        "scripts/check_esp32_touch_menu.py": ["Esp32TouchMenuBridge", "menu_touch"],
        "firmware/esp32-dualeye/include/config.h": ["waveshare_cst816x_i2c", "TOUCH_MENU_CONTROLLER", "TOUCH_MENU_I2C_ADDR"],
        "firmware/esp32-dualeye/src/main.cpp": ["esp32_touch_menu.h", "setupTouchMenu();", "pollTouchMenu(sendJson);", "handleTouchMenuCommand(doc, sendJson)"],
        "firmware/esp32-dualeye/src/esp32_touch_menu.cpp": ["Arduino_IIC_Touch_Interrupt", "CST816_REG_GESTURE", "menu_touch", "touch_status", "touch_calibration"],
        "scripts/run_menu_screen.py": ["--terminal", "--no-terminal-fallback", "run_wrapped_interface", "WRAPPED_INTERFACE_START_FAILED"],
        "scripts/koalabyte_blue_boot.sh": ["MENU_NO_TERMINAL_FALLBACK", "--no-terminal-fallback", "wrapped graphical jungle UI"],
        "systemd/koalabyte-menu.service": ["koalabyte_blue_boot.sh", "WantedBy=multi-user.target", "MENU_GRAPHICAL=1", "MENU_NO_TERMINAL_FALLBACK=1"],
        "docs/GREATWHITE_REEF.md": ["TigerShark", "Great Wire Shark", "logs/greatwhite_reef/pcaps/", "PCAP 1"],
        "docs/FRONT_PANEL_BUTTONS_REVA5.md": ["8 independent key button module", "K7", "K8", "Power On/Off", "Reset"],
        "docs/BUTTON_WIRING_REVA5.md": ["8 independent key button module", "K1", "K8", "3.3V only"],
    }
    for relative, needles in checks.items():
        failures.extend(_file_contains(REPO_ROOT / relative, needles))


def check_helpers(failures: list[str]) -> None:
    for helper in SHELL_HELPERS:
        path = REPO_ROOT / helper
        if not path.exists():
            failures.append(f"missing shell helper: {helper}")
            continue
        text = path.read_text(encoding="utf-8")
        if "set -euo pipefail" not in text:
            failures.append(f"shell helper missing strict shell mode: {helper}")
        result = subprocess.run(["bash", "-n", str(path)], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            failures.append(f"shell syntax failed for {helper}: {result.stderr.strip()}")


def main() -> int:
    failures: list[str] = []
    check_required_files(failures)
    check_readme(failures)
    check_config(failures)
    check_requirements(failures)
    check_menu_catalog(failures)
    check_project_markers(failures)
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
