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

if [[ ! -f "${HEX}" ]]; then
  echo "Missing firmware hex: ${HEX}" >&2
  echo "Build first: bash scripts/build_nrf52840_dongle_ble_primary.sh" >&2
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
  echo "No NRF_DFU_PORT set, so the package was created but not flashed."
  exit 0
fi

echo "Flashing over serial DFU port: ${DFU_PORT}"
nrfutil dfu usb-serial -pkg "${PACKAGE}" -p "${DFU_PORT}"
echo "Dongle BLE primary DFU complete."
