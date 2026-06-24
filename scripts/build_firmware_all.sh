#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

STRICT_TOOLS="${STRICT_TOOLS:-0}"
BUILT_ANY=0

python3 scripts/check_repo_readiness.py

echo "Generating default T114 protocol artifacts..."
bash scripts/build_default_t114_protocol_artifacts.sh
BUILT_ANY=1

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

if [[ "${BUILD_LEGACY_NRF_DONGLE:-0}" == "1" || "${BUILD_LEGACY_NRF_LAB:-0}" == "1" || "${BUILD_KOALA_KONNECT:-0}" == "1" ]]; then
  echo "Checking/preparing west for explicit legacy external nRF52840 builds..."
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
    if [[ "${BUILD_LEGACY_NRF_DONGLE:-0}" == "1" ]]; then
      echo "Building legacy external nRF52840 Dongle observer firmware..."
      bash scripts/build_nrf52840_dongle_ble_primary.sh
      BUILT_ANY=1
    fi
    if [[ "${BUILD_LEGACY_NRF_LAB:-0}" == "1" ]]; then
      echo "Building legacy nRF52840 Dongle KoalaByte Lab firmware..."
      bash scripts/build_nrf52840_dongle_lab.sh
      BUILT_ANY=1
    fi
    if [[ "${BUILD_KOALA_KONNECT:-0}" == "1" ]]; then
      echo "Building optional Koala Konnect adapter firmware..."
      bash scripts/build_nrf52840_dongle_hci_usb_adapter.sh
      BUILT_ANY=1
    fi
  else
    echo "Skipping legacy nRF52840 Zephyr builds: west not found." >&2
    if [[ "${STRICT_TOOLS}" == "1" ]]; then
      exit 1
    fi
  fi
else
  echo "Skipping legacy external nRF52840 builds. Set BUILD_LEGACY_NRF_DONGLE=1, BUILD_LEGACY_NRF_LAB=1, or BUILD_KOALA_KONNECT=1 to build them."
fi

if [[ "${BUILT_ANY}" == "0" ]]; then
  echo "No firmware artifacts were generated and no firmware was built." >&2
  exit 1
fi

echo "Firmware build helper complete."
