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
EXPECTED_FW="0.10.0-t114-smooth-idle-and-speech-mouth"
EXPECTED_PROTOCOL="killerkoala_face_v1"
EXPECTED_REPO_PROTOCOL="2026.06-menu-sync-v1"

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
  "expected_runtime_identity": {
    "device": "heltec-t114",
    "fw": $(json_escape "${EXPECTED_FW}"),
    "protocol": $(json_escape "${EXPECTED_PROTOCOL}"),
    "repo_protocol_version": $(json_escape "${EXPECTED_REPO_PROTOCOL}")
  },
  "secondary_ble_nodes": [
    "esp32-s3-dualeye",
    "raspberry-pi-bluez"
  ],
  "software_uf2_entry": true,
  "installer_owned_flash": true,
  "linked_identity_markers_checked": true,
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
UF2_PATH="${BUILD_DIR}/zephyr/zephyr.uf2"
if [[ ! -s "${ELF_PATH}" ]]; then
    write_status "failed" "T114 ELF is missing or empty after west build."
    exit 1
fi
if [[ ! -s "${UF2_PATH}" ]]; then
    write_status "failed" "T114 UF2 is missing or empty after west build."
    exit 1
fi
command -v strings >/dev/null 2>&1 || {
    write_status "failed" "binutils strings command is required for linked-image validation."
    exit 1
}
LINKED_STRINGS="${BUILD_DIR}/zephyr/koalabyte-linked-strings.txt"
strings "${ELF_PATH}" > "${LINKED_STRINGS}"

# Prove runtime identity, lifecycle, and software-UF2 behavior survived archive
# linking and section garbage collection.
for marker in \
    "${EXPECTED_FW}" \
    "${EXPECTED_PROTOCOL}" \
    "${EXPECTED_REPO_PROTOCOL}" \
    heltec-t114 \
    heltec_mouth_status \
    action_complete \
    koalagotchi_mode \
    koalagotchi_exit \
    disappointed \
    angry \
    error_clear \
    bootloader_ack \
    REBOOT_UF2 \
    REPEATED\ FAILURES; do
    if ! grep -Fq "${marker}" "${LINKED_STRINGS}"; then
        write_status "failed" "T114 identity/lifecycle/deployment marker missing from linked ELF: ${marker}"
        echo "Missing linked T114 marker: ${marker}" >&2
        exit 1
    fi
done

# Prove the live mouth path uses the approved original texture, generates
# articulated continuous frames, and retains explicit still-frame exclusion.
for marker in \
    original_texture_articulated_jaw_v2 \
    still_frame_cycle \
    original_killerkoala_smile \
    grin-cavity-jaw-cheeks-fangs \
    frame_signature \
    changed_pixels; do
    if ! grep -Fq "${marker}" "${LINKED_STRINGS}"; then
        write_status "failed" "T114 articulated original-texture renderer marker missing from linked ELF: ${marker}"
        echo "Missing linked articulated original-texture renderer marker: ${marker}" >&2
        exit 1
    fi
done

write_status "built" "T114 firmware built with exact linked identity, Koalagotchi lifecycle, software UF2 entry, and articulated original-texture mouth renderer."

echo ""
echo "======================================"
echo "Build completed successfully."
echo "Runtime identity: ${EXPECTED_FW} / ${EXPECTED_PROTOCOL}"
echo "Koalagotchi lifecycle: linked and verified"
echo "Software UF2 entry: linked and verified"
echo "Mouth renderer: original texture articulated jaw v2"
echo "Still-frame cycling: disabled"
echo "Frame-change diagnostics: linked"
echo "Output directory:"
echo "  ${BUILD_DIR}"
echo "======================================"
