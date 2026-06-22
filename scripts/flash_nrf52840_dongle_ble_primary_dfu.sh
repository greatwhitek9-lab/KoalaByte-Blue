#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${BUILD_DIR:-build/nrf52840-dongle-ble-primary}"
DFU_PORT="${NRF_DFU_PORT:-}"
PACKAGE="${PACKAGE:-${BUILD_DIR}/koalabyte-blue-nrf52840-dongle-ble-primary-dfu.zip}"
HEX="${HEX:-${BUILD_DIR}/zephyr/zephyr.hex}"
APP_VERSION="${APP_VERSION:-2}"
HW_VERSION="${HW_VERSION:-52}"
SD_REQ="${SD_REQ:-0x00}"
STRICT_NRF_DFU_PORT="${STRICT_NRF_DFU_PORT:-0}"
STATUS_PATH="logs/nrf52840_dongle_ble_primary_dfu_status.json"
mkdir -p logs

write_status() {
  local flashed="$1"
  local message="$2"
  cat > "${STATUS_PATH}" <<JSON
{
  "package": "${PACKAGE}",
  "hex": "${HEX}",
  "nrf_dfu_port": "${DFU_PORT}",
  "flashed": ${flashed},
  "message": "${message}",
  "runtime_port_hint": "${KOALABYTE_NRF_BLE_PORT:-/dev/koalabyte-nrf-ble}"
}
JSON
}

if [[ ! -f "${HEX}" ]]; then
  echo "Missing firmware hex: ${HEX}" >&2
  echo "Build first: bash scripts/build_nrf52840_dongle_ble_primary.sh" >&2
  write_status false "missing firmware hex"
  exit 1
fi

STRICT_NRF_TOOLS="${STRICT_NRF_TOOLS:-1}" bash scripts/setup_nrf_tools.sh --nrfutil-only

mkdir -p "$(dirname "${PACKAGE}")"
nrfutil pkg generate \
  --hw-version "${HW_VERSION}" \
  --sd-req "${SD_REQ}" \
  --application "${HEX}" \
  --application-version "${APP_VERSION}" \
  "${PACKAGE}"

echo "DFU package created: ${PACKAGE}"

if [[ -z "${DFU_PORT}" ]]; then
  echo "WARNING: NRF_DFU_PORT is not set. Package was created but the nRF52840 Dongle was not flashed." >&2
  echo "Put the dongle into DFU mode and rerun, for example: NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_nrf52840_dongle_ble_primary_dfu.sh" >&2
  write_status false "NRF_DFU_PORT not set; package created but not flashed"
  [[ "${STRICT_NRF_DFU_PORT}" == "1" ]] && exit 1
  exit 0
fi

echo "Flashing over serial DFU port: ${DFU_PORT}"
nrfutil dfu usb-serial -pkg "${PACKAGE}" -p "${DFU_PORT}"
write_status true "Dongle BLE primary DFU complete"
echo "Dongle BLE primary DFU complete."
