#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${T114_HCI_BUILD_DIR:-build/nrf52840-t114-hci-usb}"
BOARD="${T114_BOARD:-heltec_t114_v2/nrf52840/uf2}"
STATUS_PATH="${T114_HCI_STATUS_PATH:-logs/t114_hci_usb_mode.json}"
UF2_FAMILY="${T114_UF2_FAMILY:-0x239a0071}"
FLASH_LOAD_OFFSET="${T114_FLASH_LOAD_OFFSET:-0x1000}"
FLASH_LOAD_SIZE="${T114_FLASH_LOAD_SIZE:-0xdf000}"
RELEASE_UF2="${T114_RELEASE_UF2:-releases/koalabyte-blue-t114-hci-usb-HT-n5262-offset1000.uf2}"
STRICT="${STRICT_T114_HCI_BUILD:-0}"

# Prefer an explicit Zephyr path, then the user's known standalone Zephyr workspace,
# then the nRF Connect SDK-style default used by older KoalaByte Blue scripts.
if [[ -n "${ZEPHYR_BASE:-}" ]]; then
  :
elif [[ -d "${HOME}/ble-dongle-build/zephyrproject/zephyr" ]]; then
  ZEPHYR_BASE="${HOME}/ble-dongle-build/zephyrproject/zephyr"
else
  ZEPHYR_BASE="${NCS_WORKSPACE:-${HOME}/ncs}/zephyr"
fi

SAMPLE_DIR="${T114_HCI_SAMPLE_DIR:-${ZEPHYR_BASE}/samples/bluetooth/hci_usb}"
WEST_BIN="${WEST:-}"
if [[ -z "${WEST_BIN}" ]]; then
  if [[ -x "${HOME}/ble-dongle-build/.venv/bin/west" ]]; then
    WEST_BIN="${HOME}/ble-dongle-build/.venv/bin/west"
  else
    WEST_BIN="west"
  fi
fi

mkdir -p "$(dirname "${STATUS_PATH}")" "$(dirname "${RELEASE_UF2}")"

json_escape() {
  python3 - <<'PY' "$1"
import json, sys
print(json.dumps(sys.argv[1]))
PY
}

write_status() {
  local status="$1"
  local reason="$2"
  cat > "${STATUS_PATH}" <<JSON
{
  "status": $(json_escape "${status}"),
  "reason": $(json_escape "${reason}"),
  "mode": "t114_koala_konnect",
  "hci_profile": "t114_hci_usb",
  "product_mode": "Koala Konnect",
  "external_bluetooth_adapter": true,
  "board": $(json_escape "${BOARD}"),
  "build_dir": $(json_escape "${BUILD_DIR}"),
  "sample_dir": $(json_escape "${SAMPLE_DIR}"),
  "release_uf2": $(json_escape "${RELEASE_UF2}"),
  "uf2_family": $(json_escape "${UF2_FAMILY}"),
  "flash_load_offset": $(json_escape "${FLASH_LOAD_OFFSET}"),
  "flash_load_size": $(json_escape "${FLASH_LOAD_SIZE}"),
  "host_role": "USB Bluetooth HCI controller for BlueZ and compatible host Bluetooth stacks",
  "antenna_status_path": "logs/t114_2g4_antenna_status.json",
  "updated_at": $(date +%s)
}
JSON
}

fail_or_soft_exit() {
  local status="$1"
  local reason="$2"
  write_status "${status}" "${reason}"
  if [[ "${STRICT}" == "1" ]]; then
    echo "${reason}" >&2
    exit 1
  fi
  echo "${reason}; wrote ${STATUS_PATH}" >&2
  exit 0
}

bash scripts/configure_t114_2g4_antenna.sh --check-only

if ! command -v "${WEST_BIN}" >/dev/null 2>&1 && [[ ! -x "${WEST_BIN}" ]]; then
  fail_or_soft_exit "missing_west" "west is not installed or WEST does not point to an executable. Run scripts/setup_heltec_t114_tools.sh with INSTALL_HELTEC_NRF_TOOLS=1, install Zephyr/west, or set WEST=/path/to/west."
fi

if [[ ! -d "${SAMPLE_DIR}" ]]; then
  fail_or_soft_exit "missing_sample" "Zephyr hci_usb sample directory was not found at ${SAMPLE_DIR}. Set ZEPHYR_BASE or T114_HCI_SAMPLE_DIR."
fi

CMAKE_ARGS=(
  -DCONFIG_USE_DT_CODE_PARTITION=n
  -DCONFIG_FLASH_LOAD_OFFSET="${FLASH_LOAD_OFFSET}"
  -DCONFIG_FLASH_LOAD_SIZE="${FLASH_LOAD_SIZE}"
)

if overlay="$(bash scripts/configure_t114_2g4_antenna.sh --print-export)" && [[ -n "${overlay}" ]]; then
  CMAKE_ARGS+=(-DDTC_OVERLAY_FILE="${overlay}")
fi

echo "Building T114 HCI USB firmware for KoalaByte Blue"
echo "  board:        ${BOARD}"
echo "  zephyr:       ${ZEPHYR_BASE}"
echo "  sample:       ${SAMPLE_DIR}"
echo "  west:         ${WEST_BIN}"
echo "  build dir:    ${BUILD_DIR}"
echo "  output UF2:   ${RELEASE_UF2}"
echo "  app offset:   ${FLASH_LOAD_OFFSET}"
echo "  app size:     ${FLASH_LOAD_SIZE}"
echo "  UF2 family:   ${UF2_FAMILY}"

"${WEST_BIN}" build -p always \
  -b "${BOARD}" \
  "${SAMPLE_DIR}" \
  -d "${BUILD_DIR}" \
  -- "${CMAKE_ARGS[@]}"

RAW_UF2="${BUILD_DIR}/zephyr/zephyr.uf2"
if [[ ! -f "${RAW_UF2}" ]]; then
  fail_or_soft_exit "missing_raw_uf2" "Build completed but raw UF2 was not found at ${RAW_UF2}."
fi

echo "Raw UF2 metadata:"
python3 scripts/inspect_uf2.py "${RAW_UF2}"

echo "Patching UF2 family for HT-n5262 bootloader..."
python3 scripts/patch_uf2_family.py "${RAW_UF2}" "${RELEASE_UF2}" "${UF2_FAMILY}"

echo "Patched UF2 metadata:"
python3 scripts/inspect_uf2.py "${RELEASE_UF2}"

write_status "built" "T114 HCI USB firmware build completed with HT-n5262 offset/family UF2 fix."
echo "T114 HCI USB build complete: ${RELEASE_UF2}"
