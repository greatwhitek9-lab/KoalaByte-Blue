#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

APP_DIR="firmware/nrf52840-dongle-ble-primary"
BUILD_DIR="${BUILD_DIR:-build/nrf52840-dongle-ble-primary}"
BOARD="${BOARD:-nrf52840dongle_nrf52840}"

STRICT_NRF_TOOLS="${STRICT_NRF_TOOLS:-1}" bash scripts/setup_nrf_tools.sh --west-only
STRICT_NCS_TOOLCHAIN="${STRICT_NCS_TOOLCHAIN:-1}" bash scripts/setup_nrf_connect_sdk_toolchain.sh
if [[ -f "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh" ]]; then
  source "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh"
fi

if [[ ! -f "${APP_DIR}/CMakeLists.txt" || ! -f "${APP_DIR}/prj.conf" || ! -f "${APP_DIR}/src/main.c" ]]; then
  echo "Missing source files under ${APP_DIR}." >&2
  exit 1
fi

echo "Building ${APP_DIR} for ${BOARD}"
west build -b "${BOARD}" "${APP_DIR}" -d "${BUILD_DIR}"
echo "Build complete: ${BUILD_DIR}"
