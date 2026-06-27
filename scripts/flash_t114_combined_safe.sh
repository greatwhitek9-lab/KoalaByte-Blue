#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${T114_COMBINED_BUILD_DIR:-build/t114-combined-safe}"
STATUS_PATH="${T114_COMBINED_FLASH_STATUS_PATH:-logs/t114_combined_safe_flash_status.json}"
FLASH_METHOD="${T114_FLASH_METHOD:-west}"
BUILD_FIRST="${T114_COMBINED_BUILD_FIRST:-1}"
STRICT="${STRICT_T114_COMBINED_FLASH:-1}"
PORT="${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-}}"

mkdir -p "$(dirname "${STATUS_PATH}")"

json_escape() {
  python3 - <<'PY' "$1"
import json, sys
print(json.dumps(sys.argv[1]))
PY
}

write_status() {
  local status="$1"
  local reason="$2"
  cat > "${STATUS_PATH}" <<JSON
{
  "status": $(json_escape "${status}"),
  "reason": $(json_escape "${reason}"),
  "mode": "t114_combined_safe",
  "profile": "combined-safe",
  "build_dir": $(json_escape "${BUILD_DIR}"),
  "flash_method": $(json_escape "${FLASH_METHOD}"),
  "port": $(json_escape "${PORT}"),
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

case "${FLASH_METHOD}" in
  west)
    if ! command -v west >/dev/null 2>&1; then
      write_status "missing_west" "west is not installed."
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
    MOUNT="${T114_UF2_MOUNT:-}"
    if [[ -z "${MOUNT}" || ! -d "${MOUNT}" ]]; then
      write_status "missing_uf2_mount" "T114_UF2_MOUNT must point at the mounted T114 UF2 volume."
      exit 1
    fi
    if [[ ! -f "${UF2}" ]]; then
      write_status "missing_uf2" "UF2 artifact not found."
      exit 1
    fi
    cp "${UF2}" "${MOUNT}/"
    sync
    write_status "flashed" "T114 combined-safe firmware copied to UF2 mount."
    ;;
  *)
    write_status "unsupported_method" "Unsupported T114_FLASH_METHOD. Use west or uf2."
    exit 2
    ;;
esac

echo "T114 combined-safe flash helper complete. Verify JSON with: python3 scripts/discover_koalabyte_ports.py --profile heltec && PYTHONPATH=pi-companion python3 scripts/run_ble_node_manager.py --duration 30"
