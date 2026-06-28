#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue.gpio_buttons import DEFAULT_BUTTONS, DEFAULT_ELECTRICAL_MODE
from koalablue.menu_catalog import SUBMENU_ITEMS, menu_labels
from scripts.check_killerkoala_face_mouth_sync import validate_protocol
from scripts.check_menu_actions import build_manifest

STATUS_PATH = ROOT / "logs" / "one_shot" / "control_surface_status.json"

REQUIRED_ONE_SHOT_SNIPPETS = [
    "--check-only",
    "scripts/install_pi.sh",
    "scripts/flash_esp32.sh",
    "scripts/check_killerkoala_face_mouth_sync.py",
    "scripts/check_menu_actions.py",
    "scripts/check_full_runtime_dependencies.py",
    "scripts/configure_koalabyte_external_antennas.sh",
    "scripts/check_killerkoala_ai.py",
    "scripts/check_menu_display_sync.py",
    "run_menu_display_sync_gate",
    "Menu display sync and AI-face controls",
    "run_full_runtime_dependency_gate",
    "STRICT_FULL_RUNTIME_DEPENDENCIES",
    "run_killerkoala_ai_readiness",
    "STRICT_KILLERKOALA_AI",
    "prepare_anteater_status",
    "run_optional_can",
    "INSTALL_INNOMAKER_CAN",
    "STRICT_INNOMAKER_CAN",
    "InnoMaker CAN kit is optional",
    "scripts/check_field_readiness.py",
    "run_field_readiness",
    "Field readiness helpers",
    "scripts/check_koalabyte_version_handshake.py",
    "run_version_handshake",
    "Version handshake readiness",
    "scripts/run_koalabyte_status_server.py",
    "run_status_dashboard_json",
    "Status dashboard JSON check",
    "scripts/install_koalabyte_udev_rules.sh",
    "run_udev_install_or_check",
    "udev rules install",
    "scripts/install_koalabyte_boot_services.sh",
    "run_boot_services_install_or_check",
    "boot services install",
    "scripts/export_koalabyte_logs.sh",
    "scripts/build_koalabyte_release_package.sh",
    "run_release_log_helper_checks",
    "Release and log helper checks",
    "scripts/koalabyte_doctor.sh",
    "run_doctor_quick",
    "KoalaByte Doctor quick check",
]

REQUIRED_COMMAND_HELPERS = [
    "scripts/install_koalabyte_one_shot.sh",
    "scripts/check_menu_actions.py",
    "scripts/check_menu_display_sync.py",
    "scripts/check_field_readiness.py",
    "scripts/check_voice_menu_launch.py",
    "scripts/check_external_antenna_readiness.py",
    "scripts/check_killerkoala_face_mouth_sync.py",
    "scripts/check_killerkoala_ai.py",
    "scripts/check_full_runtime_dependencies.py",
    "scripts/check_t114_status_dashboard.py",
    "scripts/check_koalabyte_version_handshake.py",
    "scripts/run_koalabyte_status_server.py",
    "scripts/koalabyte_doctor.py",
    "scripts/koalabyte_doctor.sh",
    "scripts/install_koalabyte_udev_rules.sh",
    "scripts/install_koalabyte_boot_services.sh",
    "scripts/install_koalabyte_logrotate.sh",
    "scripts/koalabyte_safe_mode.sh",
    "scripts/export_koalabyte_logs.sh",
    "scripts/build_koalabyte_release_package.sh",
    "scripts/run_esp32_dualeye_voice_bridge.py",
    "scripts/configure_koalabyte_external_antennas.sh",
    "scripts/flash_t114_when_plugged.sh",
    "scripts/run_didgeridoo.py",
    "scripts/run_location_password_gate.py",
    "scripts/run_t114_bluez.py",
    "scripts/run_meshtastic_app.py",
    "scripts/run_killerkoala_voice.py",
    "scripts/run_killerkoala_hybrid.py",
    "scripts/setup_killerkoala_ollama.sh",
    "scripts/test_gpio_buttons.py",
    "scripts/setup_gpio_buttons.py",
    "scripts/run_koala_bluez.py",
    "scripts/run_koala_bluez_manifest.sh",
    "scripts/run_koala_bluez_inventory.sh",
    "scripts/run_koala_bluez_status.sh",
    "scripts/run_koala_bluez_scan.sh",
    "scripts/run_koala_bluez_monitor.sh",
    "scripts/run_koala_bluez_all_safe.sh",
    "scripts/run_koala_bluez_info.sh",
    "scripts/run_koala_bluez_services.sh",
    "scripts/run_koala_bluez_gatt_readiness.sh",
]

