#!/usr/bin/env bash
set -euo pipefail

# Try to place the Heltec T114 / HT-n5262 into UF2 bootloader mode by software.
# This avoids the physical double-tap RST step when the currently running
# firmware supports serial-triggered bootloader entry.

UF2_VOLUME_NAME="${T114_UF2_VOLUME_NAME:-HT-n5262}"
PORT="${T114_BOOTLOADER_PORT:-${KOALABYTE_MESHTASTIC_PORT:-${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-${HELTEC_PORT:-}}}}}"
TIMEOUT_SECONDS="${T114_BOOTLOADER_TIMEOUT_SECONDS:-20}"
STATUS_PATH="${T114_BOOTLOADER_STATUS_PATH:-logs/t114_bootloader_entry_status.json}"

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
  local device="${3:-}"
  cat > "${STATUS_PATH}" <<JSON
{
  "status": $(json_escape "${status}"),
  "reason": $(json_escape "${reason}"),
  "port": $(json_escape "${PORT}"),
  "uf2_volume_name": $(json_escape "${UF2_VOLUME_NAME}"),
  "uf2_device": $(json_escape "${device}"),
  "updated_at": $(date +%s)
}
JSON
}

find_uf2_device() {
  command -v lsblk >/dev/null 2>&1 || return 1
  lsblk -pnro NAME,LABEL,FSTYPE 2>/dev/null | awk -v label="${UF2_VOLUME_NAME}" '$2==label && $3=="vfat" {print $1; exit}'
}

pick_port() {
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

wait_for_uf2() {
  local deadline=$(( $(date +%s) + TIMEOUT_SECONDS ))
  local dev=""
  while (( $(date +%s) < deadline )); do
    dev="$(find_uf2_device || true)"
    if [[ -n "${dev}" ]]; then
      echo "${dev}"
      return 0
    fi
    sleep 1
  done
  return 1
}

existing="$(find_uf2_device || true)"
if [[ -n "${existing}" ]]; then
  write_status "UF2_ALREADY_PRESENT" "HT-n5262 UF2 volume is already available." "${existing}"
  cat "${STATUS_PATH}"
  exit 0
fi

PORT="$(pick_port || true)"
if [[ -z "${PORT}" ]]; then
  write_status "SERIAL_PORT_NOT_FOUND" "No Heltec serial port found. Physical RST double-tap may be required."
  cat "${STATUS_PATH}"
  exit 1
fi

# KoalaByte-aware firmware can implement one of these text requests.
for line in '{"type":"koalabyte_bootloader","mode":"uf2"}' '{"type":"bootloader","mode":"uf2"}' 'KOALABYTE_BOOTLOADER_UF2' 'REBOOT_UF2'; do
  printf '%s\n' "${line}" > "${PORT}" 2>/dev/null || true
  sleep 0.1
done

if dev="$(wait_for_uf2 || true)" && [[ -n "${dev}" ]]; then
  write_status "UF2_READY" "Board entered UF2 mode through KoalaByte serial request." "${dev}"
  cat "${STATUS_PATH}"
  exit 0
fi

# Common UF2 serial touch flow. This works only when the current firmware/USB
# stack honors a 1200-baud close as a bootloader-entry request.
stty -F "${PORT}" 1200 hupcl 2>/dev/null || true
python3 - <<'PY' "${PORT}" >/dev/null 2>&1 || true
import sys
try:
    open(sys.argv[1], 'ab', buffering=0).close()
except Exception:
    pass
PY

if dev="$(wait_for_uf2 || true)" && [[ -n "${dev}" ]]; then
  write_status "UF2_READY" "Board entered UF2 mode through serial 1200-baud touch." "${dev}"
  cat "${STATUS_PATH}"
  exit 0
fi

write_status "UF2_NOT_READY" "Software UF2 entry did not succeed. Current firmware may not support it; double-tap RST once, then rerun the selected action."
cat "${STATUS_PATH}"
exit 1
