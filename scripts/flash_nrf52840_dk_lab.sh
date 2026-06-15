#!/usr/bin/env bash
set -euo pipefail

APP_DIR="firmware/nrf52840-dk-lab-peripheral"
BUILD_DIR="build/nrf52840-dk-lab-peripheral"
BOARD="nrf52840dk_nrf52840"

if ! command -v west >/dev/null 2>&1; then
  echo "west was not found. Install Nordic nRF Connect SDK first." >&2
  echo "See docs/NRF52840_DK_FLASHING.md" >&2
  exit 1
fi

west build -b "$BOARD" "$APP_DIR" -d "$BUILD_DIR"
west flash -d "$BUILD_DIR"
