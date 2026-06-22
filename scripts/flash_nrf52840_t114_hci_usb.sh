#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${BUILD_DIR:-build/nrf52840-t114-hci-usb}"
UF2="${UF2:-${BUILD_DIR}/zephyr/zephyr.uf2}"
HEX="${HEX:-${BUILD_DIR}/zephyr/zephyr.hex}"
T114_PORT="${T114_PORT:-}"
T114_FLASH_METHOD="${T114_FLASH_METHOD:-west}"
KOALA_KONNECT_MODE_NAME="${KOALA_KONNECT_MODE_NAME:-t114_koala_konnect}"
KOALA_KONNECT_HOST_EXPECTATION="${KOALA_KONNECT_HOST_EXPECTATION:-After replugging, supported computers or USB-OTG-capable phones can use the Heltec board as an external Bluetooth HCI adapter. Host driver support is required.}"

if [[ ! -f "${HEX}" && ! -f "${UF2}" ]]; then
  echo "Missing T114 Koala Konnect / HCI USB firmware artifacts under ${BUILD_DIR}/zephyr/." >&2
  echo "Build first:" >&2
  echo "  T114_BOARD=<confirmed_zephyr_board_target> bash scripts/build_koala_konnect_t114.sh" >&2
  exit 1
fi

case "${T114_FLASH_METHOD}" in
  west)
    if ! command -v west >/dev/null 2>&1; then
      echo "west was not found. Run scripts/setup_nrf_tools.sh --west-only first." >&2
      exit 2
    fi
    echo "Flashing T114 Koala Konnect USB Bluetooth adapter firmware with west flash."
    west flash -d "${BUILD_DIR}"
    ;;
  uf2)
    if [[ -z "${T114_PORT}" || ! -d "${T114_PORT}" || ! -f "${UF2}" ]]; then
      echo "UF2 flashing requires T114_PORT=<mounted bootloader path> and ${UF2}." >&2
      exit 2
    fi
    echo "Copying T114 Koala Konnect UF2 to mounted bootloader path: ${T114_PORT}"
    cp "${UF2}" "${T114_PORT}/"
    sync
    ;;
  *)
    echo "Unknown T114_FLASH_METHOD=${T114_FLASH_METHOD}. Use west or uf2." >&2
    exit 2
    ;;
esac

mkdir -p logs
cat > logs/t114_active_ble_mode.json <<JSON
{
  "mode": "${KOALA_KONNECT_MODE_NAME}",
  "hci_profile": "t114_hci_usb",
  "product_mode": "Koala Konnect",
  "build_dir": "${BUILD_DIR}",
  "flash_method": "${T114_FLASH_METHOD}",
  "port": "${T114_PORT}",
  "external_bluetooth_adapter": true,
  "host_expectation": "${KOALA_KONNECT_HOST_EXPECTATION}",
  "verify_linux": "bluetoothctl list && bluetoothctl show && bluetoothctl --timeout 15 scan on",
  "phone_note": "Phone support depends on USB OTG power/data support and the phone OS exposing USB Bluetooth HCI adapters."
}
JSON

echo "T114 Koala Konnect flash complete. Replug the board, then verify with: bluetoothctl list && bluetoothctl show && bluetoothctl --timeout 15 scan on"
