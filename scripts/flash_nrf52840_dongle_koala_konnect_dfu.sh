#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${BUILD_DIR:-build/nrf52840-dongle-koala-konnect}"
DFU_PORT="${NRF_DFU_PORT:-}"
PACKAGE="${PACKAGE:-${BUILD_DIR}/koala-konnect-nrf52840-dongle-dfu.zip}"
HEX="${HEX:-${BUILD_DIR}/zephyr/zephyr.hex}"
APP_VERSION="${APP_VERSION:-20}"
HW_VERSION="${HW_VERSION:-52}"
SD_REQ="${SD_REQ:-0x00}"

if [[ ! -f "$HEX" ]]; then
  echo "Missing Koala Konnect firmware hex: $HEX" >&2
  echo "Build first: bash scripts/build_nrf52840_dongle_hci_usb_adapter.sh" >&2
  exit 1
fi

STRICT_NRF_TOOLS="${STRICT_NRF_TOOLS:-1}" bash scripts/setup_nrf_tools.sh --nrfutil-only

echo "Packaging Koala Konnect nRF52840 Dongle DFU zip"
mkdir -p "$(dirname "$PACKAGE")"
nrfutil pkg generate \
  --hw-version "$HW_VERSION" \
  --sd-req "$SD_REQ" \
  --application "$HEX" \
  --application-version "$APP_VERSION" \
  "$PACKAGE"

echo "Koala Konnect DFU package created: $PACKAGE"

if [[ -z "$DFU_PORT" ]]; then
  echo "No NRF_DFU_PORT set, so package was created but not flashed."
  echo "Put the dongle in bootloader mode, identify the serial port, then run for example:"
  echo "  NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_nrf52840_dongle_koala_konnect_dfu.sh"
  exit 0
fi

echo "Flashing Koala Konnect over serial DFU port: $DFU_PORT"
nrfutil dfu usb-serial -pkg "$PACKAGE" -p "$DFU_PORT"

echo "Koala Konnect DFU complete. Replug the dongle into the phone/computer USB host port."
