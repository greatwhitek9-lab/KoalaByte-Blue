#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${T114_COMBINED_BUILD_DIR:-build/t114-combined-safe}"
BOARD="${T114_BOARD:-heltec_t114_v2/nrf52840}"
APP_DIR="${T114_COMBINED_APP_DIR:-firmware/t114-combined-safe}"
STATUS_PATH="${T114_COMBINED_STATUS_PATH:-logs/t114_combined_safe_build_status.json}"
STRICT="${STRICT_T114_COMBINED_BUILD:-0}"
T114_GNSS_UART_LABEL="${T114_GNSS_UART_LABEL:-UART_1}"

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
  "mode": "t114_combined_safe",
  "profile": "combined-safe",
  "board": $(json_escape "${BOARD}"),
  "app_dir": $(json_escape "${APP_DIR}"),
  "build_dir": $(json_escape "${BUILD_DIR}"),
  "primary_ble": "heltec-t114-nrf52840",
  "primary_gnss": "heltec-t114-gnss",
  "gnss_uart_label": $(json_escape "${T114_GNSS_UART_LABEL}"),
  "secondary_ble_nodes": ["esp32-s3-dualeye", "raspberry-pi-bluez"],
  "safety": "BLE RX/TX and GNSS can run together; LoRa direct radio driver remains guarded until T114 pin validation",
  "updated_at": $(date +%s)
}
JSON
}

bash scripts/configure_t114_2g4_antenna.sh --check-only || true
bash scripts/configure_t114_lora_external_antenna.sh --check-only || true

if ! command -v west >/dev/null 2>&1; then
  write_status "missing_west" "west is not installed; run scripts/setup_heltec_t114_tools.sh with INSTALL_HELTEC_NRF_TOOLS=1 or install the nRF Connect SDK."
  if [[ "${STRICT}" == "1" ]]; then
    exit 1
  fi
  echo "west not found; wrote ${STATUS_PATH}" >&2
  exit 0
fi

if [[ ! -d "${APP_DIR}" ]]; then
  write_status "missing_app" "Combined T114 firmware app directory is missing."
  exit 1
fi

west build -b "${BOARD}" "${APP_DIR}" -d "${BUILD_DIR}" -- -DKOALABYTE_GNSS_UART_LABEL="${T114_GNSS_UART_LABEL}"
write_status "built" "T114 combined-safe firmware build completed."
echo "T114 combined-safe build complete: ${BUILD_DIR}"