REQUIRED_PROJECT_FILES = [
    "pi-companion/koalablue/bluez_tools.py",
    "pi-companion/koalablue/bluez_protected_lab.py",
    "pi-companion/koalablue/greatwhite_reef.py",
    "pi-companion/koalablue/menu_action_runner.py",
    "docs/GREATWHITE_REEF.md",
    "docs/KOALA_BLUEZ_TOOLS_REVA16.md",
    "docs/FIELD_READINESS_UPGRADES.md",
    "version/koalabyte_protocol.json",
    "udev/99-koalabyte-blue.rules",
    "systemd/koalabyte-menu.service",
    "systemd/koalabyte-menu-sync.service",
    "systemd/koalabyte-doctor.service",
    "logrotate/koalabyte-blue",
    "production/README.md",
    "production/RevA25-heltec-powerbank/PRODUCTION_README_RevA25_HeltecPowerBank.md",
    "production/RevA25-heltec-powerbank/BOM_RevA25_HeltecPowerBank.csv",
    "production/RevA25-heltec-powerbank/USB_POWER_PACK.md",
    "production/RevA25-heltec-powerbank/Safety_Test_Record_RevA25.csv",
    "production/WIRING_DIAGRAM_ANTENNAS.md",
    "production/WIRING_DIAGRAM_ANTENNAS.svg",
    ".github/workflows/release-package.yml",
]

FIELD_READINESS_SHELL_HELPERS = [
    "scripts/koalabyte_doctor.sh",
    "scripts/install_koalabyte_udev_rules.sh",
    "scripts/install_koalabyte_boot_services.sh",
    "scripts/install_koalabyte_logrotate.sh",
    "scripts/koalabyte_safe_mode.sh",
    "scripts/export_koalabyte_logs.sh",
    "scripts/build_koalabyte_release_package.sh",
]

FIELD_READINESS_PYTHON_HELPERS = [
    "scripts/check_field_readiness.py",
    "scripts/check_koalabyte_version_handshake.py",
    "scripts/run_koalabyte_status_server.py",
    "scripts/koalabyte_doctor.py",
]

FORBIDDEN_PRODUCTION_FILES = [
    "production/RevA17-dongle-only/PRODUCTION_README_RevA17_DongleOnly.md",
    "production/RevA17-dongle-only/BOM_RevA17_DongleOnly.csv",
    "production/RevA17-dongle-only/BATTERY_POWER_2S_18650.md",
    "production/RevA17-dongle-only/Safety_Test_Record_RevA17.csv",
]

FORBIDDEN_ACTIVE_PRODUCTION_MARKERS = [
    "Nordic nRF52840 USB Dongle,1,Production-default",
    "2x18650 series holder,1",
    "2S Li-ion BMS/protection board,1",
]

REQUIRED_PROTECTED_BLUEZ_LABELS = [
    "Outback Module Deck",
    "Joey Target Dossier",
    "Treehouse Service Trace",
    "Gumnut GATT Gatecheck",
    "Outback Radio Ledger",
    "Classic Track Finder",
    "Treehouse RFCOMM Wiremap",
    "Pouch Link Echo",
    "Gumnut GATT Ghostmap",
]

REQUIRED_PROTECTED_BLUEZ_COMMANDS = [
    "koala_bluez_manifest",
    "koala_bluez_info",
    "koala_bluez_services",
    "koala_bluez_gatt_readiness",
    "bluez_outback_radio_ledger",
    "bluez_classic_track_finder",
    "bluez_treehouse_rfcomm_wiremap",
    "bluez_pouch_link_echo",
    "bluez_gumnut_gatt_ghostmap",
]

REQUIRED_ANTENNA_STATUS = [
    "logs/koalabyte_external_antenna_status.json",
    "logs/t114_lora_external_antenna_status.json",
    "logs/t114_2g4_antenna_status.json",
    "logs/esp32s3_dualeye_2g4_antenna_status.json",
    "logs/pi_2g4_external_antenna_status.json",
]


