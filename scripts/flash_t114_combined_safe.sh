#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${T114_COMBINED_BUILD_DIR:-build/t114-combined-safe}"
STATUS_PATH="${T114_COMBINED_FLASH_STATUS_PATH:-logs/t114_combined_safe_flash_status.json}"
FLASH_METHOD="${T114_FLASH_METHOD:-auto}"
BUILD_FIRST="${T114_COMBINED_BUILD_FIRST:-1}"
STRICT="${STRICT_T114_COMBINED_FLASH:-1}"
PORT="${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-}}"
UF2_VOLUME_NAME="${T114_UF2_VOLUME_NAME:-HT-n5262}"

mkdir -p "$(dirname "${STATUS_PATH}")"

json_escape() {
  python3 - <<'PY' "$1"
import json, sys
print(json.dumps(sys.argv[1]))
PY
}

find_uf2_mount() {
  if [[ -n "${T114_UF2_MOUNT:-}" && -d "${T114_UF2_MOUNT}" ]]; then
    printf '%s\n' "${T114_UF2_MOUNT}"
    return 0
  fi
  local user_name="${SUDO_USER:-${USER:-}}"
  local candidates=()
  if [[ -n "${user_name}" ]]; then
    candidates+=("/media/${user_name}/${UF2_VOLUME_NAME}" "/run/media/${user_name}/${UF2_VOLUME_NAME}")
  fi
  candidates+=("/media/${UF2_VOLUME_NAME}" "/mnt/${UF2_VOLUME_NAME}" "/Volumes/${UF2_VOLUME_NAME}")
  candidates+=("/media"/*/"${UF2_VOLUME_NAME}" "/run/media"/*/"${UF2_VOLUME_NAME}")
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -d "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

write_status() {
  local status="$1"
  local reason="$2"
  local mount="${3:-}"
  cat > "${STATUS_PATH}" <<JSON
{
  "status": $(json_escape "${status}"),
  "reason": $(json_escape "${reason}"),
  "mode": "t114_combined_safe",
  "profile": "combined-safe",
  "build_dir": $(json_escape "${BUILD_DIR}"),
  "flash_method": $(json_escape "${FLASH_METHOD}"),
  "port": $(json_escape "${PORT}"),
  "uf2_volume_name": $(json_escape "${UF2_VOLUME_NAME}"),
  "uf2_mount": $(json_escape "${mount}"),
  "primary_ble": "heltec-t114-nrf52840",
  "secondary_ble_nodes": ["esp32-s3-dualeye", "raspberry-pi-bluez"],
  "host_expectation": "After flashing, the Heltec emits newline-delimited JSON over USB CDC for mouth/status, passive BLE observations, and guarded GNSS/LoRa readiness hooks.",
  "updated_at": $(date +%s)
}
JSON
}

if [[ "${BUILD_FIRST}" == "1" ]]; then
  STRICT_T114_COMBINED_BUILD="${STRICT}" bash scripts/build_t114_combined_safe.sh
fi

if [[ "${FLASH_METHOD}" == "auto" ]]; then
  if find_uf2_mount >/dev/null; then
    FLASH_METHOD="uf2"
  else
    FLASH_METHOD="west"
  fi
fi

case "${FLASH_METHOD}" in
  west)
    if ! command -v west >/dev/null 2>&1; then
      write_status "missing_west" "west is not installed. Double-tap RST on the T114 and rerun with the HT-n5262 UF2 volume mounted, or install nRF Connect SDK/west."
      exit 1
    fi
    if [[ ! -d "${BUILD_DIR}" ]]; then
      write_status "missing_build" "Build directory does not exist."
      exit 1
    fi
    west flash -d "${BUILD_DIR}"
    write_status "flashed" "T114 combined-safe firmware flashed with west."
    ;;
  uf2)
    UF2="${T114_UF2_PATH:-${BUILD_DIR}/zephyr/zephyr.uf2}"
    MOUNT="$(find_uf2_mount || true)"
    if [[ -z "${MOUNT}" || ! -d "${MOUNT}" ]]; then
      write_status "missing_uf2_mount" "Double-tap RST on the T114 until the HT-n5262 UF2 volume appears, or set T114_UF2_MOUNT to the mounted volume path." ""
      exit 1
    fi
    if [[ ! -f "${UF2}" ]]; then
      write_status "missing_uf2" "UF2 artifact not found. Build should produce build/t114-combined-safe/zephyr/zephyr.uf2." "${MOUNT}"
      exit 1
    fi
    cp "${UF2}" "${MOUNT}/"
    sync
    write_status "flashed" "T114 combined-safe firmware copied to HT-n5262 UF2 volume." "${MOUNT}"
    ;;
  *)
    write_status "unsupported_method" "Unsupported T114_FLASH_METHOD. Use auto, west, or uf2."
    exit 2
    ;;
esac

echo "T114 combined-safe flash helper complete. Verify JSON with: python3 scripts/discover_koalabyte_ports.py --profile heltec && PYTHONPATH=pi-companion python3 scripts/run_ble_node_manager.py --duration 30"
