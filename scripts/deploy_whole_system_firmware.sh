#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

CHECK_ONLY=0
BUILD_ONLY=0
USE_EXISTING_BUNDLE=0
SKIP_ESP32=0
SKIP_T114=0
BUNDLE_DIR="${KOALABYTE_FIRMWARE_BUNDLE_DIR:-${ROOT}/releases/koalabyte-blue-current}"
STATUS_PATH="${KOALABYTE_FIRMWARE_DEPLOY_STATUS:-${ROOT}/logs/deployment/whole_system_deployment_status.json}"
REQUIRE_ALL="${KOALABYTE_REQUIRE_ALL_PERIPHERALS:-1}"
DEFER_SERVICE_RESTART="${KOALABYTE_DEFER_SERVICE_RESTART:-0}"
CLEANUP_FIRMWARE_BUILD_TOOLS="${CLEANUP_FIRMWARE_BUILD_TOOLS:-1}"
SERVICES=(
  koalabyte-dualeye-voice-bridge.service
  koalabyte-ble-node-manager.service
  koalabyte-menu.service
  koalabyte-doctor.service
)

usage() {
  cat <<'EOF'
Build and flash the complete KoalaByte Blue peripheral firmware set.

Usage:
  bash scripts/deploy_whole_system_firmware.sh
  bash scripts/deploy_whole_system_firmware.sh --check-only
  bash scripts/deploy_whole_system_firmware.sh --build-only
  bash scripts/deploy_whole_system_firmware.sh --use-existing-bundle
  bash scripts/deploy_whole_system_firmware.sh --skip-esp32
  bash scripts/deploy_whole_system_firmware.sh --skip-t114
  bash scripts/deploy_whole_system_firmware.sh --keep-build-tools

Source builds finish before serial services are stopped or USB devices are
required. Immediately before flashing, the host power state is checked again,
then both selected devices are identified, flashed, and rediscovered. A failed
flash always restores any services stopped by this transaction.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) CHECK_ONLY=1 ;;
    --build-only) BUILD_ONLY=1 ;;
    --use-existing-bundle) USE_EXISTING_BUNDLE=1 ;;
    --skip-esp32) SKIP_ESP32=1 ;;
    --skip-t114) SKIP_T114=1 ;;
    --keep-build-tools) CLEANUP_FIRMWARE_BUILD_TOOLS=0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

mkdir -p "${ROOT}/logs/deployment" "${ROOT}/logs/preflight"
CURRENT_STEP="initializing"
STARTED_AT="$(date +%s)"
SERVICES_STOPPED=0

is_enabled() {
  case "$1" in
    1|true|True|yes|YES|on|ON|auto|AUTO) return 0 ;;
    *) return 1 ;;
  esac
}

