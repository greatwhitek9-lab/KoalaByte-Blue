#!/usr/bin/env bash
set -euo pipefail

# Public menu gate for T114 Meshtastic mode.
# Kept at this path for backwards compatibility with pi-companion/koalablue/meshtastic_app.py.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

export T114_SOFTWARE_BOOTLOADER="${T114_SOFTWARE_BOOTLOADER:-1}"
export T114_MESHTASTIC_AUTOFLASH="${T114_MESHTASTIC_AUTOFLASH:-1}"

if [[ -f scripts/enter_t114_uf2_bootloader.sh ]]; then
  bash scripts/enter_t114_uf2_bootloader.sh >/tmp/koalabyte_t114_auto_boot_entry.out 2>/tmp/koalabyte_t114_auto_boot_entry.err || true
fi

if command -v meshtastic >/dev/null 2>&1; then
  PORT="${KOALABYTE_MESHTASTIC_PORT:-${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-${HELTEC_PORT:-/dev/koalabyte-heltec}}}}"
  if [[ -e "${PORT}" ]]; then
    timeout 18 meshtastic --port "${PORT}" --info >/tmp/koalabyte_meshtastic_probe.out 2>/tmp/koalabyte_meshtastic_probe.err && {
      mkdir -p logs/meshtastic_app
      printf '{"status":"MESHTASTIC_MODE_READY","port":"%s","mode_gate":"software_auto_uf2","updated_at":%s}\n' "${PORT}" "$(date +%s)" > logs/meshtastic_app/t114_meshtastic_mode.json
      cat logs/meshtastic_app/t114_meshtastic_mode.json
      exit 0
    }
  fi
fi

UF2="${T114_MESHTASTIC_UF2:-releases/meshtastic-heltec-t114-ht-n5262.uf2}"
LABEL="${T114_UF2_VOLUME_NAME:-HT-n5262}"
MOUNT="${T114_UF2_MOUNT:-}"

if [[ ! -f "${UF2}" ]]; then
  mkdir -p logs/meshtastic_app
  printf '{"status":"MESHTASTIC_UF2_REQUIRED","uf2":"%s","updated_at":%s}\n' "${UF2}" "$(date +%s)" > logs/meshtastic_app/t114_meshtastic_mode.json
  cat logs/meshtastic_app/t114_meshtastic_mode.json
  exit 1
fi

if [[ -z "${MOUNT}" ]]; then
  for d in "/media/${USER:-}/${LABEL}" "/run/media/${USER:-}/${LABEL}" "/mnt/${LABEL}" "/media/${LABEL}"; do
    [[ -d "${d}" ]] && { MOUNT="${d}"; break; }
  done
fi

if [[ -z "${MOUNT}" ]]; then
  DEV="$(lsblk -pnro NAME,LABEL,FSTYPE 2>/dev/null | awk -v label="${LABEL}" '$2==label && $3=="vfat" {print $1; exit}')"
  if [[ -n "${DEV}" ]]; then
    MOUNT="${T114_UF2_MOUNTPOINT:-/mnt/koalabyte-t114-uf2}"
    sudo mkdir -p "${MOUNT}"
    sudo mount -o "uid=$(id -u),gid=$(id -g)" "${DEV}" "${MOUNT}" 2>/dev/null || sudo mount "${DEV}" "${MOUNT}"
  fi
fi

if [[ -z "${MOUNT}" || ! -d "${MOUNT}" ]]; then
  mkdir -p logs/meshtastic_app
  printf '{"status":"MESHTASTIC_BOOTLOADER_REQUIRED","reason":"UF2 volume not found after software request","updated_at":%s}\n' "$(date +%s)" > logs/meshtastic_app/t114_meshtastic_mode.json
  cat logs/meshtastic_app/t114_meshtastic_mode.json
  exit 1
fi

cp "${UF2}" "${MOUNT}/"
sync
mkdir -p logs/meshtastic_app
printf '{"status":"MESHTASTIC_FLASHED","uf2":"%s","uf2_mount":"%s","mode_gate":"software_auto_uf2","updated_at":%s}\n' "${UF2}" "${MOUNT}" "$(date +%s)" > logs/meshtastic_app/t114_meshtastic_mode.json
cat logs/meshtastic_app/t114_meshtastic_mode.json
