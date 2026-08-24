#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
STATUS_PATH="${KOALABYTE_DEPLOYABILITY_STATUS_PATH:-logs/deployability/deployability_status.json}"
mkdir -p "$(dirname "${STATUS_PATH}")"

run_step() {
  local name="$1"
  shift
  echo
  echo "== ${name} =="
  "$@"
}

write_status() {
  local status="$1" reason="$2"
  "${PYTHON_BIN}" - "${STATUS_PATH}" "${status}" "${reason}" <<'PY'
import json, sys, time
from pathlib import Path
path, status, reason = sys.argv[1:]
Path(path).write_text(json.dumps({
    "status": status,
    "reason": reason,
    "gate": "koalabyte_whole_system_deployability",
    "canonical_installer": "one-shot-install.sh",
    "runtime_mode": "headless_pi_os_lite_with_optional_hdmi",
    "hdmi_display": "read_only_auto_detect_with_koalabyte_pi_os_switch",
    "restricted_power_controls": True,
    "firmware_flashing": True,
    "firmware_targets": ["heltec-t114-uf2", "waveshare-esp32-s3-dualeye"],
    "music_engine": "mopidy",
    "can_transmit_during_install": False,
    "updated_at": time.time(),
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

trap 'write_status "DEPLOYABILITY_INCOMPLETE" "deployability gate failed"' ERR

SHELL_HELPERS=(
  install.sh
  one-shot-install.sh
  scripts/setup_pi_hardware_stage.sh
  scripts/setup_system_packages.sh
  scripts/setup_killerkoala_ollama.sh
  scripts/setup_mopidy_player.sh
  scripts/install_power_controls.sh
  scripts/install_koalabyte_udev_rules.sh
  scripts/install_koalabyte_boot_services.sh
  scripts/install_ble_node_manager_service.sh
  scripts/install_esp32_dualeye_voice_bridge_service.sh
  scripts/configure_pi_audio_output.sh
  scripts/build_whole_system_firmware.sh
  scripts/deploy_whole_system_firmware.sh
  scripts/flash_t114_current_uf2.sh
  scripts/flash_esp32_dualeye_current.sh
  scripts/enter_t114_uf2_bootloader.sh
)

run_step "Canonical shell syntax" bash -c '
  for helper in "$@"; do
    test -f "${helper}" || { echo "missing helper: ${helper}" >&2; exit 1; }
    bash -n "${helper}"
  done
' _ "${SHELL_HELPERS[@]}"

run_step "Compile Pi and deployment runtime" "${PYTHON_BIN}" -m compileall -q pi-companion scripts
run_step "Whole-system firmware deployment source" "${PYTHON_BIN}" scripts/check_whole_system_deployment.py --source-only
run_step "K1-K8 and one-shot controls" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_one_shot_controls.py
run_step "Restricted K7/K8 permissions" env KOALABYTE_SERVICE_USER="$(id -un)" bash scripts/install_power_controls.sh --check-only
run_step "Menu actions" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_menu_actions.py
run_step "Menu display sync" env PYTHONPATH=pi-companion KOALABYTE_MENU_SYNC=0 "${PYTHON_BIN}" scripts/check_menu_display_sync.py
run_step "Read-only HDMI display and Pi OS switch" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_hdmi_display.py
run_step "KillerKoala face and mouth protocol" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_killerkoala_face_mouth_sync.py
run_step "KillerKoala AI" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_killerkoala_ai.py
run_step "Mopidy music player" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_music_player.py
run_step "BLE failover" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_ble_role_failover.py
run_step "Universal error sequence" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_killerkoala_error_sequence.py
run_step "Runtime dependencies" env INSTALL_INNOMAKER_CAN=0 PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_full_runtime_dependencies.py
run_step "Hardware-stage check-only" env INSTALL_INNOMAKER_CAN=0 bash scripts/setup_pi_hardware_stage.sh --check-only
run_step "Final whole-system one-shot check-only" env KOALABYTE_SERVICE_USER="$(id -un)" INSTALL_INNOMAKER_CAN=0 bash one-shot-install.sh --check-only

write_status "DEPLOYABILITY_READY" "whole-system firmware ownership, Pi runtime, optional HDMI switch, K1-K8, AI, music, BLE, alarms, services, and no-CAN-transmit policies passed"
trap - ERR

echo
printf 'KoalaByte whole-system deployability gate complete. Status: %s\n' "${STATUS_PATH}"
