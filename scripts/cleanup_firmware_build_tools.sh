#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

STATUS_PATH="${KOALABYTE_BUILD_TOOL_CLEANUP_STATUS:-${ROOT}/logs/deployment/build_tool_cleanup_status.json}"
BUNDLE_DIR="${KOALABYTE_FIRMWARE_BUNDLE_DIR:-${ROOT}/releases/koalabyte-blue-current}"
INSTALL_USER="${SUDO_USER:-${USER:-$(id -un)}}"
INSTALL_HOME="${HOME}"
if command -v getent >/dev/null 2>&1; then
  resolved_home="$(getent passwd "${INSTALL_USER}" | cut -d: -f6 || true)"
  [[ -n "${resolved_home}" ]] && INSTALL_HOME="${resolved_home}"
fi
NCS_WORKSPACE="${NCS_WORKSPACE:-${INSTALL_HOME}/ncs}"
ZEPHYR_SDK_VERSION="${ZEPHYR_SDK_VERSION:-0.16.8}"
ZEPHYR_SDK_INSTALL_DIR="${ZEPHYR_SDK_INSTALL_DIR:-${INSTALL_HOME}/zephyr-sdk-${ZEPHYR_SDK_VERSION}}"
ZEPHYR_SDK_DOWNLOAD_DIR="${ZEPHYR_SDK_DOWNLOAD_DIR:-${INSTALL_HOME}/.cache/koalabyte/zephyr-sdk}"
ESP32_TOOLS_VENV="${ESP32_TOOLS_VENV:-${INSTALL_HOME}/.venvs/platformio}"
NCS_TOOLS_VENV="${NCS_TOOLS_VENV:-${INSTALL_HOME}/.venvs/ncs-tools}"
PLATFORMIO_HOME="${PLATFORMIO_CORE_DIR:-${INSTALL_HOME}/.platformio}"
USER_BIN="${INSTALL_HOME}/.local/bin"
DRY_RUN=0

usage() {
  cat <<'EOF'
Remove firmware build-only toolchains after verified deployment.

Usage:
  bash scripts/cleanup_firmware_build_tools.sh
  bash scripts/cleanup_firmware_build_tools.sh --dry-run

The verified release bundle and Raspberry Pi runtime environment are preserved.
Generated PlatformIO libraries and source files are removed with the SDKs because
they can be reconstructed from pinned sources on the next firmware build.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run|--check-only) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done
mkdir -p "$(dirname "${STATUS_PATH}")"

