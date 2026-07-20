#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${T114_COMBINED_BUILD_DIR:-build/t114-combined-safe}"
BOARD="${T114_BOARD:-heltec_t114_v2/nrf52840/uf2}"
BOARD_ROOT="${T114_BOARD_ROOT:-${REPO_ROOT}}"
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
  "board_root": $(json_escape "${BOARD_ROOT}"),
  "app_dir": $(json_escape "${APP_DIR}"),
  "build_dir": $(json_escape "${BUILD_DIR}"),
  "primary_ble": "heltec-t114-nrf52840",
  "primary_gnss": "heltec-t114-gnss",
  "gnss_uart_label": $(json_escape "${T114_GNSS_UART_LABEL}"),
  "secondary_ble_nodes": [
    "esp32-s3-dualeye",
    "raspberry-pi-bluez"
  ],
  "safety": "BLE RX/TX and GNSS can run together; LoRa driver guarded until pin validation.",
  "updated_at": $(date +%s)
}
JSON
}

bash scripts/configure_t114_2g4_antenna.sh --check-only || true
bash scripts/configure_t114_lora_external_antenna.sh --check-only || true

if ! command -v west >/dev/null 2>&1; then
    write_status "missing_west" "west is not installed."

    if [[ "${STRICT}" == "1" ]]; then
        exit 1
    fi

    echo "west not installed."
    exit 0
fi

if [[ ! -d "${APP_DIR}" ]]; then
    write_status "missing_app" "Application directory missing."
    exit 1
fi

echo ""
echo "==============================="
echo "KoalaByte T114 Build"
echo "==============================="
echo "BOARD       = ${BOARD}"
echo "BOARD_ROOT  = ${BOARD_ROOT}"
echo "APP_DIR     = ${APP_DIR}"
echo "BUILD_DIR   = ${BUILD_DIR}"
echo ""

export BOARD_ROOT="${BOARD_ROOT}"

west build --no-sysbuild \
    -p always \
    -b "${BOARD}" \
    "${APP_DIR}" \
    -d "${BUILD_DIR}" \
    -- \
    -DBOARD_ROOT="${BOARD_ROOT}" \
    -DKOALABYTE_GNSS_UART_LABEL="${T114_GNSS_UART_LABEL}"

ELF_PATH="${BUILD_DIR}/zephyr/zephyr.elf"
if [[ ! -f "${ELF_PATH}" ]]; then
    write_status "failed" "T114 ELF is missing after west build."
    exit 1
fi

# Prove the public lifecycle renderer survived archive linking and section GC.
# These state strings are referenced by the live render_killerkoala_mouth path.
for marker in \
    action_complete \
    koalagotchi_mode \
    koalagotchi_exit \
    disappointed \
    angry \
    error_clear \
    REPEATED\ FAILURES; do
    if ! strings "${ELF_PATH}" | grep -Fq "${marker}"; then
        write_status "failed" "T114 lifecycle marker missing from linked ELF: ${marker}"
        echo "Missing linked T114 lifecycle marker: ${marker}" >&2
        exit 1
    fi
done

write_status "built" "T114 combined-safe firmware build completed with linked Koalagotchi lifecycle state machine."

echo ""
echo "======================================"
echo "Build completed successfully."
echo "Lifecycle state machine: linked and verified"
echo "Output directory:"
echo "  ${BUILD_DIR}"
echo "======================================"
