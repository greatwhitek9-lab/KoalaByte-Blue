#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

RUN_PI=0
RUN_ESP32=0
RUN_NRF_LAB=0
RUN_NRF_KONNECT=0
RUN_CAN_CHECK=0
BUILD_ONLY=0
CHECK_ONLY=0
RUN_SMOKE=0
NO_MONITOR_DEFAULT=1

usage() {
  cat <<'EOF'
KoalaByte Blue all-component flash/install helper

Usage:
  bash scripts/flash_all_components.sh --all
  bash scripts/flash_all_components.sh --pi --esp32 --nrf-lab
  NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --nrf-lab
  ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32

Targets:
  --all            Install Pi companion, flash ESP32, build/package/flash nRF52840 KoalaByte Lab, and run CAN manifest check
  --pi             Install/update Raspberry Pi companion environment
  --esp32          Build and flash ESP32-S3 DualEye firmware with PlatformIO
  --nrf-lab        Build/package/flash nRF52840 Dongle KoalaByte Lab firmware
  --nrf-konnect    Build/package/flash optional Koala Konnect USB HCI profile instead of KoalaByte Lab
  --can-check      Write Koala Kan Kommander InnoMaker manifest artifact; no CAN traffic is sent

Modes:
  --build-only     Build/package only; do not upload/flash firmware
  --check-only     Run repo readiness check only
  --smoke          After selected actions, run safe local Pi companion smoke checks
  --monitor        Open ESP32 serial monitor after flash
  -h, --help       Show this help

Environment:
  ESP32_PORT       Optional PlatformIO upload/monitor port, for example /dev/ttyUSB0 or COM5
  NRF_DFU_PORT    Optional nRF52840 Dongle bootloader serial port, for example /dev/ttyACM0 or COM7
  BUILD_KOALA_KONNECT=1 can still be used with scripts/build_firmware_all.sh for optional HCI builds.

Notes:
  - The nRF52840 Dongle can run KoalaByte Lab or Koala Konnect, not both at the same time.
  - If NRF_DFU_PORT is unset, the nRF helper creates the DFU ZIP but does not flash.
  - Koala Kan Kommander remains passive by default; this script only writes a manifest/check artifact.
EOF
}

if [[ $# -eq 0 ]]; then
  usage
  exit 0
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)
      RUN_PI=1
      RUN_ESP32=1
      RUN_NRF_LAB=1
      RUN_CAN_CHECK=1
      ;;
    --pi) RUN_PI=1 ;;
    --esp32) RUN_ESP32=1 ;;
    --nrf-lab) RUN_NRF_LAB=1 ;;
    --nrf-konnect) RUN_NRF_KONNECT=1 ;;
    --can-check) RUN_CAN_CHECK=1 ;;
    --build-only) BUILD_ONLY=1 ;;
    --check-only) CHECK_ONLY=1 ;;
    --smoke) RUN_SMOKE=1 ;;
    --monitor) NO_MONITOR_DEFAULT=0 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [[ "${RUN_NRF_LAB}" == "1" && "${RUN_NRF_KONNECT}" == "1" && "${BUILD_ONLY}" != "1" ]]; then
  echo "Refusing to flash both nRF profiles in one run. The dongle can hold only one active profile." >&2
  echo "Run one of: --nrf-lab or --nrf-konnect. Use --build-only if you only want to build/package both." >&2
  exit 2
fi

echo "== KoalaByte Blue readiness check =="
python3 scripts/check_repo_readiness.py

if [[ "${CHECK_ONLY}" == "1" ]]; then
  echo "Check-only mode complete."
  exit 0
fi

if [[ "${RUN_PI}" == "1" ]]; then
  echo
  echo "== Installing/updating Raspberry Pi companion =="
  bash scripts/install_pi.sh
fi

if [[ "${RUN_ESP32}" == "1" ]]; then
  echo
  echo "== ESP32-S3 DualEye firmware =="
  if [[ "${BUILD_ONLY}" == "1" ]]; then
    if ! command -v pio >/dev/null 2>&1; then
      echo "PlatformIO is required for ESP32 build-only mode." >&2
      exit 1
    fi
    pio run -d firmware/esp32-dualeye
  else
    if [[ "${NO_MONITOR_DEFAULT}" == "1" ]]; then
      NO_MONITOR=1 bash scripts/flash_esp32.sh
    else
      NO_MONITOR=0 bash scripts/flash_esp32.sh
    fi
  fi
fi

if [[ "${RUN_NRF_LAB}" == "1" ]]; then
  echo
  echo "== nRF52840 Dongle KoalaByte Lab firmware =="
  bash scripts/build_nrf52840_dongle_lab.sh
  if [[ "${BUILD_ONLY}" != "1" ]]; then
    bash scripts/flash_nrf52840_dongle_lab_dfu.sh
  else
    echo "Build-only mode: skipping KoalaByte Lab DFU package/flash step."
  fi
fi

if [[ "${RUN_NRF_KONNECT}" == "1" ]]; then
  echo
  echo "== nRF52840 Dongle Koala Konnect firmware =="
  bash scripts/build_koala_konnect.sh
  if [[ "${BUILD_ONLY}" != "1" ]]; then
    bash scripts/flash_koala_konnect.sh
  else
    echo "Build-only mode: skipping Koala Konnect DFU package/flash step."
  fi
fi

if [[ "${RUN_CAN_CHECK}" == "1" ]]; then
  echo
  echo "== Koala Kan Kommander InnoMaker CAN manifest check =="
  PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
fi

if [[ "${RUN_SMOKE}" == "1" ]]; then
  echo
  echo "== Safe local smoke checks =="
  PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py manifest
  PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py inventory
  PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py status --xp 100
  PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
fi

echo
echo "KoalaByte Blue flash/install helper complete."
