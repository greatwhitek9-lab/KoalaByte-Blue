#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${T114_HCI_BUILD_DIR:-build/nrf52840-t114-hci-usb}"
BOARD="${T114_BOARD:-heltec_t114_v2/nrf52840}"
STATUS_PATH="${T114_HCI_STATUS_PATH:-logs/t114_hci_usb_mode.json}"
ZEPHYR_BASE="${ZEPHYR_BASE:-${NCS_WORKSPACE:-${HOME}/ncs}/zephyr}"
SAMPLE_DIR="${T114_HCI_SAMPLE_DIR:-${ZEPHYR_BASE}/samples/bluetooth/hci_usb}"
STRICT="${STRICT_T114_HCI_BUILD:-0}"

mkdir -p "$(dirname "${STATUS_PATH}")"

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
  "host_role": "USB Bluetooth HCI controller for BlueZ and compatible host Bluetooth stacks",
  "antenna_status_path": "logs/t114_2g4_antenna_status.json",
  "updated_at": $(date +%s)
}
JSON
}

bash scripts/configure_t114_2g4_antenna.sh --check-only

if ! command -v west >/dev/null 2>&1; then
  write_status "missing_west" "west is not installed; run scripts/setup_heltec_t114_tools.sh with INSTALL_HELTEC_NRF_TOOLS=1 or install the nRF Connect SDK."
  if [[ "${STRICT}" == "1" ]]; then
    exit 1
  fi
  echo "west not found; wrote ${STATUS_PATH}" >&2
  exit 0
fi

if [[ ! -d "${SAMPLE_DIR}" ]]; then
  write_status "missing_sample" "Zephyr hci_usb sample directory was not found."
  if [[ "${STRICT}" == "1" ]]; then
    exit 1
  fi
  echo "Zephyr hci_usb sample not found; wrote ${STATUS_PATH}" >&2
  exit 0
fi

EXTRA_ARGS=()
if overlay="$(bash scripts/configure_t114_2g4_antenna.sh --print-export)" && [[ -n "${overlay}" ]]; then
  EXTRA_ARGS+=(-- -DDTC_OVERLAY_FILE="${overlay}")
fi

west build -b "${BOARD}" "${SAMPLE_DIR}" -d "${BUILD_DIR}" "${EXTRA_ARGS[@]}"
write_status "built" "T114 HCI USB firmware build completed."
echo "T114 HCI USB build complete: ${BUILD_DIR}"
