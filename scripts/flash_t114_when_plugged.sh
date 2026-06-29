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
UF2_MOUNTPOINT="${T114_UF2_MOUNTPOINT:-/mnt/koalabyte-t114-uf2}"
REQUIRE_UF2="${T114_REQUIRE_UF2:-0}"
CHECK_ONLY=0
LAST_UF2_DEVICE=""

usage() {
  cat <<'EOF'
KoalaByte Blue T114 plug-in firmware flash helper

Usage:
  bash scripts/flash_t114_when_plugged.sh
  T114_PLUG_FLASH_PROFILE=combined-safe bash scripts/flash_t114_when_plugged.sh
  T114_REQUIRE_UF2=1 T114_FLASH_METHOD=uf2 bash scripts/flash_t114_when_plugged.sh
  T114_PLUG_FLASH_PROFILE=color-mouth bash scripts/flash_t114_when_plugged.sh
  T114_PLUG_FLASH_PROFILE=hci-usb bash scripts/flash_t114_when_plugged.sh
  T114_PLUG_FLASH_PROFILE=skip bash scripts/flash_t114_when_plugged.sh
  bash scripts/flash_t114_when_plugged.sh --check-only

Manual T114 bootloader path:
  Connect the T114 by USB, then press RST twice quickly. The bootloader volume
  should appear as HT-n5262. The combined-safe profile auto-detects that volume,
  mounts it on Pi OS Lite when needed, and copies the generated UF2 firmware to it.

UF2-first mode:
  Set T114_REQUIRE_UF2=1 and T114_FLASH_METHOD=uf2 to require the HT-n5262 UF2
  bootloader volume before flashing. This prevents accidental fallback to serial
  west flashing during a one-shot install.

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

json_bool() {
  case "$1" in
    1|true|True|yes|YES|on|ON) printf 'true' ;;
    *) printf 'false' ;;
  esac
}

sudo_or_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    return 1
  fi
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
  "require_uf2": $(json_bool "${REQUIRE_UF2}"),
  "uf2_volume_name": $(json_escape "${UF2_VOLUME_NAME}"),
  "uf2_mount": $(json_escape "${uf2_mount}"),
  "uf2_mountpoint": $(json_escape "${UF2_MOUNTPOINT}"),
  "uf2_block_device": $(json_escape "${LAST_UF2_DEVICE}"),
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

find_uf2_block_record() {
  command -v lsblk >/dev/null 2>&1 || return 1
  python3 - <<'PY' "${UF2_VOLUME_NAME}"
import json
import subprocess
import sys

target = sys.argv[1].lower()
try:
    data = json.loads(subprocess.check_output(["lsblk", "-J", "-o", "LABEL,PATH,MOUNTPOINT,TYPE"], text=True))
except Exception:
    sys.exit(1)

def walk(nodes):
    for node in nodes:
        label = str(node.get("label") or "").lower()
        if label == target:
            print(f"{node.get('mountpoint') or ''}\t{node.get('path') or ''}")
            return True
        if walk(node.get("children") or []):
            return True
    return False

sys.exit(0 if walk(data.get("blockdevices") or []) else 1)
PY
}

mount_uf2_block_if_needed() {
  local record mount_path device
  record="$(find_uf2_block_record || true)"
  [[ -n "${record}" ]] || return 1
  mount_path="${record%%$'\t'*}"
  device="${record#*$'\t'}"
  LAST_UF2_DEVICE="${device}"
  if [[ -n "${mount_path}" && -d "${mount_path}" ]]; then
    echo "${mount_path}"
    return 0
  fi
  [[ -n "${device}" && -e "${device}" ]] || return 1
  sudo_or_root mkdir -p "${UF2_MOUNTPOINT}" || return 1
  if command -v mountpoint >/dev/null 2>&1 && mountpoint -q "${UF2_MOUNTPOINT}"; then
    echo "${UF2_MOUNTPOINT}"
    return 0
  fi
  sudo_or_root mount -o "uid=$(id -u),gid=$(id -g)" "${device}" "${UF2_MOUNTPOINT}" || sudo_or_root mount "${device}" "${UF2_MOUNTPOINT}" || return 1
  echo "${UF2_MOUNTPOINT}"
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
  candidates+=("/media/${UF2_VOLUME_NAME}" "/mnt/${UF2_VOLUME_NAME}" "/Volumes/${UF2_VOLUME_NAME}" "${UF2_MOUNTPOINT}")
  candidates+=("/media"/*/"${UF2_VOLUME_NAME}" "/run/media"/*/"${UF2_VOLUME_NAME}")
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -d "${candidate}" ]]; then
      echo "${candidate}"
      return 0
    fi
  done
  mount_uf2_block_if_needed
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
    write_status "check_ready" "Flash helper exists; check-only mode did not wait for or flash hardware. Combined-safe supports the HT-n5262 UF2 bootloader volume and Pi OS Lite mount path." "" "${HELPER}" ""
  else
    write_status "check_missing_helper" "Flash helper is not present yet; check-only mode did not fail hardware deployment." "" "${HELPER}" ""
  fi
  echo "T114 plug-in flash check-only status written to ${STATUS_PATH}"
  exit 0
