#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${BUILD_DIR:-build/nrf52840-t114-lab}"
HEX="${HEX:-${BUILD_DIR}/zephyr/zephyr.hex}"
BIN="${BIN:-${BUILD_DIR}/zephyr/zephyr.bin}"
UF2="${UF2:-${BUILD_DIR}/zephyr/zephyr.uf2}"
T114_PORT="${T114_PORT:-}"
T114_FLASH_CMD="${T114_FLASH_CMD:-}"

if [[ ! -f "${HEX}" && ! -f "${BIN}" && ! -f "${UF2}" ]]; then
  echo "Missing T114 KoalaByte Lab firmware artifacts under ${BUILD_DIR}/zephyr/." >&2
  echo "Build first:" >&2
  echo "  T114_BOARD=<confirmed_zephyr_board_target> bash scripts/build_nrf52840_t114_lab.sh" >&2
  exit 1
fi

if [[ -z "${T114_FLASH_CMD}" ]]; then
  cat >&2 <<EOF
T114_FLASH_CMD is not set, so this helper will not guess the board's bootloader/flash method.

Built artifact candidates:
  HEX: ${HEX}
  BIN: ${BIN}
  UF2: ${UF2}

Set a confirmed flash command after validating the exact T114 bootloader. Placeholders are supported:
  {HEX}       -> ${HEX}
  {BIN}       -> ${BIN}
  {UF2}       -> ${UF2}
  {PORT}      -> ${T114_PORT}
  {BUILD_DIR} -> ${BUILD_DIR}

Examples after verification only:
  T114_FLASH_CMD='west flash -d {BUILD_DIR}' bash scripts/flash_nrf52840_t114_lab.sh
  T114_PORT=/dev/ttyACM0 T114_FLASH_CMD='<vendor flash command using {PORT} and {HEX}>' bash scripts/flash_nrf52840_t114_lab.sh

The Nordic nRF52840 Dongle DFU path remains unchanged:
  NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_nrf52840_dongle_lab_dfu.sh
EOF
  exit 2
fi

cmd="${T114_FLASH_CMD}"
cmd="${cmd//\{HEX\}/${HEX}}"
cmd="${cmd//\{BIN\}/${BIN}}"
cmd="${cmd//\{UF2\}/${UF2}}"
cmd="${cmd//\{PORT\}/${T114_PORT}}"
cmd="${cmd//\{BUILD_DIR\}/${BUILD_DIR}}"

echo "Flashing alternate Heltec Mesh Node T114 V2 KoalaByte Lab target with confirmed command:"
echo "  ${cmd}"
eval "${cmd}"

echo "T114 alternate target flash command complete. Verify USB enumeration and KoalaByte Lab BLE behavior before treating it as a dongle replacement."
