#!/usr/bin/env bash
set -euo pipefail

# Ensure the Heltec T114 / HT-n5262 is running Meshtastic firmware for menu actions.
# If the node already answers the Meshtastic CLI, this exits cleanly.
# If not, it flashes a configured Meshtastic UF2 when the HT-n5262 bootloader
# volume is present.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

STATUS_PATH="${T114_MESHTASTIC_STATUS_PATH:-logs/meshtastic_app/t114_meshtastic_mode.json}"
UF2_VOLUME_NAME="${T114_UF2_VOLUME_NAME:-HT-n5262}"
UF2_MOUNTPOINT="${T114_UF2_MOUNTPOINT:-/mnt/koalabyte-t114-uf2}"
MESHTASTIC_UF2="${T114_MESHTASTIC_UF2:-releases/meshtastic-heltec-t114-ht-n5262.uf2}"
MESHTASTIC_UF2_URL="${T114_MESHTASTIC_UF2_URL:-}"
PORT="${KOALABYTE_MESHTASTIC_PORT:-${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-${HELTEC_PORT:-/dev/koalabyte-heltec}}}}"
CHECK_SECONDS="${T114_MESHTASTIC_CHECK_SECONDS:-18}"
AUTOFLASH="${T114_MESHTASTIC_AUTOFLASH:-1}"
LAST_UF2_DEVICE=""

mkdir -p "$(dirname "${STATUS_PATH}")" "$(dirname "${MESHTASTIC_UF2}")"

json_escape() {
  python3 - <<'PY' "$1"
import json, sys
print(json.dumps(sys.argv[1]))
PY
}

write_status() {
  local status="$1"
  local reason="$2"
  local mode="${3:-meshtastic}"
  local mount="${4:-}"
  cat > "${STATUS_PATH}" <<JSON
{
  "status": $(json_escape "${status}"),
  "reason": $(json_escape "${reason}"),
  "requested_mode": "meshtastic",
  "active_mode": $(json_escape "${mode}"),
  "port": $(json_escape "${PORT}"),
  "uf2": $(json_escape "${MESHTASTIC_UF2}"),
  "uf2_url": $(json_escape "${MESHTASTIC_UF2_URL}"),
  "uf2_volume_name": $(json_escape "${UF2_VOLUME_NAME}"),
  "uf2_mount": $(json_escape "${mount}"),
  "uf2_block_device": $(json_escape "${LAST_UF2_DEVICE}"),
  "sx1262_driver": "Meshtastic firmware owns the SX1262 LoRa radio in this mode",
  "menu_action_gate": true,
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

meshtastic_alive() {
  command -v meshtastic >/dev/null 2>&1 || return 1
  [[ -e "${PORT}" ]] || return 1
  timeout "${CHECK_SECONDS}" meshtastic --port "${PORT}" --info >/tmp/koalabyte_meshtastic_probe.out 2>/tmp/koalabyte_meshtastic_probe.err || return 1
  return 0
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

fetch_uf2_if_configured() {
  if [[ -f "${MESHTASTIC_UF2}" ]]; then
    return 0
  fi
  if [[ -z "${MESHTASTIC_UF2_URL}" ]]; then
    return 1
  fi
  if ! command -v curl >/dev/null 2>&1; then
    write_status "missing_curl" "Meshtastic UF2 URL is configured but curl is not installed." "missing" ""
    return 1
  fi
  echo "Downloading Meshtastic UF2 from configured URL..."
  curl -L --fail --output "${MESHTASTIC_UF2}" "${MESHTASTIC_UF2_URL}"
}

if meshtastic_alive; then
  write_status "MESHTASTIC_MODE_READY" "T114 already answers Meshtastic CLI on the configured serial port." "meshtastic" ""
  cat "${STATUS_PATH}"
  exit 0
fi

if [[ "${AUTOFLASH}" != "1" ]]; then
  write_status "MESHTASTIC_MODE_NOT_READY" "T114 does not answer Meshtastic CLI and T114_MESHTASTIC_AUTOFLASH is disabled." "unknown" ""
  cat "${STATUS_PATH}"
  exit 1
fi

if ! fetch_uf2_if_configured; then
  write_status "MESHTASTIC_UF2_REQUIRED" "No Meshtastic UF2 found. Place one at ${MESHTASTIC_UF2} or set T114_MESHTASTIC_UF2_URL to a trusted Meshtastic T114 UF2 release asset." "missing" ""
  cat "${STATUS_PATH}"
  exit 1
fi

MOUNT="$(resolve_uf2_mount || true)"
if [[ -z "${MOUNT}" || ! -d "${MOUNT}" ]]; then
  write_status "MESHTASTIC_BOOTLOADER_REQUIRED" "T114 is not in Meshtastic mode and the ${UF2_VOLUME_NAME} UF2 volume was not found. Double-tap RST, then choose the Meshtastic menu action again." "bootloader_required" ""
  cat "${STATUS_PATH}"
  exit 1
fi

echo "Flashing Meshtastic UF2 ${MESHTASTIC_UF2} to ${MOUNT}/"
cp "${MESHTASTIC_UF2}" "${MOUNT}/"
sync
write_status "MESHTASTIC_FLASHED" "Meshtastic UF2 copied to T114. Unplug/replug normally if the board does not reconnect automatically." "meshtastic_pending_replug" "${MOUNT}"
cat "${STATUS_PATH}"
