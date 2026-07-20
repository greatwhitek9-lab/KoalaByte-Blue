#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

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
payload = {
    "status": status,
    "reason": reason,
    "gate": "koalabyte_pi_deployability",
    "canonical_installer": "one-shot-install.sh",
    "runtime_mode": "headless_pi_os_lite",
    "restricted_power_controls": True,
    "firmware_flashing": False,
    "can_transmit_during_install": False,
    "updated_at": time.time(),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

trap 'write_status "DEPLOYABILITY_INCOMPLETE" "deployability gate failed"' ERR

SHELL_HELPERS=(
  install.sh
  one-shot-install.sh
  scripts/setup_pi_hardware_stage.sh
  scripts/setup_system_packages.sh
  scripts/install_power_controls.sh
  scripts/install_koalabyte_udev_rules.sh
  scripts/install_koalabyte_boot_services.sh
  scripts/install_ble_node_manager_service.sh
  scripts/install_esp32_dualeye_voice_bridge_service.sh
  scripts/configure_pi_audio_output.sh
  scripts/koalabyte_blue_boot.sh
)

run_step "Canonical shell syntax" bash -c '
  for helper in "$@"; do
    test -f "${helper}" || { echo "missing helper: ${helper}" >&2; exit 1; }
    bash -n "${helper}"
  done
' _ "${SHELL_HELPERS[@]}"

run_step "Compile Pi runtime" "${PYTHON_BIN}" -m compileall -q pi-companion scripts
run_step "Repository readiness" "${PYTHON_BIN}" scripts/check_repo_readiness.py
run_step "K1-K8 and one-shot controls" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_one_shot_controls.py
run_step "Restricted K7/K8 permissions" env KOALABYTE_SERVICE_USER="$(id -un)" bash scripts/install_power_controls.sh --check-only
run_step "Menu actions" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_menu_actions.py
run_step "Menu display sync" env PYTHONPATH=pi-companion KOALABYTE_MENU_SYNC=0 "${PYTHON_BIN}" scripts/check_menu_display_sync.py
run_step "KillerKoala face and mouth protocol" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_killerkoala_face_mouth_sync.py
run_step "KillerKoala AI" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_killerkoala_ai.py
run_step "Runtime dependencies" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_full_runtime_dependencies.py
run_step "Hardware-stage check-only" bash scripts/setup_pi_hardware_stage.sh --check-only
run_step "Final one-shot check-only" env KOALABYTE_SERVICE_USER="$(id -un)" bash one-shot-install.sh --check-only

write_status "DEPLOYABILITY_READY" "canonical Pi OS Lite one-shot, K1-K8, restricted power controls, menu, voice, display sync, services, and no-flash policies passed"
trap - ERR

echo
printf 'KoalaByte Pi deployability gate complete. Status: %s\n' "${STATUS_PATH}"
