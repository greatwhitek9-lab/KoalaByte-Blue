#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${BUILD_DIR:-build/nrf52840-t114-hci-usb}"
T114_BOARD="${T114_BOARD:-}"
HCI_USB_SAMPLE_DIR="${HCI_USB_SAMPLE_DIR:-}"
T114_2G4_ANTENNA="${T114_2G4_ANTENNA:-connector}"
KOALA_KONNECT_MODE_NAME="${KOALA_KONNECT_MODE_NAME:-t114_koala_konnect}"

STRICT_NRF_TOOLS="${STRICT_NRF_TOOLS:-1}" bash scripts/setup_nrf_tools.sh --include-nfcutil
if [[ -f "scripts/setup_nrf_connect_sdk_toolchain.sh" ]]; then
  STRICT_NCS_TOOLCHAIN="${STRICT_NCS_TOOLCHAIN:-1}" bash scripts/setup_nrf_connect_sdk_toolchain.sh --check-only || true
fi
if [[ -f "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh" ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh"
fi

if [[ -z "${T114_BOARD}" ]]; then
  T114_BOARD="$(bash scripts/confirm_t114_board_target.sh | awk -F': ' '/Confirmed T114 Zephyr board target/ {print $2}' | tail -n 1)"
fi

if [[ -z "${T114_BOARD}" ]]; then
  echo "Unable to resolve T114_BOARD." >&2
  exit 2
fi

if [[ -z "${HCI_USB_SAMPLE_DIR}" ]]; then
  if [[ -n "${ZEPHYR_BASE:-}" && -d "${ZEPHYR_BASE}/samples/bluetooth/hci_usb" ]]; then
    HCI_USB_SAMPLE_DIR="${ZEPHYR_BASE}/samples/bluetooth/hci_usb"
  elif [[ -n "${NCS_WORKSPACE:-}" && -d "${NCS_WORKSPACE}/zephyr/samples/bluetooth/hci_usb" ]]; then
    HCI_USB_SAMPLE_DIR="${NCS_WORKSPACE}/zephyr/samples/bluetooth/hci_usb"
  fi
fi

if [[ -z "${HCI_USB_SAMPLE_DIR}" || ! -f "${HCI_USB_SAMPLE_DIR}/CMakeLists.txt" ]]; then
  cat >&2 <<'EOF'
Could not find Zephyr's samples/bluetooth/hci_usb application.

Confirm Zephyr/NCS is installed and sourced, or set:

  HCI_USB_SAMPLE_DIR=/path/to/zephyr/samples/bluetooth/hci_usb
EOF
  exit 2
fi

mkdir -p logs
ANTENNA_OVERLAY="$(T114_2G4_ANTENNA="${T114_2G4_ANTENNA}" bash scripts/configure_t114_2g4_antenna.sh --print-export | tail -n 1)"

cat > logs/t114_hci_usb_mode.json <<JSON
{
  "mode": "${KOALA_KONNECT_MODE_NAME}",
  "hci_profile": "t114_hci_usb",
  "product_mode": "Koala Konnect",
  "external_bluetooth_adapter": true,
  "board": "${T114_BOARD}",
  "build_dir": "${BUILD_DIR}",
  "sample_dir": "${HCI_USB_SAMPLE_DIR}",
  "host_role": "USB Bluetooth HCI controller for BlueZ and compatible host Bluetooth stacks",
  "t114_2g4_antenna": "${T114_2G4_ANTENNA}",
  "antenna_status_path": "logs/t114_2g4_antenna_status.json",
  "antenna_overlay": "${ANTENNA_OVERLAY}"
}
JSON

echo "Building Heltec T114 Koala Konnect USB Bluetooth adapter firmware"
echo "Board: ${T114_BOARD}"
echo "Sample: ${HCI_USB_SAMPLE_DIR}"
echo "Build dir: ${BUILD_DIR}"
if [[ -n "${ANTENNA_OVERLAY}" ]]; then
  west build -b "${T114_BOARD}" "${HCI_USB_SAMPLE_DIR}" -d "${BUILD_DIR}" -- -DEXTRA_DTC_OVERLAY_FILE="${ANTENNA_OVERLAY}"
else
  west build -b "${T114_BOARD}" "${HCI_USB_SAMPLE_DIR}" -d "${BUILD_DIR}"
fi

echo "T114 Koala Konnect firmware build complete: ${BUILD_DIR}"
echo "After flashing and replugging, supported hosts should expose the board as a USB Bluetooth HCI adapter."
