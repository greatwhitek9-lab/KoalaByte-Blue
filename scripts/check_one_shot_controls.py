#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
for path in (ROOT, PI_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from koalablue.gpio_buttons import DEFAULT_BUTTONS, DEFAULT_ELECTRICAL_MODE
from scripts.check_killerkoala_face_mouth_sync import validate_protocol
from scripts.check_menu_actions import build_manifest

STATUS_PATH = ROOT / "logs" / "one_shot" / "control_surface_status.json"
ONE_SHOT = ROOT / "one-shot-install.sh"

REQUIRED_INSTALLER_MARKERS = (
    "scripts/setup_pi_hardware_stage.sh",
    "scripts/deploy_whole_system_firmware.sh",
    "scripts/build_whole_system_firmware.sh",
    "scripts/flash_t114_current_uf2.sh",
    "scripts/flash_esp32_dualeye_current.sh",
    "scripts/setup_mopidy_player.sh",
    "--install-runtime-services",
    "scripts/setup_gpio_buttons.py",
    "scripts/discover_koalabyte_ports.py",
    "scripts/install_power_controls.sh",
    "scripts/install_ble_node_manager_service.sh",
    "scripts/install_esp32_dualeye_voice_bridge_service.sh",
    "scripts/pi_hardware_doctor.py",
    "scripts/run_hdmi_display.py",
    "scripts/set_hdmi_display_mode.py",
    "scripts/check_hdmi_display.py",
    "koalabyte-hdmi.service",
    "firmware_flashing",
    "KOALABYTE_REQUIRE_ALL_PERIPHERALS",
    "can_transmit_during_install",
    "INSTALL_INNOMAKER_CAN",
    "--check-only",
)

FORBIDDEN_INSTALLER_MARKERS = (
    "verify_prebuilt_firmware_bundle",
    "firmware/prebuilt/manifest.json",
    "koalabyte-menu-sync.service",
    "scripts/install_koalabyte_one_shot.sh",
)

REQUIRED_FILES = (
    "one-shot-install.sh",
    "install.sh",
    "scripts/run_headless_menu.py",
    "scripts/run_hdmi_display.py",
    "scripts/set_hdmi_display_mode.py",
    "scripts/setup_pi_hardware_stage.sh",
    "scripts/setup_gpio_buttons.py",
    "scripts/test_gpio_buttons.py",
    "scripts/pi_hardware_doctor.py",
    "scripts/discover_koalabyte_ports.py",
    "scripts/install_power_controls.sh",
    "scripts/install_koalabyte_udev_rules.sh",
    "scripts/install_koalabyte_boot_services.sh",
    "scripts/install_ble_node_manager_service.sh",
    "scripts/install_esp32_dualeye_voice_bridge_service.sh",
    "scripts/configure_pi_audio_output.sh",
    "scripts/setup_mopidy_player.sh",
    "scripts/build_whole_system_firmware.sh",
    "scripts/deploy_whole_system_firmware.sh",
    "scripts/flash_t114_current_uf2.sh",
    "scripts/flash_esp32_dualeye_current.sh",
    "scripts/enter_t114_uf2_bootloader.sh",
    "scripts/check_whole_system_deployment.py",
    "scripts/check_menu_actions.py",
    "scripts/check_menu_display_sync.py",
    "scripts/check_hdmi_display.py",
    "scripts/check_killerkoala_face_mouth_sync.py",
    "scripts/check_music_player.py",
    "pi-companion/koalablue/gpio_buttons.py",
    "pi-companion/koalablue/menu_action_runner.py",
    "pi-companion/koalablue/hdmi_display.py",
    "pi-companion/koalablue/hdmi_display_state.py",
    "pi-companion/koalablue/music_player.py",
    "pi-companion/koalablue/mopidy_player.py",
    "systemd/koalabyte-menu.service",
    "systemd/koalabyte-hdmi.service",
    "systemd/koalabyte-doctor.service",
    "desktop/koalabyte-hdmi-toggle.desktop",
    "docs/HDMI_DISPLAY.md",
    "udev/99-koalabyte-blue.rules",
)

SHELL_FILES = (
    "one-shot-install.sh",
    "install.sh",
    "scripts/setup_pi_hardware_stage.sh",
    "scripts/install_power_controls.sh",
    "scripts/install_koalabyte_udev_rules.sh",
    "scripts/install_koalabyte_boot_services.sh",
    "scripts/install_ble_node_manager_service.sh",
    "scripts/install_esp32_dualeye_voice_bridge_service.sh",
    "scripts/configure_pi_audio_output.sh",
    "scripts/setup_mopidy_player.sh",
    "scripts/build_whole_system_firmware.sh",
    "scripts/deploy_whole_system_firmware.sh",
    "scripts/flash_t114_current_uf2.sh",
    "scripts/flash_esp32_dualeye_current.sh",
    "scripts/enter_t114_uf2_bootloader.sh",
)

PYTHON_FILES = (
    "scripts/run_headless_menu.py",
    "scripts/run_hdmi_display.py",
    "scripts/set_hdmi_display_mode.py",
    "scripts/check_hdmi_display.py",
    "scripts/setup_gpio_buttons.py",
    "scripts/test_gpio_buttons.py",
    "scripts/pi_hardware_doctor.py",
    "scripts/discover_koalabyte_ports.py",
    "scripts/check_whole_system_deployment.py",
    "scripts/check_music_player.py",
    "pi-companion/koalablue/gpio_buttons.py",
    "pi-companion/koalablue/hdmi_display.py",
    "pi-companion/koalablue/hdmi_display_state.py",
    "pi-companion/koalablue/music_player.py",
    "pi-companion/koalablue/mopidy_player.py",
)


def run(command: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    return proc.returncode, proc.stdout, proc.stderr


def validate_buttons() -> tuple[list[dict[str, object]], list[str]]:
    failures: list[str] = []
    rows: list[dict[str, object]] = []
    numbers: set[int] = set()
    pins: set[int] = set()
    commands: set[str] = set()

    for key, cfg in sorted(DEFAULT_BUTTONS.items(), key=lambda item: int(item[1]["number"])):
        number = int(cfg["number"])
        pin = int(cfg["pin"])
        command = str(cfg.get("press_command", ""))
        numbers.add(number)
        pins.add(pin)
        commands.add(command)
        rows.append({
            "id": key,
            "number": number,
            "module_key": cfg.get("module_key", f"K{number}"),
            "label": cfg.get("label"),
            "pin_bcm": pin,
            "physical_pin": cfg.get("physical_pin"),
            "command": command,
            "requires_hold": bool(cfg.get("requires_hold", False)),
            "hold_seconds": float(cfg.get("hold_seconds", 0.0)),
        })

    if numbers != set(range(1, 9)):
        failures.append(f"K1-K8 numbering is incomplete: {sorted(numbers)}")
    if len(pins) != 8:
        failures.append("K1-K8 GPIO pins are not unique")
    expected = {"main_menu", "move_left", "select", "move_right", "up", "down", "power_toggle", "reset"}
    missing = expected - commands
    if missing:
        failures.append(f"K1-K8 commands missing: {sorted(missing)}")

    by_number = {row["number"]: row for row in rows}
    for number, command, minimum in ((7, "power_toggle", 2.5), (8, "reset", 3.0)):
        row = by_number.get(number, {})
        if row.get("command") != command:
            failures.append(f"K{number} must map to {command}")
        if not row.get("requires_hold"):
            failures.append(f"K{number} must require a deliberate hold")
        if float(row.get("hold_seconds", 0.0)) < minimum:
            failures.append(f"K{number} hold must be at least {minimum:.1f}s")

    if not DEFAULT_ELECTRICAL_MODE.pull_up:
        failures.append("K1-K8 must use the Pi internal pull-up")
    if DEFAULT_ELECTRICAL_MODE.idle_state != "HIGH":
        failures.append("K1-K8 idle state must be HIGH")
    if DEFAULT_ELECTRICAL_MODE.pressed_state != "LOW":
        failures.append("K1-K8 pressed state must be LOW")
    return rows, failures


def validate_power_controls() -> list[str]:
    failures: list[str] = []
    path = ROOT / "scripts/install_power_controls.sh"
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    for marker in ("NOPASSWD", "shutdown", "-h now", "reboot", "visudo"):
        if marker not in text:
            failures.append(f"restricted power installer missing marker: {marker}")
    return failures


def main() -> int:
    failures: list[str] = []
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    for relative in REQUIRED_FILES:
        if not (ROOT / relative).exists():
            failures.append(f"missing required whole-system file: {relative}")

    installer_text = ONE_SHOT.read_text(encoding="utf-8") if ONE_SHOT.exists() else ""
    for marker in REQUIRED_INSTALLER_MARKERS:
        if marker not in installer_text:
            failures.append(f"final one-shot missing marker: {marker}")
    for marker in FORBIDDEN_INSTALLER_MARKERS:
        if marker in installer_text:
            failures.append(f"final one-shot still contains obsolete path: {marker}")

    for relative in SHELL_FILES:
        if not (ROOT / relative).exists():
            continue
        rc, _stdout, stderr = run(["bash", "-n", relative])
        if rc != 0:
            failures.append(f"shell syntax failed for {relative}: {stderr.strip()}")

    for relative in PYTHON_FILES:
        if not (ROOT / relative).exists():
            continue
        rc, _stdout, stderr = run([sys.executable, "-m", "py_compile", relative])
        if rc != 0:
            failures.append(f"Python compile failed for {relative}: {stderr.strip()}")

    buttons, button_failures = validate_buttons()
    failures.extend(button_failures)
    failures.extend(validate_power_controls())
    menu_manifest, menu_failures = build_manifest()
    failures.extend(f"menu: {failure}" for failure in menu_failures)
    failures.extend(validate_protocol())

    status = {
        "status": "ONE_SHOT_CONTROLS_READY" if not failures else "ONE_SHOT_CONTROLS_INCOMPLETE",
        "canonical_installer": "one-shot-install.sh",
        "bootstrapper": "install.sh",
        "runtime_mode": "headless_pi_os_lite_with_optional_hdmi",
        "hdmi_display": "read_only_auto_detect_with_koalabyte_pi_os_switch",
        "live_display_sync_owner": "koalabyte-menu.service",
        "restricted_power_controls": True,
        "firmware_flashing": True,
        "firmware_targets": ["heltec-t114-uf2", "waveshare-esp32-s3-dualeye"],
        "firmware_build_source": "current_checkout",
        "music_engine": "mopidy",
        "can_transmit_during_install": False,
        "button_board": "K1-K8 8-key front-panel module",
        "buttons": buttons,
        "menu_status": menu_manifest.get("status"),
        "menus": menu_manifest.get("menu_names", []),
        "leaf_count": menu_manifest.get("enabled_leaf_count"),
        "updated_at": time.time(),
        "failures": failures,
    }
    STATUS_PATH.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": status["status"], "status_path": str(STATUS_PATH), "failures": failures}, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
