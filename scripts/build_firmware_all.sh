#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

STRICT_TOOLS="${STRICT_TOOLS:-0}"
BUILT_ANY=0

python3 scripts/check_repo_readiness.py

echo "Checking/installing system package dependencies when available..."
STRICT_SYSTEM_PACKAGES="${STRICT_TOOLS}" bash scripts/setup_system_packages.sh || {
  if [[ "${STRICT_TOOLS}" == "1" ]]; then
    exit 1
  fi
}

echo "Checking/preparing PlatformIO for ESP32 build..."
if ! STRICT_ESP32_TOOLS="${STRICT_TOOLS}" bash scripts/setup_esp32_tools.sh; then
  echo "PlatformIO setup/check failed." >&2
  if [[ "${STRICT_TOOLS}" == "1" ]]; then
    exit 1
  fi
fi

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

echo "Checking/preparing west for nRF52840 Zephyr builds..."
if ! STRICT_NRF_TOOLS="${STRICT_TOOLS}" bash scripts/setup_nrf_tools.sh --west-only; then
  echo "west setup/check failed." >&2
  if [[ "${STRICT_TOOLS}" == "1" ]]; then
    exit 1
  fi
fi

echo "Checking/preparing full nRF Connect SDK / Zephyr toolchain..."
if ! STRICT_NCS_TOOLCHAIN="${STRICT_TOOLS}" bash scripts/setup_nrf_connect_sdk_toolchain.sh; then
  echo "Full NCS/Zephyr toolchain setup/check failed." >&2
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
  if [[ "${BUILD_T114_LAB:-0}" == "1" ]]; then
    echo "Building optional Heltec Mesh Node T114 V2 alternate nRF52840 KoalaByte Lab target..."
    bash scripts/build_nrf52840_t114_lab.sh
  else
    echo "Skipping optional T114 alternate target build. Set BUILD_T114_LAB=1 and T114_BOARD=<confirmed target> to build it."
  fi
else
  echo "Skipping nRF52840 Zephyr builds: west not found." >&2
  if [[ "${STRICT_TOOLS}" == "1" ]]; then
    exit 1
  fi
fi

if [[ "${BUILT_ANY}" == "0" ]]; then
  echo "No firmware was built because PlatformIO and west were not found." >&2
  echo "Install PlatformIO for ESP32 and use scripts/setup_nrf_tools.sh plus scripts/setup_nrf_connect_sdk_toolchain.sh for nRF/Zephyr." >&2
  exit 1
fi

echo "Firmware build helper complete."
