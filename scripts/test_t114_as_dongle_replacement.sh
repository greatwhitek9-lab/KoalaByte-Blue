#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_ONLY=1
FLASH_T114=0
TEST_ESP32=1
TEST_CAN=1
TEST_SMOKE=1
TEST_PI_INSTALL=0

usage() {
  cat <<'EOF'
KoalaByte Blue T114 in-place firmware test helper

Purpose:
  Test the whole KoalaByte Blue firmware stack with the Heltec Mesh Node T114 V2
  acting as the opt-in nRF52840 target for this test run, while leaving the
  Nordic nRF52840 Dongle production path untouched.

Usage:
  T114_BOARD=<confirmed_zephyr_board_target> bash scripts/test_t114_as_dongle_replacement.sh --build-only
  T114_BOARD=<confirmed_zephyr_board_target> T114_FLASH_CMD='<confirmed flash command>' bash scripts/test_t114_as_dongle_replacement.sh --flash-t114

Options:
  --build-only       Build/test only. Default.
  --flash-t114       Build and flash the T114 using T114_FLASH_CMD.
  --pi-install       Also run scripts/install_pi.sh.
  --skip-esp32       Skip ESP32-S3 DualEye build.
  --skip-can         Skip Koala Kan Kommander manifest check.
  --skip-smoke       Skip safe Pi companion smoke checks.
  -h, --help         Show this help.

Required for T114 build:
  T114_BOARD          Confirmed Zephyr/NCS board target for the Heltec Mesh Node T114 V2.

Required for T114 flash:
  T114_FLASH_CMD      Confirmed bootloader/vendor flash command. This script does not guess.
  T114_PORT           Optional serial/DFU port used by T114_FLASH_CMD if it references {PORT}.

This script never flashes the Nordic nRF52840 Dongle path.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build-only)
      BUILD_ONLY=1
      FLASH_T114=0
      ;;
    --flash-t114)
      BUILD_ONLY=0
      FLASH_T114=1
      ;;
    --pi-install)
      TEST_PI_INSTALL=1
      ;;
    --skip-esp32)
      TEST_ESP32=0
      ;;
    --skip-can)
      TEST_CAN=0
      ;;
    --skip-smoke)
      TEST_SMOKE=0
      ;;
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

if [[ -z "${T114_BOARD:-}" ]]; then
  cat >&2 <<'EOF'
T114_BOARD is required for this test.

Confirm the exact Zephyr/NCS board target for the Heltec Mesh Node T114 V2, then run:

  T114_BOARD=<confirmed_zephyr_board_target> bash scripts/test_t114_as_dongle_replacement.sh --build-only
EOF
  exit 2
fi

if [[ "${FLASH_T114}" == "1" && -z "${T114_FLASH_CMD:-}" ]]; then
  cat >&2 <<'EOF'
--flash-t114 requires T114_FLASH_CMD.

This script will not guess the T114 bootloader or flash method.
Example shape after verification:

  T114_BOARD=<confirmed_zephyr_board_target> \
  T114_PORT=/dev/ttyACM0 \
  T114_FLASH_CMD='<confirmed flash command>' \
  bash scripts/test_t114_as_dongle_replacement.sh --flash-t114
EOF
  exit 2
fi

echo "== KoalaByte Blue T114 in-place firmware test =="
echo "Repository root: ${REPO_ROOT}"
echo "T114_BOARD=${T114_BOARD}"
echo "Build only: ${BUILD_ONLY}"
echo "Flash T114: ${FLASH_T114}"
echo "ESP32 test: ${TEST_ESP32}"
echo "CAN manifest test: ${TEST_CAN}"
echo "Smoke tests: ${TEST_SMOKE}"
echo

echo "== 1/6 Repo readiness =="
python3 scripts/check_repo_readiness.py

echo
 echo "== 2/6 Python compile check =="
python3 -m compileall pi-companion scripts

if [[ "${TEST_PI_INSTALL}" == "1" ]]; then
  echo
  echo "== Optional Pi companion install =="
  bash scripts/install_pi.sh
fi

if [[ "${TEST_ESP32}" == "1" ]]; then
  echo
  echo "== 3/6 ESP32-S3 DualEye build check =="
  if command -v pio >/dev/null 2>&1; then
    pio run -d firmware/esp32-dualeye
  else
    echo "PlatformIO is not installed; preparing/checking ESP32 tools..."
    STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS:-1}" bash scripts/setup_esp32_tools.sh
    pio run -d firmware/esp32-dualeye
  fi
else
  echo
  echo "== 3/6 ESP32-S3 DualEye build check skipped =="
fi

echo
 echo "== 4/6 T114 alternate nRF52840 KoalaByte Lab build =="
bash scripts/build_nrf52840_t114_lab.sh

if [[ "${FLASH_T114}" == "1" ]]; then
  echo
  echo "== T114 alternate nRF52840 flash =="
  bash scripts/flash_nrf52840_t114_lab.sh
else
  echo
  echo "Build-only mode: T114 flash skipped."
fi

if [[ "${TEST_CAN}" == "1" ]]; then
  echo
  echo "== 5/6 Koala Kan Kommander manifest check =="
  PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
else
  echo
  echo "== 5/6 Koala Kan Kommander manifest check skipped =="
fi

if [[ "${TEST_SMOKE}" == "1" ]]; then
  echo
  echo "== 6/6 Safe Pi companion smoke checks =="
  PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py manifest
  PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py status --xp 100
  PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py status
  PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py manifest
  PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py status
else
  echo
  echo "== 6/6 Safe Pi companion smoke checks skipped =="
fi

echo
echo "T114 in-place firmware test complete."
echo "Nordic nRF52840 Dongle production path was not flashed."
echo "Validate on hardware next: USB enumeration, KoalaByte Lab BLE advertisement, button/menu behavior, and any board-specific overlay needs."