fi

if [[ "${REQUIRE_UF2}" == "1" && !( "${PROFILE}" == "combined-safe" || "${PROFILE}" == "combined_safe" || "${PROFILE}" == "combined" ) ]]; then
  write_status "unsupported_uf2_first_profile" "T114_REQUIRE_UF2=1 is only supported with the combined-safe profile." "" "${HELPER}" ""
  echo "T114_REQUIRE_UF2=1 requires T114_PLUG_FLASH_PROFILE=combined-safe." >&2
  exit 2
fi

echo "Waiting for Heltec T114 USB device for profile ${PROFILE}..."
if [[ "${REQUIRE_UF2}" == "1" ]]; then
  echo "UF2-first mode is required: double-tap RST until the ${UF2_VOLUME_NAME} bootloader volume appears. Serial fallback is disabled for this run."
else
  echo "For manual bootloader flash: connect USB, press RST twice quickly, wait for the ${UF2_VOLUME_NAME} volume. On Pi OS Lite this script can mount the detected label at ${UF2_MOUNTPOINT}."
fi
START=$(date +%s)
SELECTED_PORT=""
SELECTED_UF2_MOUNT=""
while true; do
  if [[ "${PROFILE}" == "combined-safe" || "${PROFILE}" == "combined_safe" || "${PROFILE}" == "combined" ]]; then
    if SELECTED_UF2_MOUNT="$(resolve_uf2_mount)"; then
      break
    fi
  fi
  if [[ "${REQUIRE_UF2}" != "1" ]]; then
    if SELECTED_PORT="$(resolve_port)"; then
      break
    fi
  fi
  NOW=$(date +%s)
  if (( NOW - START >= TIMEOUT_SECONDS )); then
    if [[ "${REQUIRE_UF2}" == "1" ]]; then
      write_status "uf2_not_found" "Timed out waiting for required ${UF2_VOLUME_NAME} UF2 bootloader volume." "" "${HELPER}" ""
      echo "Timed out waiting for required ${UF2_VOLUME_NAME} UF2 bootloader volume. Press RST twice quickly on the T114 and rerun." >&2
    else
      write_status "not_plugged_in" "Timed out waiting for Heltec T114 USB serial device or ${UF2_VOLUME_NAME} UF2 bootloader volume." "" "${HELPER}" ""
      echo "Timed out waiting for Heltec T114 USB serial device or ${UF2_VOLUME_NAME} UF2 volume." >&2
    fi
    exit 1
  fi
  sleep "${POLL_SECONDS}"
done

if [[ -n "${SELECTED_UF2_MOUNT}" ]]; then
  export T114_UF2_MOUNT="${SELECTED_UF2_MOUNT}"
  export T114_FLASH_METHOD="uf2"
  write_status "bootloader_volume_detected" "${UF2_VOLUME_NAME} UF2 bootloader volume detected; selected UF2 drag-and-drop flash path." "" "${HELPER}" "${SELECTED_UF2_MOUNT}"
  echo "Heltec T114 bootloader volume detected at ${SELECTED_UF2_MOUNT}; running ${HELPER} with T114_FLASH_METHOD=uf2"
else
  export KOALABYTE_HELTEC_USB_PORT="${SELECTED_PORT}"
  export KOALABYTE_PRIMARY_BLE_PORT="${KOALABYTE_PRIMARY_BLE_PORT:-${SELECTED_PORT}}"
  export HELTEC_PORT="${HELTEC_PORT:-${SELECTED_PORT}}"
  write_status "plugged_in" "Heltec T114 USB serial device detected; preparing selected firmware helper." "${SELECTED_PORT}" "${HELPER}" ""
  echo "Heltec T114 detected at ${SELECTED_PORT}; running ${HELPER}"
fi

if [[ ! -f "${HELPER}" ]]; then
  write_status "missing_helper" "Selected firmware flash helper is missing in this branch." "${SELECTED_PORT}" "${HELPER}" "${SELECTED_UF2_MOUNT}"
  echo "Selected flash helper is missing: ${HELPER}" >&2
  exit 1
fi

bash "${HELPER}"
write_status "flash_helper_complete" "Selected firmware flash helper completed." "${SELECTED_PORT}" "${HELPER}" "${SELECTED_UF2_MOUNT}"
echo "T114 plug-in firmware flash complete."
