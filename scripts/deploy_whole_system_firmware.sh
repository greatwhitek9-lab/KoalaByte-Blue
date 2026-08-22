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
T114_UF2_VOLUME_NAME="${T114_UF2_VOLUME_NAME:-HT-n5262}"
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
required. Immediately before flashing, the host power state is checked again.
Only schema-2, partition-bounded bundles are accepted, and each selected board
must report the exact bundled firmware and protocol identity after flashing.
Recovery states are accepted: a T114 already exposing HT-n5262 UF2 is flashable,
and ESP32-S3 identity is proven by a non-writing chip_id probe before either
board is written, then confirmed again immediately before ESP32 write_flash.
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
[[ "${SKIP_ESP32}" == "1" && "${SKIP_T114}" == "1" ]] && {
  echo "Cannot skip both ESP32 and T114 firmware targets." >&2
  exit 2
}

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
    "transactional_target_preflight": True,
    "schema_2_bundle_required": True,
    "exact_runtime_identity_required": True,
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
  bash -n scripts/probe_esp32_s3.sh
  bash -n scripts/enter_t114_uf2_bootloader.sh
  bash -n scripts/cleanup_firmware_build_tools.sh
  bash -n scripts/preflight_firmware_host.sh
  python3 -m py_compile \
    scripts/check_whole_system_deployment.py scripts/check_firmware_bundle.py \
    scripts/check_verified_firmware_flashes.py scripts/write_firmware_bundle_manifest.py \
    scripts/check_flash_recovery_preflight.py
  python3 scripts/check_flash_recovery_preflight.py
}

selected_requirement() {
  if [[ "${SKIP_ESP32}" == "1" ]]; then printf '%s\n' t114
  elif [[ "${SKIP_T114}" == "1" ]]; then printf '%s\n' esp32
  else printf '%s\n' all
  fi
}

verify_bundle() {
  local requirement
  requirement="$(selected_requirement)"
  python3 scripts/check_firmware_bundle.py \
    --bundle "${BUNDLE_DIR}" --require "${requirement}"
  python3 scripts/check_whole_system_deployment.py \
    --bundle-only --bundle-dir "${BUNDLE_DIR}"
}

t114_uf2_present() {
  command -v lsblk >/dev/null 2>&1 || return 1
  lsblk -pnro LABEL,FSTYPE 2>/dev/null | \
    awk -v label="${T114_UF2_VOLUME_NAME}" \
      '$1 == label && ($2 == "vfat" || $2 == "fat") { found=1 } END { exit(found ? 0 : 1) }'
}

discover_required_devices() {
  local t114_runtime=""
  PYTHONPATH=pi-companion python3 scripts/discover_koalabyte_ports.py --profile heltec --output-dir logs/preflight || true
  if [[ -f logs/preflight/koalabyte_ports.env ]]; then
    # shellcheck disable=SC1091
    source logs/preflight/koalabyte_ports.env
  fi

  if [[ "${REQUIRE_ALL}" != "1" ]]; then
    echo "KOALABYTE_REQUIRE_ALL_PERIPHERALS=${REQUIRE_ALL} no longer bypasses selected-target safety preflight; every selected target must be proven before the first write." >&2
  fi

  if [[ "${SKIP_T114}" != "1" ]]; then
    t114_runtime="${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-${HELTEC_PORT:-}}}"
    if [[ -n "${t114_runtime}" && -e "${t114_runtime}" ]]; then
      echo "Heltec T114 runtime USB detected: ${t114_runtime}"
    elif [[ -e /dev/koalabyte-heltec || -e /dev/koalabyte-heltec-t114 ]]; then
      echo "Heltec T114 runtime alias detected."
    elif t114_uf2_present; then
      echo "Heltec T114 recovery UF2 volume detected: ${T114_UF2_VOLUME_NAME}"
    else
      echo "Heltec T114 was not detected as runtime USB or ${T114_UF2_VOLUME_NAME} UF2 recovery volume immediately before flashing." >&2
      return 1
    fi
  fi

  if [[ "${SKIP_ESP32}" != "1" ]]; then
    bash scripts/probe_esp32_s3.sh
    [[ -f logs/preflight/esp32_chip_probe.env ]] || {
      echo "ESP32-S3 probe succeeded without producing the verified-port environment." >&2
      return 1
    }
    # shellcheck disable=SC1091
    source logs/preflight/esp32_chip_probe.env
    export ESP32_PORT KOALABYTE_ESP32_FACE_PORT
    [[ -n "${ESP32_PORT:-}" && -e "${ESP32_PORT}" ]] || {
      echo "ESP32-S3 verified port disappeared before the transactional preflight completed." >&2
      return 1
    }
    echo "ESP32-S3 transactional preflight verified: ${ESP32_PORT}"
  fi
}

CURRENT_STEP="source_contract"
validate_contract
if [[ "${CHECK_ONLY}" == "1" ]]; then
  bash scripts/build_whole_system_firmware.sh --check-only
  python3 scripts/check_whole_system_deployment.py --source-only
  write_status check_only_ready "Whole-system build/flash source, hardware, protocol, recovery-state, transactional-target, and bundle contracts validated without touching hardware."
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

CURRENT_STEP="verify_schema_2_bundle"
verify_bundle
if [[ "${BUILD_ONLY}" == "1" ]]; then
  write_status built "Firmware bundle built and verified with partition bounds, checksums, and exact runtime identities; flash skipped by --build-only."
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

CURRENT_STEP="post_flash_exact_identity"
sleep 2
PYTHONPATH=pi-companion python3 scripts/discover_koalabyte_ports.py --profile heltec --output-dir logs/preflight
post_args=(--post-flash --bundle-dir "${BUNDLE_DIR}")
[[ "${SKIP_ESP32}" == "1" ]] && post_args+=(--skip-esp32)
[[ "${SKIP_T114}" == "1" ]] && post_args+=(--skip-t114)
python3 scripts/check_whole_system_deployment.py "${post_args[@]}"
python3 scripts/check_verified_firmware_flashes.py \
  --bundle "${BUNDLE_DIR}" --require "$(selected_requirement)"

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
write_status complete "Firmware was built or selected, schema-2 validated, power-gated, all selected targets transactionally preflighted, flashed, and exact firmware/protocol identities were rediscovered."
trap - ERR
restore_services 0
echo "Whole-system peripheral firmware deployment complete."
