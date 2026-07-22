#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_USER="${KOALABYTE_SERVICE_USER:-${SUDO_USER:-${USER:-$(id -un)}}}"
SERVICE_HOME="${HOME}"
if command -v getent >/dev/null 2>&1; then
  resolved_home="$(getent passwd "${SERVICE_USER}" | cut -d: -f6 || true)"
  [[ -n "${resolved_home}" ]] && SERVICE_HOME="${resolved_home}"
fi

NCS_WORKSPACE="${NCS_WORKSPACE:-${SERVICE_HOME}/ncs}"
ZEPHYR_SDK_VERSION="${ZEPHYR_SDK_VERSION:-0.17.0}"
ZEPHYR_SDK_INSTALL_DIR="${ZEPHYR_SDK_INSTALL_DIR:-${SERVICE_HOME}/zephyr-sdk-${ZEPHYR_SDK_VERSION}}"
ZEPHYR_SDK_DOWNLOAD_DIR="${ZEPHYR_SDK_DOWNLOAD_DIR:-${SERVICE_HOME}/.cache/koalabyte/zephyr-sdk}"
ESP32_TOOLS_VENV="${ESP32_TOOLS_VENV:-${SERVICE_HOME}/.venvs/platformio}"
PLATFORMIO_HOME_DIR="${PLATFORMIO_HOME_DIR:-${SERVICE_HOME}/.platformio}"
BUNDLE_DIR="${KOALABYTE_FIRMWARE_BUNDLE_DIR:-${ROOT}/releases/koalabyte-blue-current}"
STATUS_PATH="${KOALABYTE_BUILD_TOOL_CLEANUP_STATUS:-${ROOT}/logs/deployment/build_tool_cleanup_status.json}"
CHECK_ONLY=0

usage() {
  cat <<'EOF'
Remove firmware build-only toolchains after a verified KoalaByte deployment.

Usage:
  bash scripts/cleanup_firmware_build_tools.sh
  bash scripts/cleanup_firmware_build_tools.sh --check-only

Preserved:
  - Raspberry Pi runtime virtual environment and services
  - edge-tts/William voice runtime dependency
  - current ESP32 and T114 firmware bundle
  - source tree, logs, manifests, and flashing scripts

Removed:
  - nRF Connect SDK/west workspace
  - Zephyr SDK and its download cache
  - PlatformIO virtual environment and package cache
  - generated ESP32 and T114 build directories

Set CLEANUP_PLATFORMIO=0 or CLEANUP_NORDIC_TOOLCHAIN=0 to retain either toolchain.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) CHECK_ONLY=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

mkdir -p "$(dirname "${STATUS_PATH}")"

is_enabled() {
  case "$1" in
    1|true|True|yes|YES|on|ON|auto|AUTO) return 0 ;;
    *) return 1 ;;
  esac
}

path_size_kb() {
  local path="$1"
  if [[ -e "${path}" || -L "${path}" ]]; then
    du -sk "${path}" 2>/dev/null | awk '{print $1}' || echo 0
  else
    echo 0
  fi
}

