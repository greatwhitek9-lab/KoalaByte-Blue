#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${T114_HCI_BUILD_DIR:-build/nrf52840-t114-hci-usb}"
STATUS_PATH="${T114_ACTIVE_BLE_MODE_PATH:-logs/t114_active_ble_mode.json}"
FLASH_METHOD="${T114_FLASH_METHOD:-west}"
PORT="${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-}}"
BUILD_FIRST="${T114_HCI_BUILD_FIRST:-1}"
STRICT="${STRICT_T114_HCI_FLASH:-1}"

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
  "mode": "t114_koala_konnect",
  "hci_profile": "t114_hci_usb",
  "product_mode": "Koala Konnect",
  "build_dir": $(json_escape "${BUILD_DIR}"),
  "flash_method": $(json_escape "${FLASH_METHOD}"),
  "port": $(json_escape "${PORT}"),
  "external_bluetooth_adapter": true,
  "host_expectation": "After replugging, supported hosts may expose the Heltec board as an external Bluetooth HCI adapter. Host driver support is required.",
  "verify_linux": "bluetoothctl list && bluetoothctl show && bluetoothctl --timeout 15 scan on",
  "updated_at": $(date +%s)
}
JSON
}

if [[ "${BUILD_FIRST}" == "1" ]]; then
  STRICT_T114_HCI_BUILD="${STRICT}" bash scripts/build_nrf52840_t114_hci_usb.sh
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
    write_status "flashed" "T114 HCI USB firmware flashed with west."
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
    write_status "flashed" "T114 HCI USB firmware copied to UF2 mount."
    ;;
  *)
    write_status "unsupported_method" "Unsupported T114_FLASH_METHOD. Use west or uf2."
    exit 2
    ;;
esac

echo "T114 HCI USB flash helper complete. Verify on Linux with: bluetoothctl list && bluetoothctl show && bluetoothctl --timeout 15 scan on"
