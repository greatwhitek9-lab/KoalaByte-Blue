#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

if command -v pio >/dev/null 2>&1; then
  echo "Building ESP32-S3 DualEye firmware..."
  pio run -d firmware/esp32-dualeye
else
  echo "Skipping ESP32 build: PlatformIO not found." >&2
fi

if command -v west >/dev/null 2>&1; then
  echo "Building nRF52840 Dongle KoalaByte Lab firmware..."
  bash scripts/build_nrf52840_dongle_lab.sh
  if [[ "${BUILD_KOALA_KONNECT:-0}" == "1" ]]; then
    echo "Building optional Koala Konnect external Bluetooth adapter firmware..."
    bash scripts/build_nrf52840_dongle_hci_usb_adapter.sh
  else
    echo "Skipping optional Koala Konnect build. Set BUILD_KOALA_KONNECT=1 to build it."
  fi
else
  echo "Skipping nRF52840 Dongle Zephyr builds: west not found." >&2
fi

echo "Firmware build helper complete. Install PlatformIO and nRF Connect SDK to build all retained targets."
