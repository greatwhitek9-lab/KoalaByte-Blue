#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${T114_HCI_BUILD_DIR:-build/nrf52840-t114-hci-usb}"
STATUS_PATH="${T114_ACTIVE_BLE_MODE_PATH:-logs/t114_active_ble_mode.json}"
FLASH_METHOD="${T114_FLASH_METHOD:-uf2}"
PORT="${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-}}"
BUILD_FIRST="${T114_HCI_BUILD_FIRST:-1}"
STRICT="${STRICT_T114_HCI_FLASH:-1}"
RELEASE_UF2="${T114_RELEASE_UF2:-releases/koalabyte-blue-t114-hci-usb-HT-n5262-offset1000.uf2}"
UF2="${T114_UF2_PATH:-${RELEASE_UF2}}"
UF2_VOLUME_NAME="${T114_UF2_VOLUME_NAME:-HT-n5262}"
UF2_MOUNTPOINT="${T114_UF2_MOUNTPOINT:-/mnt/koalabyte-t114-uf2}"

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
  local uf2_mount="${3:-}"
  cat > "${STATUS_PATH}" <<JSON
{
  "status": $(json_escape "${status}"),
  "reason": $(json_escape "${reason}"),
  "mode": "t114_koala_konnect",
  "hci_profile": "t114_hci_usb",
  "product_mode": "Koala Konnect",
  "build_dir": $(json_escape "${BUILD_DIR}"),
  "flash_method": $(json_escape "${FLASH_METHOD}"),
  "port": $(json_escape "${PORT}"),
  "uf2": $(json_escape "${UF2}"),
  "uf2_mount": $(json_escape "${uf2_mount}"),
  "uf2_volume_name": $(json_escape "${UF2_VOLUME_NAME}"),
  "external_bluetooth_adapter": true,
  "host_expectation": "After normal replug, supported Linux hosts should expose the Heltec board as a USB Bluetooth HCI adapter.",
  "verify_linux": "lsusb && ls /sys/class/bluetooth && bluetoothctl list",
  "updated_at": $(date +%s)
}
JSON
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

  local record mount_path device
  record="$(find_uf2_block_record || true)"
  [[ -n "${record}" ]] || return 1
  mount_path="${record%%$'\t'*}"
  device="${record#*$'\t'}"

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

if [[ "${BUILD_FIRST}" == "1" ]]; then
  STRICT_T114_HCI_BUILD="${STRICT}" bash scripts/build_nrf52840_t114_hci_usb.sh
fi

case "${FLASH_METHOD}" in
  uf2)
    if [[ ! -f "${UF2}" ]]; then
      write_status "missing_uf2" "Patched UF2 artifact not found. Expected ${UF2}." ""
      exit 1
    fi

    MOUNT="$(resolve_uf2_mount || true)"
    if [[ -z "${MOUNT}" || ! -d "${MOUNT}" ]]; then
      write_status "missing_uf2_mount" "HT-n5262 UF2 bootloader volume not found. Double-tap RST until the ${UF2_VOLUME_NAME} volume appears." ""
      exit 1
    fi

    echo "Copying ${UF2} to ${MOUNT}/"
    cp "${UF2}" "${MOUNT}/"
    sync
    write_status "flashed" "T114 HCI USB firmware copied to HT-n5262 UF2 bootloader volume." "${MOUNT}"
    ;;

  west)
    if ! command -v west >/dev/null 2>&1; then
      write_status "missing_west" "west is not installed." ""
      exit 1
    fi
    if [[ ! -d "${BUILD_DIR}" ]]; then
      write_status "missing_build" "Build directory does not exist." ""
      exit 1
    fi
    west flash -d "${BUILD_DIR}"
    write_status "flashed" "T114 HCI USB firmware flashed with west. UF2 flashing is preferred for HT-n5262." ""
    ;;

  *)
    write_status "unsupported_method" "Unsupported T114_FLASH_METHOD. Use uf2 or west." ""
    exit 2
    ;;
esac

echo "T114 HCI USB flash helper complete."
echo "Unplug the board, wait five seconds, then plug it back in normally."
echo "Verify on Linux with: lsusb && ls /sys/class/bluetooth && bluetoothctl list"
