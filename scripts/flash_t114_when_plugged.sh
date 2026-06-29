#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

PROFILE="${T114_PLUG_FLASH_PROFILE:-combined-safe}"
TIMEOUT_SECONDS="${T114_PLUG_FLASH_TIMEOUT_SECONDS:-120}"
POLL_SECONDS="${T114_PLUG_FLASH_POLL_SECONDS:-2}"
PORT="${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-${HELTEC_PORT:-}}}"
STATUS_PATH="${T114_PLUG_FLASH_STATUS_PATH:-logs/t114_plug_flash_status.json}"
UF2_VOLUME_NAME="${T114_UF2_VOLUME_NAME:-HT-n5262}"
CHECK_ONLY=0

usage() {
  cat <<'EOF'
KoalaByte Blue T114 plug-in firmware flash helper

Usage:
  bash scripts/flash_t114_when_plugged.sh
  T114_PLUG_FLASH_PROFILE=combined-safe bash scripts/flash_t114_when_plugged.sh
  T114_PLUG_FLASH_PROFILE=color-mouth bash scripts/flash_t114_when_plugged.sh
  T114_PLUG_FLASH_PROFILE=hci-usb bash scripts/flash_t114_when_plugged.sh
  T114_PLUG_FLASH_PROFILE=skip bash scripts/flash_t114_when_plugged.sh
  bash scripts/flash_t114_when_plugged.sh --check-only

Manual T114 bootloader path:
  Connect the T114 by USB, then press RST twice quickly. The bootloader volume
  should appear as HT-n5262. The combined-safe profile auto-detects that volume
  and copies the generated UF2 firmware to it.

Profiles:
  combined-safe  Default combined T114 firmware for primary BLE JSON plus KillerKoala mouth/status JSON.
  color-mouth    Legacy mouth/status profile.
  hci-usb        Optional USB Bluetooth adapter profile.
  skip           Do not flash.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) CHECK_ONLY=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

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
  local selected_port="$3"
  local helper="$4"
  local uf2_mount="${5:-}"
  cat > "${STATUS_PATH}" <<JSON
{
  "status": $(json_escape "${status}"),
  "reason": $(json_escape "${reason}"),
  "profile": $(json_escape "${PROFILE}"),
  "selected_port": $(json_escape "${selected_port}"),
  "uf2_volume_name": $(json_escape "${UF2_VOLUME_NAME}"),
  "uf2_mount": $(json_escape "${uf2_mount}"),
  "helper": $(json_escape "${helper}"),
  "timeout_seconds": $(json_escape "${TIMEOUT_SECONDS}"),
  "source": "scripts/flash_t114_when_plugged.sh",
  "updated_at": $(date +%s)
}
JSON
}

resolve_port() {
  if [[ -n "${PORT}" && -e "${PORT}" ]]; then
    echo "${PORT}"
    return 0
  fi
  for candidate in /dev/koalabyte-heltec /dev/ttyACM0 /dev/ttyACM1 /dev/ttyUSB0 /dev/ttyUSB1; do
    if [[ -e "${candidate}" ]]; then
      echo "${candidate}"
      return 0
    fi
  done
  return 1
}

resolve_uf2_mount() {
  if [[ -n "${T114_UF2_MOUNT:-}" && -d "${T114_UF2_MOUNT}" ]]; then
    echo "${T114_UF2_MOUNT}"
    return 0
  fi
  local user_name="${SUDO_USER:-${USER:-}}"
  local candidates=()
  if [[ -n "${user_name}" ]]; then
    candidates+=("/media/${user_name}/${UF2_VOLUME_NAME}" "/run/media/${user_name}/${UF2_VOLUME_NAME}")
  fi
  candidates+=("/media/${UF2_VOLUME_NAME}" "/mnt/${UF2_VOLUME_NAME}" "/Volumes/${UF2_VOLUME_NAME}")
  candidates+=("/media"/*/"${UF2_VOLUME_NAME}" "/run/media"/*/"${UF2_VOLUME_NAME}")
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -d "${candidate}" ]]; then
      echo "${candidate}"
      return 0
    fi
  done
  return 1
}

