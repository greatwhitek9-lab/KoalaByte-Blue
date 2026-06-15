#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

STRICT_TOOLS="${STRICT_TOOLS:-0}"
BUILT_ANY=0

python3 scripts/check_repo_readiness.py

if command -v pio >/dev/null 2>&1; then
  echo "Building ESP32-S3 DualEye firmware..."
  pio run -d firmware/esp32-dualeye
  BUILT_ANY=1
else
  echo "Skipping ESP32 build: PlatformIO not found." >&2
  if [[ "${STRICT_TOOLS}" == "1" ]]; then
    exit 1
  fi
fi

if command -v west >/dev/null 2>&1; then
  echo "Building nRF52840 Dongle KoalaByte Lab firmware..."
  bash scripts/build_nrf52840_dongle_lab.sh
  BUILT_ANY=1
  if [[ "${BUILD_KOALA_KONNECT:-0}" == "1" ]]; then
    echo "Building optional Koala Konnect external Bluetooth adapter firmware..."
    bash scripts/build_nrf52840_dongle_hci_usb_adapter.sh
  else
    echo "Skipping optional Koala Konnect build. Set BUILD_KOALA_KONNECT=1 to build it."
  fi
else
  echo "Skipping nRF52840 Dongle Zephyr builds: west not found." >&2
  if [[ "${STRICT_TOOLS}" == "1" ]]; then
    exit 1
  fi
fi

if [[ "${BUILT_ANY}" == "0" ]]; then
  echo "No firmware was built because PlatformIO and west were not found." >&2
  echo "Install PlatformIO for ESP32 and nRF Connect SDK/west for the nRF52840 Dongle." >&2
  exit 1
fi

echo "Firmware build helper complete."
