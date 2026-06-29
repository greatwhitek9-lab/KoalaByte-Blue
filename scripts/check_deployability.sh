#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
STATUS_PATH="${KOALABYTE_DEPLOYABILITY_STATUS_PATH:-logs/deployability/deployability_status.json}"
STRICT_DEPLOYABILITY="${STRICT_DEPLOYABILITY:-0}"

mkdir -p "$(dirname "${STATUS_PATH}")" logs/deployability

run_step() {
  local name="$1"
  shift
  echo
  echo "== ${name} =="
  "$@"
}

write_status() {
  local status="$1"
  local reason="$2"
  "${PYTHON_BIN}" - <<'PY' "${STATUS_PATH}" "${status}" "${reason}" "${STRICT_DEPLOYABILITY}"
import json
import sys
import time
from pathlib import Path

path, status, reason, strict = sys.argv[1:]
payload = {
    "status": status,
    "reason": reason,
    "gate": "koalabyte_blue_deployability",
    "checks": [
        "shell syntax for deploy/install/flash helpers",
        "repo readiness",
        "runtime dependency import coverage",
        "menu/action readiness",
        "K1-K8 one-shot control readiness",
        "first-boot WiFi helper check-only",
        "system package helper check-only",
        "ESP32 PlatformIO helper check-only",
        "Heltec T114 helper check-only",
        "T114 plug-flash helper check-only",
        "UF2-first one-shot option check-only",
        "udev/boot/logrotate helper check-only",
        "antenna helper check-only",
        "Heltec hardware preflight profile",
        "flash_all_components check-only",
    ],
    "strict_deployability": strict == "1",
    "updated_at": time.time(),
}
Path(path).parent.mkdir(parents=True, exist_ok=True)
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(payload, sort_keys=True))
PY
}

trap 'write_status "DEPLOYABILITY_INCOMPLETE" "deployability gate failed before completion"' ERR

SHELL_HELPERS=(
  install.sh
  scripts/install_koalabyte_one_shot.sh
  scripts/install_pi.sh
  scripts/flash_all_components.sh
  scripts/flash_esp32.sh
  scripts/flash_t114_when_plugged.sh
  scripts/flash_t114_combined_safe.sh
  scripts/build_t114_combined_safe.sh
  scripts/flash_heltec_mouth.sh
  scripts/setup_wifi_first_boot.sh
  scripts/setup_system_packages.sh
  scripts/setup_esp32_tools.sh
  scripts/setup_heltec_t114_tools.sh
  scripts/setup_nrf_tools.sh
  scripts/setup_nrf_connect_sdk_toolchain.sh
  scripts/setup_bluez_gatttool.sh
  scripts/setup_killerkoala_ollama.sh
  scripts/configure_koalabyte_external_antennas.sh
  scripts/configure_esp32s3_dualeye_2g4_antenna.sh
  scripts/configure_t114_2g4_antenna.sh
  scripts/configure_t114_lora_external_antenna.sh
  scripts/install_koalabyte_udev_rules.sh
  scripts/install_koalabyte_boot_services.sh
  scripts/install_koalabyte_logrotate.sh
  scripts/koalabyte_doctor.sh
  scripts/koalabyte_safe_mode.sh
  scripts/export_koalabyte_logs.sh
  scripts/build_koalabyte_release_package.sh
)

run_step "Shell syntax for install and flash helpers" bash -c '
  for helper in "$@"; do
    test -f "${helper}" || { echo "missing helper: ${helper}" >&2; exit 1; }
    bash -n "${helper}"
  done
' _ "${SHELL_HELPERS[@]}"

run_step "Compile Python scripts and Pi companion" "${PYTHON_BIN}" -m compileall pi-companion scripts
run_step "Repo readiness" "${PYTHON_BIN}" scripts/check_repo_readiness.py
run_step "Runtime dependency coverage" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_full_runtime_dependencies.py
run_step "Menu action readiness" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_menu_actions.py
run_step "Menu display sync readiness" env PYTHONPATH=pi-companion KOALABYTE_MENU_SYNC=0 "${PYTHON_BIN}" scripts/check_menu_display_sync.py
run_step "K1-K8 one-shot controls" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_one_shot_controls.py

run_step "WiFi first-boot helper check-only" bash scripts/setup_wifi_first_boot.sh --check-only
run_step "System package helper check-only" bash scripts/setup_system_packages.sh --check-only
run_step "ESP32 PlatformIO helper check-only" bash scripts/setup_esp32_tools.sh --check-only
run_step "Heltec T114 helper check-only" bash scripts/setup_heltec_t114_tools.sh --check-only
run_step "nRF helper check-only" bash scripts/setup_nrf_tools.sh --check-only
run_step "nRF Connect SDK helper check-only" bash scripts/setup_nrf_connect_sdk_toolchain.sh --check-only
run_step "BlueZ gatttool helper check-only" bash scripts/setup_bluez_gatttool.sh --check-only
run_step "KillerKoala Ollama helper check-only" bash scripts/setup_killerkoala_ollama.sh --check-only
run_step "External antenna helper check-only" bash scripts/configure_koalabyte_external_antennas.sh --check-only
run_step "ESP32 antenna helper check-only" bash scripts/configure_esp32s3_dualeye_2g4_antenna.sh --check-only
run_step "T114 plug flash helper check-only" bash scripts/flash_t114_when_plugged.sh --check-only
run_step "T114 required-UF2 flash helper check-only" env T114_REQUIRE_UF2=1 T114_FLASH_METHOD=uf2 bash scripts/flash_t114_when_plugged.sh --check-only
run_step "one-shot UF2-first option check-only" bash scripts/install_koalabyte_one_shot.sh --check-only --heltec-uf2-first
run_step "udev rule helper check-only" bash scripts/install_koalabyte_udev_rules.sh --check-only
run_step "boot service helper check-only" bash scripts/install_koalabyte_boot_services.sh --check-only
run_step "logrotate helper check-only" bash scripts/install_koalabyte_logrotate.sh --check-only
run_step "Heltec profile hardware preflight" "${PYTHON_BIN}" scripts/preflight_all_hardware.py --profile heltec
run_step "flash_all_components check-only" bash scripts/flash_all_components.sh --check-only
run_step "one-shot installer check-only" bash scripts/install_koalabyte_one_shot.sh --check-only

if [[ "${STRICT_DEPLOYABILITY}" == "1" ]]; then
  run_step "strict runtime host-command dependency coverage" env PYTHONPATH=pi-companion STRICT_FULL_RUNTIME_DEPENDENCIES=1 "${PYTHON_BIN}" scripts/check_full_runtime_dependencies.py --strict-commands
fi

trap - ERR
write_status "DEPLOYABILITY_READY" "install, dependency, menu, helper, and flash dry-run checks passed"
echo
printf 'KoalaByte deployability gate complete. Status: %s\n' "${STATUS_PATH}"