helper_for_profile() {
  case "${PROFILE}" in
    combined-safe|combined_safe|combined) echo "scripts/flash_t114_combined_safe.sh" ;;
    color-mouth|mouth|color_mouth) echo "scripts/flash_heltec_mouth.sh" ;;
    hci-usb|hci_usb|koala-konnect|koala_konnect) echo "scripts/flash_nrf52840_t114_hci_usb.sh" ;;
    skip|none|disabled) echo "" ;;
    *) echo "unsupported" ;;
  esac
}

HELPER="$(helper_for_profile)"
if [[ "${HELPER}" == "unsupported" ]]; then
  write_status "unsupported_profile" "Unsupported T114_PLUG_FLASH_PROFILE. Use combined-safe, color-mouth, hci-usb, or skip." "" "" ""
  echo "Unsupported T114_PLUG_FLASH_PROFILE=${PROFILE}" >&2
  exit 2
fi

if [[ -z "${HELPER}" ]]; then
  write_status "skipped" "T114 plug-in firmware flashing skipped by profile." "" "" ""
  echo "T114 plug-in firmware flashing skipped."
  exit 0
fi

if [[ "${CHECK_ONLY}" == "1" ]]; then
  if [[ -f "${HELPER}" ]]; then
    write_status "check_ready" "Flash helper exists; check-only mode did not wait for or flash hardware. Combined-safe supports the HT-n5262 UF2 bootloader volume." "" "${HELPER}" ""
  else
    write_status "check_missing_helper" "Flash helper is not present yet; check-only mode did not fail hardware deployment." "" "${HELPER}" ""
  fi
  echo "T114 plug-in flash check-only status written to ${STATUS_PATH}"
  exit 0
fi

echo "Waiting for Heltec T114 USB device for profile ${PROFILE}..."
echo "For manual bootloader flash: connect USB, press RST twice quickly, wait for the HT-n5262 volume."
START=$(date +%s)
SELECTED_PORT=""
SELECTED_UF2_MOUNT=""
while true; do
  if [[ "${PROFILE}" == "combined-safe" || "${PROFILE}" == "combined_safe" || "${PROFILE}" == "combined" ]]; then
    if SELECTED_UF2_MOUNT="$(resolve_uf2_mount)"; then
      break
    fi
  fi
  if SELECTED_PORT="$(resolve_port)"; then
    break
  fi
  NOW=$(date +%s)
  if (( NOW - START >= TIMEOUT_SECONDS )); then
    write_status "not_plugged_in" "Timed out waiting for Heltec T114 USB serial device or HT-n5262 UF2 bootloader volume." "" "${HELPER}" ""
    echo "Timed out waiting for Heltec T114 USB serial device or HT-n5262 UF2 volume." >&2
    exit 1
  fi
  sleep "${POLL_SECONDS}"
done

if [[ -n "${SELECTED_UF2_MOUNT}" ]]; then
  export T114_UF2_MOUNT="${SELECTED_UF2_MOUNT}"
  export T114_FLASH_METHOD="uf2"
  write_status "bootloader_volume_detected" "HT-n5262 UF2 bootloader volume detected; selected UF2 drag-and-drop flash path." "" "${HELPER}" "${SELECTED_UF2_MOUNT}"
  echo "Heltec T114 bootloader volume detected at ${SELECTED_UF2_MOUNT}; running ${HELPER} with T114_FLASH_METHOD=uf2"
else
  export KOALABYTE_HELTEC_USB_PORT="${SELECTED_PORT}"
  export KOALABYTE_PRIMARY_BLE_PORT="${KOALABYTE_PRIMARY_BLE_PORT:-${SELECTED_PORT}}"
  export HELTEC_PORT="${HELTEC_PORT:-${SELECTED_PORT}}"
  write_status "plugged_in" "Heltec T114 USB serial device detected; preparing selected firmware helper." "${SELECTED_PORT}" "${HELPER}" ""
  echo "Heltec T114 detected at ${SELECTED_PORT}; running ${HELPER}"
fi

if [[ ! -f "${HELPER}" ]]; then
  write_status "missing_helper" "Selected firmware flash helper is not present in this branch." "${SELECTED_PORT}" "${HELPER}" "${SELECTED_UF2_MOUNT}"
  echo "Selected flash helper is missing: ${HELPER}" >&2
  exit 1
fi

bash "${HELPER}"
write_status "flash_helper_complete" "Selected firmware flash helper completed." "${SELECTED_PORT}" "${HELPER}" "${SELECTED_UF2_MOUNT}"
echo "T114 plug-in firmware flash complete."
