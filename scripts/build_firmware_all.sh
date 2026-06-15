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
  echo "Building nRF52840 DK Zephyr firmware..."
  bash scripts/build_nrf52840_dk_lab.sh
else
  echo "Skipping nRF52840 Zephyr build: west not found." >&2
fi

echo "Firmware build helper complete. Install PlatformIO and nRF Connect SDK to build both targets."
