#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

APP_DIR="firmware/nrf52840-dongle-ear-tag-tx-lab"
BUILD_DIR="${BUILD_DIR:-build/nrf52840-dongle-lab}"
BOARD="${BOARD:-nrf52840dongle_nrf52840}"

STRICT_NRF_TOOLS="${STRICT_NRF_TOOLS:-1}" bash scripts/setup_nrf_tools.sh --west-only
STRICT_NCS_TOOLCHAIN="${STRICT_NCS_TOOLCHAIN:-1}" bash scripts/setup_nrf_connect_sdk_toolchain.sh
if [[ -f "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh" ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh"
fi

if [[ ! -f "${APP_DIR}/CMakeLists.txt" || ! -f "${APP_DIR}/prj.conf" || ! -f "${APP_DIR}/src/main.c" ]]; then
  echo "Missing nRF52840 Dongle KoalaByte Lab source files under ${APP_DIR}." >&2
  exit 1
fi

echo "Building KoalaByte Lab nRF52840 Dongle Zephyr firmware"
echo "Repository root: ${REPO_ROOT}"
echo "Board: ${BOARD}"
echo "App: ${APP_DIR}"
echo "Build dir: ${BUILD_DIR}"
west build -b "${BOARD}" "${APP_DIR}" -d "${BUILD_DIR}"

echo "nRF52840 Dongle KoalaByte Lab firmware build complete: ${BUILD_DIR}"
echo "Primary artifacts normally appear under: ${BUILD_DIR}/zephyr/"
echo "Next step: NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_nrf52840_dongle_lab_dfu.sh"