write_status() {
  local status="$1" reason="$2" reclaimed_kb="${3:-0}"
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${reclaimed_kb}" \
    "${BUNDLE_DIR}" "${NCS_WORKSPACE}" "${ZEPHYR_SDK_INSTALL_DIR}" \
    "${ESP32_TOOLS_VENV}" "${NCS_TOOLS_VENV}" <<'PY'
import json, sys, time
from pathlib import Path
(path, status, reason, reclaimed_kb, bundle, ncs, sdk, pio, ncs_tools) = sys.argv[1:]
Path(path).write_text(json.dumps({
    "status": status,
    "reason": reason,
    "reclaimed_mib": round(int(reclaimed_kb) / 1024, 1),
    "firmware_bundle_preserved": bundle,
    "removed_build_tool_paths": [ncs, sdk, pio, ncs_tools],
    "generated_esp32_dependencies_removed": True,
    "pi_runtime_preserved": True,
    "updated_at": time.time(),
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

required_bundle_files=(
  manifest.json SHA256SUMS.txt
  esp32/bootloader.bin esp32/partitions.bin esp32/boot_app0.bin
  esp32/firmware.bin esp32/srmodels.bin
  t114/koalabyte-t114-current.uf2
)
for relative in "${required_bundle_files[@]}"; do
  [[ -f "${BUNDLE_DIR}/${relative}" ]] || {
    write_status refused "Refusing cleanup because verified firmware bundle file is missing: ${relative}"
    echo "Refusing cleanup: missing ${BUNDLE_DIR}/${relative}" >&2
    exit 1
  }
done
(
  cd "${BUNDLE_DIR}"
  sha256sum -c SHA256SUMS.txt
) || {
  write_status refused "Refusing cleanup because firmware bundle checksums failed."
  exit 1
}

runtime_python="${ROOT}/pi-companion/.venv/bin/python"
[[ -x "${runtime_python}" ]] || {
  write_status refused "Refusing cleanup because Pi runtime virtual environment is unavailable."
  exit 1
}
"${runtime_python}" -c 'import httpx, serial; import koalablue.killerkoala_hybrid_companion' || {
  write_status refused "Refusing cleanup because Pi runtime imports failed."
  exit 1
}

runtime_edge="${ROOT}/pi-companion/.venv/bin/edge-tts"
[[ -x "${runtime_edge}" ]] || {
  write_status refused "Refusing cleanup because runtime edge-tts is unavailable outside PlatformIO."
  exit 1
}
command -v ffmpeg >/dev/null 2>&1 || {
  write_status refused "Refusing cleanup because ffmpeg is unavailable."
  exit 1
}

safe_rm() {
  local target="$1" resolved allowed=0
  [[ -e "${target}" || -L "${target}" ]] || return 0
  resolved="$(readlink -m -- "${target}")"
  for prefix in "${INSTALL_HOME}/" "${ROOT}/"; do
    [[ "${resolved}" == "${prefix}"* ]] && allowed=1
  done
  [[ "${allowed}" == "1" && "${resolved}" != "${INSTALL_HOME}" && "${resolved}" != "${ROOT}" ]] || {
    echo "Unsafe cleanup path refused: ${target} -> ${resolved}" >&2
    return 1
  }
  if [[ "${DRY_RUN}" == "1" ]]; then
    echo "Would remove: ${resolved}"
  else
    rm -rf -- "${resolved}"
    echo "Removed: ${resolved}"
  fi
}

size_kb() {
  local total=0 path value
  for path in "$@"; do
    if [[ -e "${path}" || -L "${path}" ]]; then
      value="$(du -sk -- "${path}" 2>/dev/null | awk '{print $1}' || echo 0)"
      [[ "${value}" =~ ^[0-9]+$ ]] && total=$((total + value))
    fi
  done
  echo "${total}"
}

targets=(
  "${NCS_WORKSPACE}"
  "${ZEPHYR_SDK_INSTALL_DIR}"
  "${ZEPHYR_SDK_DOWNLOAD_DIR}"
  "${NCS_TOOLS_VENV}"
  "${ESP32_TOOLS_VENV}"
  "${PLATFORMIO_HOME}"
  "${ROOT}/build/t114-combined-safe"
  "${ROOT}/firmware/esp32-dualeye/.pio"
  "${ROOT}/firmware/esp32-dualeye/lib/es8311"
  "${ROOT}/firmware/esp32-dualeye/lib/es7210"
  "${ROOT}/firmware/esp32-dualeye/lib/arduino_network_runtime"
  "${ROOT}/firmware/esp32-dualeye/lib/.arduino_network_runtime.staging"
  "${ROOT}/firmware/esp32-dualeye/lib/.waveshare-audio-f16371c"
  "${ROOT}/firmware/esp32-dualeye/src/local_voice_responses_generated.cpp"
  "${ROOT}/firmware/esp32-dualeye/include/generated_voice_menu_catalog.h"
)
before_kb="$(size_kb "${targets[@]}")"
for target in "${targets[@]}"; do safe_rm "${target}"; done

for link in pio platformio edge-tts west; do
  path="${USER_BIN}/${link}"
  if [[ -L "${path}" ]]; then
    destination="$(readlink -f "${path}" 2>/dev/null || true)"
    if [[ "${destination}" == "${ESP32_TOOLS_VENV}/"* || "${destination}" == "${NCS_TOOLS_VENV}/"* || "${destination}" == "${NCS_WORKSPACE}/.venv/"* ]]; then
      safe_rm "${path}"
    fi
  fi
done

if [[ "${DRY_RUN}" == "1" ]]; then
  write_status dry_run "Cleanup validation passed; no files were removed." "${before_kb}"
  exit 0
fi
write_status complete "Verified firmware bundle and Pi runtime were preserved; firmware-only SDKs, generated libraries, sources, and build outputs were removed." "${before_kb}"
echo "Firmware build-tool cleanup complete; approximately $((before_kb / 1024)) MiB removed."
