#!/usr/bin/env bash
set -euo pipefail

APP_DIR="firmware/nrf52840-dk-lab-peripheral"
BUILD_DIR="build/nrf52840-dongle-lab"
BOARD="${BOARD:-nrf52840dongle_nrf52840}"

if ! command -v west >/dev/null 2>&1; then
  echo "west was not found. Install Nordic nRF Connect SDK first." >&2
  echo "See docs/NRF52840_DONGLE_FLASHING.md" >&2
  exit 1
fi

echo "Building KoalaByte Blue nRF52840 Dongle Zephyr firmware"
echo "Board: ${BOARD}"
echo "App: ${APP_DIR}"
echo "Build dir: ${BUILD_DIR}"
west build -b "$BOARD" "$APP_DIR" -d "$BUILD_DIR"

echo "nRF52840 Dongle Ear Tag TX Lab firmware build complete: ${BUILD_DIR}"
echo "Primary artifacts normally appear under: ${BUILD_DIR}/zephyr/"
echo "Use docs/NRF52840_DONGLE_FLASHING.md for DFU/package flashing guidance."
