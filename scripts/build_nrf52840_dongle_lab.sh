#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

APP_DIR="firmware/nrf52840-dongle-ear-tag-tx-lab"
BUILD_DIR="${BUILD_DIR:-build/nrf52840-dongle-lab}"
BOARD="${BOARD:-nrf52840dongle_nrf52840}"

if ! command -v west >/dev/null 2>&1; then
  echo "west was not found. Install Nordic nRF Connect SDK first." >&2
  echo "See docs/NRF52840_DONGLE_FLASHING.md" >&2
  exit 1
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