write_status() {
  local status="$1" reason="$2"
  python3 - "${STATUS_PATH}" "${status}" "${CURRENT_STEP}" "${reason}" \
    "${BUNDLE_DIR}" "${SKIP_ESP32}" "${SKIP_T114}" "${STARTED_AT}" \
    "${DEFER_SERVICE_RESTART}" "${CLEANUP_FIRMWARE_BUILD_TOOLS}" <<'PY'
import json, sys, time
from pathlib import Path
(path, status, step, reason, bundle, skip_esp32, skip_t114, started,
 defer_restart, cleanup_tools) = sys.argv[1:]
Path(path).write_text(json.dumps({
    "status": status,
    "step": step,
    "reason": reason,
    "bundle_dir": bundle,
    "esp32_required": skip_esp32 != "1",
    "t114_required": skip_t114 != "1",
    "service_restart_deferred": defer_restart == "1",
    "build_tool_cleanup_requested": cleanup_tools.lower() in {"1", "true", "yes", "on", "auto"},
    "pre_flash_power_gate": True,
    "failure_restores_services": True,
    "can_transmit": False,
    "started_at": int(started),
    "updated_at": time.time(),
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

sudo_systemctl() {
  command -v systemctl >/dev/null 2>&1 || return 0
  if [[ "${EUID}" -eq 0 ]]; then systemctl "$@"
  elif command -v sudo >/dev/null 2>&1; then sudo systemctl "$@"
  fi
}

stop_serial_services() {
  local service
  for service in "${SERVICES[@]}"; do
    if sudo_systemctl list-unit-files "${service}" >/dev/null 2>&1; then
      sudo_systemctl stop "${service}" >/dev/null 2>&1 || true
    fi
  done
  SERVICES_STOPPED=1
}

restore_services() {
  local force="${1:-0}" service
  [[ "${SERVICES_STOPPED}" == "1" ]] || return 0
  [[ "${CHECK_ONLY}" == "1" || "${BUILD_ONLY}" == "1" ]] && return 0
  if [[ "${force}" != "1" && "${DEFER_SERVICE_RESTART}" == "1" ]]; then
    return 0
  fi
  for service in "${SERVICES[@]}"; do
    if sudo_systemctl list-unit-files "${service}" >/dev/null 2>&1; then
      sudo_systemctl restart "${service}" >/dev/null 2>&1 || true
    fi
  done
  SERVICES_STOPPED=0
}

on_error() {
  local rc=$?
  write_status failed "Deployment stopped at ${CURRENT_STEP} with exit ${rc}. The verified firmware bundle was retained and previously running services were restored; correct the reported condition and rerun."
  restore_services 1
  exit "${rc}"
}
trap on_error ERR

validate_contract() {
  bash -n scripts/deploy_whole_system_firmware.sh
  bash -n scripts/build_whole_system_firmware.sh
  bash -n scripts/flash_t114_current_uf2.sh
  bash -n scripts/flash_esp32_dualeye_current.sh
  bash -n scripts/enter_t114_uf2_bootloader.sh
  bash -n scripts/cleanup_firmware_build_tools.sh
  bash -n scripts/preflight_firmware_host.sh
  python3 -m py_compile scripts/check_whole_system_deployment.py
}

verify_bundle() {
  test -f "${BUNDLE_DIR}/SHA256SUMS.txt"
  (
    cd "${BUNDLE_DIR}"
    sha256sum -c SHA256SUMS.txt
  )
  python3 scripts/check_whole_system_deployment.py --bundle-only --bundle-dir "${BUNDLE_DIR}"
}

discover_required_devices() {
  PYTHONPATH=pi-companion python3 scripts/discover_koalabyte_ports.py --profile heltec --output-dir logs/preflight || true
  if [[ -f logs/preflight/koalabyte_ports.env ]]; then
    # shellcheck disable=SC1091
    source logs/preflight/koalabyte_ports.env
  fi
  [[ "${REQUIRE_ALL}" == "1" ]] || return 0
  if [[ "${SKIP_ESP32}" != "1" && -z "${ESP32_PORT:-${KOALABYTE_ESP32_FACE_PORT:-${KOALABYTE_ESP32_DUALEYE_BY_ID:-}}}" ]]; then
    echo "ESP32-S3 DualEye was not detected immediately before flashing." >&2
    return 1
  fi
  if [[ "${SKIP_T114}" != "1" && -z "${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-${HELTEC_PORT:-}}}" && ! -e /dev/koalabyte-heltec ]]; then
    echo "Heltec T114 was not detected immediately before flashing." >&2
    return 1
  fi
}

CURRENT_STEP="source_contract"
validate_contract
if [[ "${CHECK_ONLY}" == "1" ]]; then
  bash scripts/build_whole_system_firmware.sh --check-only
  python3 scripts/check_whole_system_deployment.py --source-only
  write_status check_only_ready "Whole-system build/flash source contract validated without touching hardware."
  trap - ERR
  exit 0
fi

[[ "$(uname -s)" == "Linux" ]] || { echo "Firmware deployment requires Linux." >&2; exit 1; }

CURRENT_STEP="build_firmware_bundle"
if [[ "${USE_EXISTING_BUNDLE}" != "1" ]]; then
  args=()
  [[ "${SKIP_ESP32}" == "1" ]] && args+=(--skip-esp32)
  [[ "${SKIP_T114}" == "1" ]] && args+=(--skip-t114)
  bash scripts/build_whole_system_firmware.sh "${args[@]}"
fi

CURRENT_STEP="verify_bundle_checksums"
verify_bundle
if [[ "${BUILD_ONLY}" == "1" ]]; then
  write_status built "Whole-system firmware bundle built and verified; flash skipped by --build-only."
  trap - ERR
  exit 0
fi

CURRENT_STEP="pre_flash_power_gate"
bash scripts/preflight_firmware_host.sh --before-flash

CURRENT_STEP="stop_runtime_services"
stop_serial_services

CURRENT_STEP="device_preflight"
discover_required_devices

if [[ "${SKIP_T114}" != "1" ]]; then
  CURRENT_STEP="flash_t114_uf2"
  bash scripts/flash_t114_current_uf2.sh
fi

if [[ "${SKIP_ESP32}" != "1" ]]; then
  CURRENT_STEP="flash_esp32_complete_image"
  bash scripts/flash_esp32_dualeye_current.sh
fi

CURRENT_STEP="post_flash_discovery"
sleep 2
PYTHONPATH=pi-companion python3 scripts/discover_koalabyte_ports.py --profile heltec --output-dir logs/preflight
python3 scripts/check_whole_system_deployment.py --post-flash --bundle-dir "${BUNDLE_DIR}" \
  $([[ "${SKIP_ESP32}" == "1" ]] && printf '%s' '--skip-esp32') \
  $([[ "${SKIP_T114}" == "1" ]] && printf '%s' '--skip-t114')

if is_enabled "${CLEANUP_FIRMWARE_BUILD_TOOLS}"; then
  if [[ "${SKIP_ESP32}" == "1" || "${SKIP_T114}" == "1" ]]; then
    echo "Build-tool cleanup skipped after partial deployment."
  else
    CURRENT_STEP="cleanup_firmware_build_tools"
    if ! bash scripts/cleanup_firmware_build_tools.sh; then
      echo "warning: firmware was flashed successfully, but build-tool cleanup was incomplete" >&2
    fi
  fi
else
  echo "Firmware build toolchains retained by configuration."
fi

CURRENT_STEP="complete"
write_status complete "Firmware was built or selected, checksummed, power-gated, flashed, and rediscovered."
trap - ERR
restore_services 0
echo "Whole-system peripheral firmware deployment complete."
