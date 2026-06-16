#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

APP_DIR="${APP_DIR:-samples/bluetooth/hci_usb}"
BUILD_DIR="${BUILD_DIR:-build/nrf52840-dongle-koala-konnect}"
BOARD="${BOARD:-nrf52840dongle_nrf52840}"

STRICT_NRF_TOOLS="${STRICT_NRF_TOOLS:-1}" bash scripts/setup_nrf_tools.sh --west-only
STRICT_NCS_TOOLCHAIN="${STRICT_NCS_TOOLCHAIN:-1}" bash scripts/setup_nrf_connect_sdk_toolchain.sh
if [[ -f "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh" ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh"
fi

if [[ "${APP_DIR}" == samples/* && -n "${NCS_WORKSPACE:-}" && -d "${NCS_WORKSPACE}/zephyr/${APP_DIR}" ]]; then
  APP_DIR="${NCS_WORKSPACE}/zephyr/${APP_DIR}"
fi

echo "Building Koala Konnect for KoalaByte Blue nRF52840 Dongle"
echo "Mode: Koala Konnect external Bluetooth adapter"
echo "Board: ${BOARD}"
echo "Zephyr app: ${APP_DIR}"
echo "Build dir: ${BUILD_DIR}"
west build -b "$BOARD" "$APP_DIR" -d "$BUILD_DIR"

echo "Koala Konnect firmware build complete: ${BUILD_DIR}"
echo "Primary artifacts normally appear under: ${BUILD_DIR}/zephyr/"
echo "Use docs/KOALA_KONNECT_REVA20.md for DFU/package flashing guidance."
