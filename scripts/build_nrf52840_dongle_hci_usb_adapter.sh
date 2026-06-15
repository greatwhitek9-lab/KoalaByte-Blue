#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-samples/bluetooth/hci_usb}"
BUILD_DIR="${BUILD_DIR:-build/nrf52840-dongle-hci-usb-adapter}"
BOARD="${BOARD:-nrf52840dongle_nrf52840}"

if ! command -v west >/dev/null 2>&1; then
  echo "west was not found. Install Nordic nRF Connect SDK / Zephyr first." >&2
  echo "See docs/EXTERNAL_BT_ADAPTER_MODE_REVA20.md" >&2
  exit 1
fi

echo "Building KoalaByte Blue nRF52840 Dongle HCI USB adapter firmware"
echo "Board: ${BOARD}"
echo "Zephyr app: ${APP_DIR}"
echo "Build dir: ${BUILD_DIR}"
west build -b "$BOARD" "$APP_DIR" -d "$BUILD_DIR"

echo "nRF52840 Dongle HCI USB adapter firmware build complete: ${BUILD_DIR}"
echo "Primary artifacts normally appear under: ${BUILD_DIR}/zephyr/"
echo "Use docs/EXTERNAL_BT_ADAPTER_MODE_REVA20.md for DFU/package flashing guidance."
