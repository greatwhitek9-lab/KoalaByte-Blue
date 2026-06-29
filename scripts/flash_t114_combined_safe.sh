#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BUILD_DIR="${T114_COMBINED_BUILD_DIR:-build/t114-combined-safe}"
STATUS_PATH="${T114_COMBINED_FLASH_STATUS_PATH:-logs/t114_combined_safe_flash_status.json}"
FLASH_METHOD="${T114_FLASH_METHOD:-auto}"
BUILD_FIRST="${T114_COMBINED_BUILD_FIRST:-1}"
STRICT="${STRICT_T114_COMBINED_FLASH:-1}"
PORT="${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-}}"
UF2_VOLUME_NAME="${T114_UF2_VOLUME_NAME:-HT-n5262}"
UF2_MOUNTPOINT="${T114_UF2_MOUNTPOINT:-/mnt/koalabyte-t114-uf2}"
LAST_UF2_DEVICE=""

mkdir -p "$(dirname "${STATUS_PATH}")"

json_escape() {
  python3 - <<'PY' "$1"
import json, sys
print(json.dumps(sys.argv[1]))
PY
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

mount_uf2_block_if_needed() {
  local record mount_path device
  record="$(find_uf2_block_record || true)"
  [[ -n "${record}" ]] || return 1
  mount_path="${record%%$'\t'*}"
  device="${record#*$'\t'}"
  LAST_UF2_DEVICE="${device}"
  if [[ -n "${mount_path}" && -d "${mount_path}" ]]; then
    printf '%s\n' "${mount_path}"
    return 0
  fi
  [[ -n "${device}" && -e "${device}" ]] || return 1
  sudo_or_root mkdir -p "${UF2_MOUNTPOINT}" || return 1
  if command -v mountpoint >/dev/null 2>&1 && mountpoint -q "${UF2_MOUNTPOINT}"; then
    printf '%s\n' "${UF2_MOUNTPOINT}"
    return 0
  fi
  sudo_or_root mount -o "uid=$(id -u),gid=$(id -g)" "${device}" "${UF2_MOUNTPOINT}" || sudo_or_root mount "${device}" "${UF2_MOUNTPOINT}" || return 1
  printf '%s\n' "${UF2_MOUNTPOINT}"
}

find_uf2_mount() {
  if [[ -n "${T114_UF2_MOUNT:-}" && -d "${T114_UF2_MOUNT}" ]]; then
    printf '%s\n' "${T114_UF2_MOUNT}"
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
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  mount_uf2_block_if_needed
}

write_status() {
  local status="$1"
  local reason="$2"
  local mount="${3:-}"
  cat > "${STATUS_PATH}" <<JSON
{
  "status": $(json_escape "${status}"),
  "reason": $(json_escape "${reason}"),
  "mode": "t114_combined_safe",
  "profile": "combined-safe",
  "build_dir": $(json_escape "${BUILD_DIR}"),
  "flash_method": $(json_escape "${FLASH_METHOD}"),
  "port": $(json_escape "${PORT}"),
  "uf2_volume_name": $(json_escape "${UF2_VOLUME_NAME}"),
  "uf2_mount": $(json_escape "${mount}"),
  "uf2_mountpoint": $(json_escape "${UF2_MOUNTPOINT}"),
  "uf2_block_device": $(json_escape "${LAST_UF2_DEVICE}"),
  "primary_ble": "heltec-t114-nrf52840",
  "secondary_ble_nodes": ["esp32-s3-dualeye", "raspberry-pi-bluez"],
  "host_expectation": "After flashing, the Heltec emits newline-delimited JSON over USB CDC for mouth/status, passive BLE observations, and guarded GNSS/LoRa readiness hooks.",
  "updated_at": $(date +%s)
}
JSON
}

if [[ "${BUILD_FIRST}" == "1" ]]; then
  STRICT_T114_COMBINED_BUILD="${STRICT}" bash scripts/build_t114_combined_safe.sh
fi

if [[ "${FLASH_METHOD}" == "auto" ]]; then
  if find_uf2_mount >/dev/null; then
    FLASH_METHOD="uf2"
  else
    FLASH_METHOD="west"
  fi
fi

case "${FLASH_METHOD}" in
  west)
    if ! command -v west >/dev/null 2>&1; then
      write_status "missing_west" "west is not installed. Double-tap RST on the T114 and rerun with the HT-n5262 UF2 volume mounted, or install nRF Connect SDK/west."
      exit 1
    fi
    if [[ ! -d "${BUILD_DIR}" ]]; then
      write_status "missing_build" "Build directory does not exist."
      exit 1
    fi
    west flash -d "${BUILD_DIR}"
    write_status "flashed" "T114 combined-safe firmware flashed with west."
    ;;
  uf2)
    UF2="${T114_UF2_PATH:-${BUILD_DIR}/zephyr/zephyr.uf2}"
    MOUNT="$(find_uf2_mount || true)"
    if [[ -z "${MOUNT}" || ! -d "${MOUNT}" ]]; then
      write_status "missing_uf2_mount" "Double-tap RST on the T114 until the HT-n5262 UF2 volume appears. On Pi OS Lite, this helper also tries to mount the label automatically with lsblk/mount; set T114_UF2_MOUNT if needed." ""
      exit 1
    fi
    if [[ ! -f "${UF2}" ]]; then
      write_status "missing_uf2" "UF2 artifact not found. Build should produce build/t114-combined-safe/zephyr/zephyr.uf2." "${MOUNT}"
      exit 1
    fi
    cp "${UF2}" "${MOUNT}/"
    sync
    write_status "flashed" "T114 combined-safe firmware copied to HT-n5262 UF2 volume." "${MOUNT}"
    ;;
  *)
    write_status "unsupported_method" "Unsupported T114_FLASH_METHOD. Use auto, west, or uf2."
    exit 2
    ;;
esac

echo "T114 combined-safe flash helper complete. Verify JSON with: python3 scripts/discover_koalabyte_ports.py --profile heltec && PYTHONPATH=pi-companion python3 scripts/run_ble_node_manager.py --duration 30"