def run_command(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    return proc.returncode, proc.stdout, proc.stderr


def button_manifest() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen_numbers: set[int] = set()
    seen_pins: set[int] = set()
    for key, cfg in sorted(DEFAULT_BUTTONS.items(), key=lambda item: int(item[1]["number"])):
        number = int(cfg["number"])
        pin = int(cfg["pin"])
        seen_numbers.add(number)
        seen_pins.add(pin)
        rows.append({
            "id": key,
            "number": number,
            "label": cfg.get("label"),
            "pin_bcm": pin,
            "physical_pin": cfg.get("physical_pin"),
            "press_command": cfg.get("press_command"),
            "alias_command": cfg.get("alias_command", ""),
            "hold_command": cfg.get("hold_command", ""),
            "hold_seconds": cfg.get("hold_seconds", ""),
            "electrical_mode": {
                "internal_pull_up_enabled": DEFAULT_ELECTRICAL_MODE.pull_up,
                "not_pressed_raw_level": DEFAULT_ELECTRICAL_MODE.idle_state,
                "pressed_raw_level": DEFAULT_ELECTRICAL_MODE.pressed_state,
                "wiring": DEFAULT_ELECTRICAL_MODE.wiring,
            },
        })
    if seen_numbers != {1, 2, 3, 4, 5, 6}:
        raise ValueError(f"front-panel button numbers must be 1..6, got {sorted(seen_numbers)}")
    if len(seen_pins) != 6:
        raise ValueError("front-panel button GPIO pins must be unique")
    return rows


def _optional_can_required_false_marker_present(one_shot_text: str) -> bool:
    return '"required": false' in one_shot_text or '"required": False' in one_shot_text


def validate_optional_can_policy(one_shot_text: str) -> list[str]:
    failures: list[str] = []
    for needle in ["set +e", "setup_rc=$?", "manifest_rc=$?", "inventory_rc=$?", "status_rc=$?", "STRICT_INNOMAKER_CAN"]:
        if needle not in one_shot_text:
            failures.append(f"optional CAN policy missing non-failing marker: {needle}")
    if not _optional_can_required_false_marker_present(one_shot_text):
        failures.append('optional CAN policy missing non-failing marker: "required": false or "required": False')
    if "exit 1" in one_shot_text.split("run_optional_can", 1)[-1].split("prepare_anteater_status", 1)[0] and "STRICT_INNOMAKER_CAN" not in one_shot_text:
        failures.append("optional CAN block can fail without STRICT_INNOMAKER_CAN")
    return failures


def validate_field_readiness_files() -> list[str]:
    failures: list[str] = []
    for helper in FIELD_READINESS_SHELL_HELPERS:
        path = ROOT / helper
        if not path.exists():
            failures.append(f"missing field shell helper: {helper}")
            continue
        rc, _stdout, stderr = run_command(["bash", "-n", helper])
        if rc != 0:
            failures.append(f"field shell helper syntax failed for {helper}: {stderr.strip()}")
    for helper in FIELD_READINESS_PYTHON_HELPERS:
        path = ROOT / helper
        if not path.exists():
            failures.append(f"missing field python helper: {helper}")
            continue
        rc, _stdout, stderr = run_command([sys.executable, "-m", "py_compile", helper])
        if rc != 0:
            failures.append(f"field python helper compile failed for {helper}: {stderr.strip()}")
    manifest = ROOT / "version" / "koalabyte_protocol.json"
    if manifest.exists():
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            for key in ["repo_protocol_version", "features"]:
                if key not in payload:
                    failures.append(f"version manifest missing {key}")
        except Exception as exc:
            failures.append(f"version manifest invalid JSON: {exc}")
    production_text = ""
    for relative in [
        "production/README.md",
        "production/RevA25-heltec-powerbank/PRODUCTION_README_RevA25_HeltecPowerBank.md",
        "production/RevA25-heltec-powerbank/BOM_RevA25_HeltecPowerBank.csv",
        "production/RevA25-heltec-powerbank/USB_POWER_PACK.md",
        "production/RevA25-heltec-powerbank/Safety_Test_Record_RevA25.csv",
    ]:
        path = ROOT / relative
        if path.exists():
            production_text += "\n" + path.read_text(encoding="utf-8", errors="ignore")
    for required in ["Heltec Mesh Node T114", "USB portable power pack", "power bank"]:
        if required not in production_text:
            failures.append(f"production package missing marker: {required}")
    for forbidden in FORBIDDEN_ACTIVE_PRODUCTION_MARKERS:
        if forbidden in production_text:
            failures.append(f"production package still contains active old marker: {forbidden}")
    for forbidden_file in FORBIDDEN_PRODUCTION_FILES:
        if (ROOT / forbidden_file).exists():
            failures.append(f"old production file must be removed: {forbidden_file}")
    return failures


def validate_protected_bluez_menu() -> list[str]:
    failures: list[str] = []
    bluetooth_labels = set(menu_labels("bluetooth"))
    lab_labels = set(menu_labels("lab"))
    all_entries = [entry for entries in SUBMENU_ITEMS.values() for entry in entries]
    commands = {str(entry.get("command", "")) for entry in all_entries}
    for label in REQUIRED_PROTECTED_BLUEZ_LABELS:
        if label not in bluetooth_labels:
            failures.append(f"Bluetooth Tools menu missing protected BlueZ label: {label}")
    for label in REQUIRED_PROTECTED_BLUEZ_LABELS[1:]:
        if label not in lab_labels:
            failures.append(f"Authorized Lab menu missing protected BlueZ label: {label}")
    for command in REQUIRED_PROTECTED_BLUEZ_COMMANDS:
        if command not in commands:
            failures.append(f"menu catalog missing protected BlueZ command: {command}")
    return failures


def validate_greatwhite_reef_menu() -> list[str]:
    failures: list[str] = []
    main_labels = set(menu_labels("main"))
    reef_labels = set(menu_labels("greatwhite_reef"))
    if "GreatWhite Reef" not in main_labels:
        failures.append("Main Canopy missing GreatWhite Reef")
    for label in ["Reef Status", "TigerShark Install Check", "TigerShark Interfaces", "TigerShark PCAP Folder", "TigerShark Read Latest PCAP", "Great Wire Shark Launch Notes", "Great Wire Shark Folder Notes", "GreatWhite Reef Report"]:
        if label not in reef_labels:
            failures.append(f"GreatWhite Reef menu missing label: {label}")
    return failures


def validate_protected_bluez_code() -> list[str]:
    failures: list[str] = []
    required_needles = {
        ROOT / "pi-companion" / "koalablue" / "bluez_protected_lab.py": [
            "ensure_unlocked",
            "KOALABYTE_BLUEZ_LAB_TARGET",
            "KOALABYTE_BLUEZ_OWNED_DEVICE",
            "Outback Radio Ledger",
            "Classic Track Finder",
            "Treehouse RFCOMM Wiremap",
            "Pouch Link Echo",
            "Gumnut GATT Ghostmap",
        ],
        ROOT / "pi-companion" / "koalablue" / "menu_action_runner.py": [
            "koala_bluez_manifest",
            "bluez_gumnut_gatt_ghostmap",
            "bluez_platypus_bt_proxy",
            "_protected_bluez",
        ],
        ROOT / "pi-companion" / "koalablue" / "greatwhite_reef.py": [
            "GREATWHITE_REEF_COMMANDS",
            "greatwhite_pcap_read:",
            "TigerShark",
            "Great Wire Shark",
            "logs/greatwhite_reef",
        ],
        ROOT / "docs" / "GREATWHITE_REEF.md": [
            "TigerShark",
            "Great Wire Shark",
            "logs/greatwhite_reef/pcaps/",
            "PCAP 1",
        ],
        ROOT / "docs" / "KOALA_BLUEZ_TOOLS_REVA16.md": [
            "Outback Module Deck",
            "Protected lab-only BlueZ menu actions",
            "KOALABYTE_BLUEZ_LAB_TARGET",
            "Gumnut GATT Ghostmap",
        ],
        ROOT / "scripts" / "check_full_runtime_dependencies.py": [
            "koalablue.bluez_protected_lab",
            "koalablue.greatwhite_reef",
            "greatwhite_reef_pcap_review",
            "tshark",
            "wireshark",
            "scripts/run_koala_bluez_info.sh",
            "scripts/run_koala_bluez_services.sh",
            "bluez_legacy_lab_optional",
        ],
        ROOT / "scripts" / "setup_system_packages.sh": [
            "tshark",
            "wireshark",
            "GreatWhite Reef",
        ],
    }
    for path, needles in required_needles.items():
        if not path.exists():
            failures.append(f"missing protected/reef file: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in needles:
            if needle not in text:
                failures.append(f"{path.relative_to(ROOT)} missing protected/reef marker: {needle}")
    return failures


def main() -> int:
    failures: list[str] = []
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    menu_manifest, menu_failures = build_manifest()
    failures.extend(f"menu: {failure}" for failure in menu_failures)
    failures.extend(validate_protected_bluez_menu())
    failures.extend(validate_greatwhite_reef_menu())
    failures.extend(validate_protected_bluez_code())
    failures.extend(validate_field_readiness_files())

    buttons: list[dict[str, object]] = []
    try:
        buttons = button_manifest()
    except Exception as exc:
        failures.append(f"buttons: {exc}")

    for helper in REQUIRED_COMMAND_HELPERS:
        if not (ROOT / helper).exists():
            failures.append(f"missing command/control helper: {helper}")
    for project_file in REQUIRED_PROJECT_FILES:
        if not (ROOT / project_file).exists():
            failures.append(f"missing project file: {project_file}")

    one_shot = ROOT / "scripts" / "install_koalabyte_one_shot.sh"
    one_shot_text = one_shot.read_text(encoding="utf-8") if one_shot.exists() else ""
    for snippet in REQUIRED_ONE_SHOT_SNIPPETS:
        if snippet not in one_shot_text:
            failures.append(f"one-shot installer missing required step/policy: {snippet}")
    if not _optional_can_required_false_marker_present(one_shot_text):
        failures.append('one-shot installer missing required step/policy: "required": false or "required": False')
    failures.extend(validate_optional_can_policy(one_shot_text))

    antenna_config = (ROOT / "scripts" / "configure_koalabyte_external_antennas.sh").read_text(encoding="utf-8", errors="ignore")
    for status_path in REQUIRED_ANTENNA_STATUS:
        if status_path not in antenna_config:
            failures.append(f"antenna config missing status path: {status_path}")

    for check in [
        "scripts/check_menu_actions.py",
        "scripts/check_killerkoala_face_mouth_sync.py",
        "scripts/check_menu_display_sync.py",
        "scripts/check_field_readiness.py",
        "scripts/check_koalabyte_version_handshake.py",
    ]:
        rc, stdout, stderr = run_command([sys.executable, check])
        if rc != 0:
            failures.append(f"{check} failed: {stdout} {stderr}".strip())
    rc, stdout, stderr = run_command([sys.executable, "scripts/run_koalabyte_status_server.py", "--json"])
    if rc != 0:
        failures.append(f"run_koalabyte_status_server.py --json failed: {stdout} {stderr}".strip())
    failures.extend(validate_protocol())

    status = {
        "status": "ONE_SHOT_CONTROLS_READY" if not failures else "ONE_SHOT_CONTROLS_INCOMPLETE",
        "buttons": buttons,
        "menu_status": menu_manifest.get("status"),
        "menus": menu_manifest.get("menu_names", []),
        "leaf_count": menu_manifest.get("enabled_leaf_count"),
        "protected_bluez_labels": REQUIRED_PROTECTED_BLUEZ_LABELS,
        "protected_bluez_commands": REQUIRED_PROTECTED_BLUEZ_COMMANDS,
        "greatwhite_reef_enabled": "GreatWhite Reef" in set(menu_labels("main")),
        "one_shot_installer": str(one_shot),
        "optional_can_required": False,
        "field_readiness_files": FIELD_READINESS_SHELL_HELPERS + FIELD_READINESS_PYTHON_HELPERS + REQUIRED_PROJECT_FILES,
        "forbidden_production_files": FORBIDDEN_PRODUCTION_FILES,
        "forbidden_active_production_markers": FORBIDDEN_ACTIVE_PRODUCTION_MARKERS,
        "antenna_status_paths": REQUIRED_ANTENNA_STATUS,
        "updated_at": time.time(),
        "failures": failures,
    }
    STATUS_PATH.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": status["status"], "status_path": str(STATUS_PATH), "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
