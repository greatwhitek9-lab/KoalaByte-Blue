#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
for path in (ROOT, PI_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

REQUIRED_FILES = (
    "README.md",
    "install.sh",
    "one-shot-install.sh",
    "pi-companion/requirements.txt",
    "pi-companion/config.default.json",
    "pi-companion/koalablue/gpio_buttons.py",
    "pi-companion/koalablue/menu_catalog.py",
    "pi-companion/koalablue/menu_ui.py",
    "pi-companion/koalablue/menu_theme.py",
    "pi-companion/koalablue/menu_display_sync.py",
    "pi-companion/koalablue/menu_action_runner.py",
    "pi-companion/koalablue/killerkoala_hybrid_companion.py",
    "pi-companion/koalablue/dualeye_tts.py",
    "pi-companion/koalablue/esp32_dualeye_latched_koalagotchi_bridge.py",
    "scripts/run_headless_menu.py",
    "scripts/setup_pi_hardware_stage.sh",
    "scripts/setup_system_packages.sh",
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
    "scripts/check_one_shot_controls.py",
    "scripts/check_menu_actions.py",
    "scripts/check_menu_display_sync.py",
    "scripts/check_killerkoala_face_mouth_sync.py",
    "scripts/check_killerkoala_ai.py",
    "scripts/check_full_runtime_dependencies.py",
    "scripts/koalabyte_blue_boot.sh",
    "udev/99-koalabyte-blue.rules",
    "systemd/koalabyte-menu.service",
    "systemd/koalabyte-menu-sync.service",
    "systemd/koalabyte-doctor.service",
)

SHELL_FILES = (
    "install.sh",
    "one-shot-install.sh",
    "scripts/setup_pi_hardware_stage.sh",
    "scripts/setup_system_packages.sh",
    "scripts/install_power_controls.sh",
    "scripts/install_koalabyte_udev_rules.sh",
    "scripts/install_koalabyte_boot_services.sh",
    "scripts/install_ble_node_manager_service.sh",
    "scripts/install_esp32_dualeye_voice_bridge_service.sh",
    "scripts/configure_pi_audio_output.sh",
    "scripts/koalabyte_blue_boot.sh",
)

PYTHON_FILES = (
    "scripts/run_headless_menu.py",
    "scripts/setup_gpio_buttons.py",
    "scripts/test_gpio_buttons.py",
    "scripts/pi_hardware_doctor.py",
    "scripts/discover_koalabyte_ports.py",
    "scripts/check_one_shot_controls.py",
    "pi-companion/koalablue/gpio_buttons.py",
    "pi-companion/koalablue/menu_display_sync.py",
    "pi-companion/koalablue/killerkoala_hybrid_companion.py",
)

REQUIRED_REQUIREMENTS = (
    "bleak",
    "pyserial",
    "fastapi",
    "uvicorn",
    "httpx",
    "gpiozero",
    "pygame",
    "python-can",
    "pyttsx3",
    "SpeechRecognition",
    "edge-tts",
)


def run(command: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    return proc.returncode, proc.stdout, proc.stderr


def check_markers(failures: list[str]) -> None:
    installer = (ROOT / "one-shot-install.sh").read_text(encoding="utf-8", errors="ignore")
    for marker in (
        "--install-runtime-services",
        "scripts/setup_gpio_buttons.py",
        "scripts/discover_koalabyte_ports.py",
        "scripts/install_power_controls.sh",
        "scripts/pi_hardware_doctor.py",
        "firmware_flashing",
        "can_transmit_during_install",
    ):
        if marker not in installer:
            failures.append(f"one-shot-install.sh missing marker: {marker}")
    for forbidden in (
        "flash_esp32",
        "flash_t114",
        "verify_prebuilt_firmware_bundle",
        "firmware/prebuilt/manifest.json",
    ):
        if forbidden in installer:
            failures.append(f"canonical installer contains obsolete firmware path: {forbidden}")

    gpio = (ROOT / "pi-companion/koalablue/gpio_buttons.py").read_text(encoding="utf-8", errors="ignore")
    for marker in ("K7", "K8", "requires_hold", "2.5", "3.0", "when_held"):
        if marker not in gpio:
            failures.append(f"GPIO manager missing protected-button marker: {marker}")

    power = (ROOT / "scripts/install_power_controls.sh").read_text(encoding="utf-8", errors="ignore")
    for marker in ("NOPASSWD", "shutdown", "-h now", "reboot", "visudo"):
        if marker not in power:
            failures.append(f"restricted power installer missing marker: {marker}")

    service = (ROOT / "systemd/koalabyte-menu.service").read_text(encoding="utf-8", errors="ignore")
    for marker in ("run_headless_menu.py", "Restart=always", "WantedBy=multi-user.target"):
        if marker not in service:
            failures.append(f"headless menu service missing marker: {marker}")

    rules = (ROOT / "udev/99-koalabyte-blue.rules").read_text(encoding="utf-8", errors="ignore")
    for marker in ("2fe3", "0100", "303a", "1001", "koalabyte-heltec", "koalabyte-esp32-dualeye"):
        if marker not in rules:
            failures.append(f"udev rules missing device marker: {marker}")


def main() -> int:
    failures: list[str] = []

    for relative in REQUIRED_FILES:
        if not (ROOT / relative).exists():
            failures.append(f"missing required runtime file: {relative}")

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

    requirements = (ROOT / "pi-companion/requirements.txt").read_text(encoding="utf-8", errors="ignore").lower()
    for requirement in REQUIRED_REQUIREMENTS:
        if requirement.lower() not in requirements:
            failures.append(f"requirements.txt missing: {requirement}")

    try:
        json.loads((ROOT / "pi-companion/config.default.json").read_text(encoding="utf-8"))
    except Exception as exc:
        failures.append(f"config.default.json is invalid: {exc}")

    check_markers(failures)

    if failures:
        print("KoalaByte repository readiness failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("KoalaByte repository readiness passed: one canonical Pi installer, headless runtime, protected K1-K8 controls, restricted power permissions, stable device aliases, and no installer firmware flashing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
