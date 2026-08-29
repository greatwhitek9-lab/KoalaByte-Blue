#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

UF2_VOLUME_NAME="${T114_UF2_VOLUME_NAME:-HT-n5262}"
PORT="${T114_BOOTLOADER_PORT:-${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-${HELTEC_PORT:-}}}}"
AUTO_TIMEOUT_SECONDS="${T114_AUTO_BOOTLOADER_TIMEOUT_SECONDS:-12}"
MANUAL_TIMEOUT_SECONDS="${T114_BOOTLOADER_TIMEOUT_SECONDS:-45}"
STATUS_PATH="${T114_BOOTLOADER_STATUS_PATH:-logs/deployment/t114_bootloader_entry_status.json}"

mkdir -p "$(dirname "${STATUS_PATH}")"

write_status() {
  local status="$1" reason="$2" device="${3:-}"
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${PORT}" "${UF2_VOLUME_NAME}" "${device}" <<'PY'
import json, sys, time
from pathlib import Path
path, status, reason, port, label, device = sys.argv[1:]
Path(path).write_text(json.dumps({
    "status": status,
    "reason": reason,
    "port": port,
    "uf2_volume_name": label,
    "uf2_device": device,
    "serial_privilege_fallback": True,
    "updated_at": time.time(),
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

find_uf2_device() {
  command -v lsblk >/dev/null 2>&1 || return 1
  lsblk -pnro NAME,LABEL,FSTYPE 2>/dev/null | \
    awk -v label="${UF2_VOLUME_NAME}" '$2==label && ($3=="vfat" || $3=="fat") {print $1; exit}'
}

pick_port() {
  if [[ -n "${PORT}" && -e "${PORT}" ]]; then
    printf '%s\n' "${PORT}"
    return 0
  fi
  # Stable aliases only. Blind ttyACM/ttyUSB selection can target the ESP32.
  for candidate in \
    /dev/koalabyte-heltec \
    /dev/koalabyte-heltec-t114 \
    /dev/koalabyte-nrf52840; do
    if [[ -e "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

wait_for_uf2() {
  local timeout="$1"
  local deadline=$(( $(date +%s) + timeout ))
  local dev=""
  while (( $(date +%s) < deadline )); do
    dev="$(find_uf2_device || true)"
    if [[ -n "${dev}" ]]; then
      printf '%s\n' "${dev}"
      return 0
    fi
    sleep 1
  done
  return 1
}

write_serial_line() {
  local line="$1"
  if [[ -w "${PORT}" ]]; then
    printf '%s\n' "${line}" >"${PORT}"
  elif command -v sudo >/dev/null 2>&1; then
    printf '%s\n' "${line}" | sudo tee "${PORT}" >/dev/null
  else
    return 1
  fi
}

serial_touch_1200() {
  if [[ -r "${PORT}" && -w "${PORT}" ]]; then
    stty -F "${PORT}" 1200 hupcl 2>/dev/null || true
    python3 - "${PORT}" >/dev/null 2>&1 <<'PY' || true
import sys
try:
    open(sys.argv[1], "ab", buffering=0).close()
except Exception:
    pass
PY
  elif command -v sudo >/dev/null 2>&1; then
    sudo stty -F "${PORT}" 1200 hupcl 2>/dev/null || true
    sudo python3 - "${PORT}" >/dev/null 2>&1 <<'PY' || true
import sys
try:
    open(sys.argv[1], "ab", buffering=0).close()
except Exception:
    pass
PY
  fi
}

existing="$(find_uf2_device || true)"
if [[ -n "${existing}" ]]; then
  write_status UF2_ALREADY_PRESENT "HT-n5262 UF2 volume is already available." "${existing}"
  exit 0
fi

PORT="$(pick_port || true)"
if [[ -n "${PORT}" ]]; then
  echo "Requesting T114 UF2 bootloader mode over ${PORT}..."
  for line in \
    '{"type":"koalabyte_bootloader","mode":"uf2"}' \
    '{"type":"bootloader","mode":"uf2"}' \
    'KOALABYTE_BOOTLOADER_UF2' \
    'REBOOT_UF2'; do
    write_serial_line "${line}" 2>/dev/null || true
    sleep 0.15
  done
  if dev="$(wait_for_uf2 "${AUTO_TIMEOUT_SECONDS}" || true)" && [[ -n "${dev}" ]]; then
    write_status UF2_READY "T114 entered UF2 through the KoalaByte serial command." "${dev}"
    exit 0
  fi

  echo "Trying a 1200-baud serial touch..."
  serial_touch_1200
  if dev="$(wait_for_uf2 "${AUTO_TIMEOUT_SECONDS}" || true)" && [[ -n "${dev}" ]]; then
    write_status UF2_READY "T114 entered UF2 through a 1200-baud serial touch." "${dev}"
    exit 0
  fi
fi

cat >&2 <<EOF
The T114 UF2 volume did not appear automatically.
Double-tap the T114 reset button now so ${UF2_VOLUME_NAME} appears; the installer will continue watching for ${MANUAL_TIMEOUT_SECONDS} seconds.
EOF
if dev="$(wait_for_uf2 "${MANUAL_TIMEOUT_SECONDS}" || true)" && [[ -n "${dev}" ]]; then
  write_status UF2_READY "T114 entered UF2 after the physical reset fallback." "${dev}"
  exit 0
fi

write_status UF2_NOT_READY "T114 UF2 volume did not appear before the deployment timeout."
echo "T114 UF2 bootloader entry failed." >&2
exit 1