safe_removable_path() {
  local path="$1"
  [[ -n "${path}" ]] || return 1
  [[ "${path}" != "/" && "${path}" != "${SERVICE_HOME}" && "${path}" != "${ROOT}" ]] || return 1
  case "${path}" in
    "${SERVICE_HOME}"/*|"${ROOT}"/*) return 0 ;;
    *) return 1 ;;
  esac
}

removed_paths=()
retained_paths=()
reclaimed_kb=0

remove_path() {
  local path="$1" size_kb
  if [[ ! -e "${path}" && ! -L "${path}" ]]; then
    return 0
  fi
  if ! safe_removable_path "${path}"; then
    echo "Refusing unsafe cleanup path: ${path}" >&2
    return 1
  fi
  size_kb="$(path_size_kb "${path}")"
  echo "Removing build-only path: ${path} ($((size_kb / 1024)) MiB)"
  if [[ "${CHECK_ONLY}" != "1" ]]; then
    rm -rf -- "${path}"
  fi
  reclaimed_kb=$((reclaimed_kb + size_kb))
  removed_paths+=("${path}")
}

require_firmware_bundle() {
  local required=(
    "${BUNDLE_DIR}/manifest.json"
    "${BUNDLE_DIR}/esp32/bootloader.bin"
    "${BUNDLE_DIR}/esp32/partitions.bin"
    "${BUNDLE_DIR}/esp32/firmware.bin"
    "${BUNDLE_DIR}/esp32/srmodels.bin"
    "${BUNDLE_DIR}/t114/koalabyte-t114-current.uf2"
  )
  local missing=() path
  for path in "${required[@]}"; do
    [[ -f "${path}" ]] || missing+=("${path}")
  done
  if (( ${#missing[@]} > 0 )); then
    echo "Refusing build-tool cleanup because the current firmware bundle is incomplete:" >&2
    printf '  %s\n' "${missing[@]}" >&2
    return 1
  fi
}

write_status() {
  local status="$1" reason="$2"
  REMOVED_PATHS="$(printf '%s\n' "${removed_paths[@]:-}")" \
  RETAINED_PATHS="$(printf '%s\n' "${retained_paths[@]:-}")" \
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${reclaimed_kb}" \
    "${BUNDLE_DIR}" "${CHECK_ONLY}" <<'PY'
import json
import os
import sys
import time
from pathlib import Path

path, status, reason, reclaimed_kb, bundle, check_only = sys.argv[1:]
removed = [line for line in os.environ.get("REMOVED_PATHS", "").splitlines() if line]
retained = [line for line in os.environ.get("RETAINED_PATHS", "").splitlines() if line]
payload = {
    "status": status,
    "reason": reason,
    "check_only": check_only == "1",
    "reclaimed_kib": int(reclaimed_kb),
    "reclaimed_mib": round(int(reclaimed_kb) / 1024, 1),
    "firmware_bundle_preserved": bundle,
    "removed_paths": removed,
    "retained_paths": retained,
    "updated_at": time.time(),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

require_firmware_bundle

echo "== KoalaByte firmware build-tool cleanup =="
echo "Firmware bundle preserved: ${BUNDLE_DIR}"
echo "Service user/home: ${SERVICE_USER} ${SERVICE_HOME}"

runtime_edge_tts="${ROOT}/pi-companion/.venv/bin/edge-tts"
platformio_cleanup="${CLEANUP_PLATFORMIO:-1}"
nordic_cleanup="${CLEANUP_NORDIC_TOOLCHAIN:-1}"

if is_enabled "${nordic_cleanup}"; then
  remove_path "${NCS_WORKSPACE}"
  remove_path "${ZEPHYR_SDK_INSTALL_DIR}"
  remove_path "${ZEPHYR_SDK_DOWNLOAD_DIR}"
  remove_path "${ROOT}/build/t114-combined-safe"
else
  retained_paths+=("${NCS_WORKSPACE}" "${ZEPHYR_SDK_INSTALL_DIR}")
fi

if is_enabled "${platformio_cleanup}"; then
  if [[ -x "${runtime_edge_tts}" ]]; then
    remove_path "${ESP32_TOOLS_VENV}"
    remove_path "${PLATFORMIO_HOME_DIR}"
    remove_path "${ROOT}/firmware/esp32-dualeye/.pio"
    remove_path "${SERVICE_HOME}/.local/bin/pio"
    remove_path "${SERVICE_HOME}/.local/bin/platformio"
    if [[ "${CHECK_ONLY}" != "1" ]]; then
      mkdir -p "${SERVICE_HOME}/.local/bin"
      ln -sfn "${runtime_edge_tts}" "${SERVICE_HOME}/.local/bin/edge-tts"
    fi
    echo "William voice runtime preserved: ${runtime_edge_tts}"
  else
    echo "Warning: Pi runtime edge-tts is missing; retaining PlatformIO environment as a voice fallback." >&2
    retained_paths+=("${ESP32_TOOLS_VENV}" "${PLATFORMIO_HOME_DIR}")
  fi
else
  retained_paths+=("${ESP32_TOOLS_VENV}" "${PLATFORMIO_HOME_DIR}")
fi

if [[ "${CHECK_ONLY}" == "1" ]]; then
  write_status "check_only_ready" "Cleanup paths and preserved firmware bundle validated."
  echo "Cleanup check complete; no files were removed."
else
  write_status "complete" "Build-only toolchains removed after successful deployment."
  echo "Build-tool cleanup complete. Approximate space reclaimed: $((reclaimed_kb / 1024)) MiB"
fi
