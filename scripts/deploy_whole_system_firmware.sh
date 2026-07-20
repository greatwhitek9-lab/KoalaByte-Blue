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

Default behavior is strict: both the T114 and ESP32 must be connected and both
must flash successfully. Standalone use restarts the previously stopped runtime
services. The canonical one-shot sets KOALABYTE_DEFER_SERVICE_RESTART=1 because
it provisions and starts the final services after flashing.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) CHECK_ONLY=1 ;;
    --build-only) BUILD_ONLY=1 ;;
    --use-existing-bundle) USE_EXISTING_BUNDLE=1 ;;
    --skip-esp32) SKIP_ESP32=1 ;;
    --skip-t114) SKIP_T114=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

mkdir -p "${ROOT}/logs/deployment" "${ROOT}/logs/preflight"
CURRENT_STEP="initializing"
STARTED_AT="$(date +%s)"

write_status() {
  local status="$1" reason="$2"
  python3 - "${STATUS_PATH}" "${status}" "${CURRENT_STEP}" "${reason}" \
    "${BUNDLE_DIR}" "${SKIP_ESP32}" "${SKIP_T114}" "${STARTED_AT}" \
    "${DEFER_SERVICE_RESTART}" <<'PY'
import json, sys, time
from pathlib import Path
(path, status, step, reason, bundle, skip_esp32, skip_t114, started,
 defer_restart) = sys.argv[1:]
Path(path).write_text(json.dumps({
    "status": status,
    "step": step,
    "reason": reason,
    "bundle_dir": bundle,
    "esp32_required": skip_esp32 != "1",
    "t114_required": skip_t114 != "1",
    "service_restart_deferred": defer_restart == "1",
    "can_transmit": False,
    "started_at": int(started),
    "updated_at": time.time(),
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

sudo_systemctl() {
  command -v systemctl >/dev/null 2>&1 || return 0
  if [[ "${EUID}" -eq 0 ]]; then
    systemctl "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo systemctl "$@"
  fi
}

stop_serial_services() {
  local service
  for service in "${SERVICES[@]}"; do
    if sudo_systemctl list-unit-files "${service}" >/dev/null 2>&1; then
      sudo_systemctl stop "${service}" >/dev/null 2>&1 || true
    fi
  done
}

restore_services() {
  local service
  [[ "${CHECK_ONLY}" == "1" || "${BUILD_ONLY}" == "1" ]] && return 0
  [[ "${DEFER_SERVICE_RESTART}" == "1" ]] && return 0
  for service in "${SERVICES[@]}"; do
    if sudo_systemctl list-unit-files "${service}" >/dev/null 2>&1; then
      sudo_systemctl restart "${service}" >/dev/null 2>&1 || true
    fi
  done
}

on_error() {
  local rc=$?
  write_status "failed" "Deployment stopped at ${CURRENT_STEP} with exit ${rc}. Re-run the same one-shot command after correcting the reported hardware condition."
  restore_services
  exit "${rc}"
}
trap on_error ERR

validate_contract() {
  bash -n scripts/deploy_whole_system_firmware.sh
  bash -n scripts/build_whole_system_firmware.sh
  bash -n scripts/flash_t114_current_uf2.sh
  bash -n scripts/flash_esp32_dualeye_current.sh
  bash -n scripts/enter_t114_uf2_bootloader.sh
  python3 -m py_compile scripts/check_whole_system_deployment.py
}

CURRENT_STEP="source_contract"
validate_contract
if [[ "${CHECK_ONLY}" == "1" ]]; then
  bash scripts/build_whole_system_firmware.sh --check-only
  bash scripts/flash_t114_current_uf2.sh --check-only 2>/dev/null || true
  bash scripts/flash_esp32_dualeye_current.sh --check-only 2>/dev/null || true
  python3 scripts/check_whole_system_deployment.py --source-only
  write_status "check_only_ready" "Whole-system build/flash/deployment source contract validated without touching hardware."
  trap - ERR
  exit 0
fi

if [[ "$(uname -s)" != "Linux" ]]; then
  write_status "unsupported_host" "Whole-system deployment must run on the Raspberry Pi Linux host."
  exit 1
fi

CURRENT_STEP="stop_runtime_services"
write_status "running" "Stopping services that own ESP32/T114 serial ports."
stop_serial_services

CURRENT_STEP="device_preflight"
PYTHONPATH=pi-companion python3 scripts/discover_koalabyte_ports.py --profile heltec --output-dir logs/preflight || true
if [[ -f logs/preflight/koalabyte_ports.env ]]; then
  # shellcheck disable=SC1091
  source logs/preflight/koalabyte_ports.env
fi

if [[ "${REQUIRE_ALL}" == "1" ]]; then
  if [[ "${SKIP_ESP32}" != "1" && -z "${ESP32_PORT:-${KOALABYTE_ESP32_FACE_PORT:-${KOALABYTE_ESP32_DUALEYE_BY_ID:-}}}" ]]; then
    write_status "hardware_missing" "ESP32-S3 DualEye was not detected."
    echo "Connect the ESP32-S3 DualEye before running the complete one-shot." >&2
    exit 1
  fi
  if [[ "${SKIP_T114}" != "1" && -z "${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-${HELTEC_PORT:-}}}" && ! -e /dev/koalabyte-heltec ]]; then
    write_status "hardware_missing" "Heltec T114 was not detected."
    echo "Connect the Heltec T114 before running the complete one-shot." >&2
    exit 1
  fi
fi

CURRENT_STEP="build_firmware_bundle"
if [[ "${USE_EXISTING_BUNDLE}" != "1" ]]; then
  args=()
  [[ "${SKIP_ESP32}" == "1" ]] && args+=(--skip-esp32)
  [[ "${SKIP_T114}" == "1" ]] && args+=(--skip-t114)
  bash scripts/build_whole_system_firmware.sh "${args[@]}"
fi

CURRENT_STEP="verify_bundle_checksums"
(
  cd "${BUNDLE_DIR}"
  sha256sum -c SHA256SUMS.txt
)
python3 scripts/check_whole_system_deployment.py --bundle-only --bundle-dir "${BUNDLE_DIR}"

if [[ "${BUILD_ONLY}" == "1" ]]; then
  write_status "built" "Whole-system firmware bundle built and verified; hardware flash skipped by --build-only."
  trap - ERR
  exit 0
fi

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
python3 scripts/check_whole_system_deployment.py --post-flash --bundle-dir "${BUNDLE_DIR}"

CURRENT_STEP="complete"
write_status "complete" "T114 UF2 and complete ESP32-S3 image set were built, checksummed, flashed, and rediscovered."
trap - ERR
restore_services
echo "Whole-system peripheral firmware deployment complete."
