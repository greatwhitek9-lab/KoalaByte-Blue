#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERFACE="${CAN_INTERFACE:-can0}"
BITRATE="${CAN_BITRATE:-500000}"
RESTART_MS="${CAN_RESTART_MS:-100}"
WAIT_SECONDS="${CAN_WAIT_SECONDS:-30}"
STRICT_CAN_SETUP="${STRICT_CAN_SETUP:-0}"
OUTPUT_DIR="${CAN_SETUP_OUTPUT_DIR:-${REPO_ROOT}/logs/koala_kan_kommander}"

usage() {
  cat <<'EOF'
KoalaByte Blue SocketCAN setup helper for InnoMaker USB-to-CAN

Usage:
  bash scripts/setup_can0.sh
  bash scripts/setup_can0.sh --interface can0 --bitrate 500000
  bash scripts/setup_can0.sh --interface auto --wait-seconds 45
  STRICT_CAN_SETUP=1 bash scripts/setup_can0.sh

Environment:
  CAN_INTERFACE       SocketCAN interface name. Default: can0; use auto for first can* device
  CAN_BITRATE         CAN bitrate. Default: 500000
  CAN_RESTART_MS      Automatic bus-off recovery delay. Default: 100
  CAN_WAIT_SECONDS    Wait for USB enumeration. Default: 30
  STRICT_CAN_SETUP    1 fails if modules/interface setup fails. Default: 0

This helper loads the Linux CAN and gs_usb modules, waits for the adapter to
enumerate, and configures SocketCAN. It never flashes or modifies adapter firmware.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --interface) INTERFACE="${2:-}"; shift 2 ;;
    --bitrate) BITRATE="${2:-}"; shift 2 ;;
    --restart-ms) RESTART_MS="${2:-}"; shift 2 ;;
    --wait-seconds) WAIT_SECONDS="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for numeric in BITRATE RESTART_MS WAIT_SECONDS; do
  value="${!numeric}"
  if [[ ! "${value}" =~ ^[0-9]+$ ]]; then
    echo "${numeric} must be a non-negative integer, got: ${value}" >&2
    exit 2
  fi
done
if [[ "${BITRATE}" == "0" ]]; then
  echo "CAN_BITRATE must be greater than zero." >&2
  exit 2
fi

mkdir -p "${OUTPUT_DIR}"
LOG_JSON="${OUTPUT_DIR}/${INTERFACE}_setup.json"
LOG_TXT="${OUTPUT_DIR}/${INTERFACE}_setup.log"
: > "${LOG_TXT}"

if [[ "${EUID}" -eq 0 ]]; then
  sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then
  sudo_cmd=(sudo)
else
  sudo_cmd=()
fi

run_step() {
  local label="$1"
  shift
  echo "+ $*" | tee -a "${LOG_TXT}"
  if "$@" >>"${LOG_TXT}" 2>&1; then
    echo "${label}: ok" | tee -a "${LOG_TXT}"
    return 0
  fi
  local rc=$?
  echo "${label}: failed rc=${rc}" | tee -a "${LOG_TXT}"
  return "${rc}"
}

status="ok"
reason="configured_or_checked"
selected_interface="${INTERFACE}"

for module in can can_raw can_dev gs_usb; do
  if command -v modprobe >/dev/null 2>&1; then
    if ! run_step "modprobe_${module}" "${sudo_cmd[@]}" modprobe "${module}"; then
      status="warning"
      reason="one_or_more_can_modules_failed_to_load"
    fi
  else
    echo "modprobe not found; skipping module load for ${module}" | tee -a "${LOG_TXT}"
    status="warning"
    reason="modprobe_not_found"
  fi
done

if command -v udevadm >/dev/null 2>&1; then
  run_step "udev_settle" "${sudo_cmd[@]}" udevadm settle --timeout="${WAIT_SECONDS}" || true
fi

find_can_interface() {
  if [[ "${INTERFACE}" != "auto" && -d "/sys/class/net/${INTERFACE}" ]]; then
    printf '%s\n' "${INTERFACE}"
    return 0
  fi
  local path
  path="$(find /sys/class/net -maxdepth 1 -type l -name 'can*' -print 2>/dev/null | sort | head -n 1 || true)"
  [[ -n "${path}" ]] && basename "${path}"
}

deadline=$((SECONDS + WAIT_SECONDS))
while true; do
  selected_interface="$(find_can_interface || true)"
  if [[ -n "${selected_interface}" ]]; then
    break
  fi
  if (( SECONDS >= deadline )); then
    break
  fi
  sleep 1
done

usb_line=""
if command -v lsusb >/dev/null 2>&1; then
  usb_line="$(lsusb | grep -Ei 'innomaker|usb.?can|gs[_ -]?usb|candle|canable' | head -n 1 || true)"
fi

if ! command -v ip >/dev/null 2>&1; then
  echo "ip command not found; cannot configure SocketCAN" | tee -a "${LOG_TXT}"
  status="warning"
  reason="ip_command_not_found"
elif [[ -n "${selected_interface}" ]] && ip link show "${selected_interface}" >/dev/null 2>&1; then
  if ip -details link show "${selected_interface}" 2>/dev/null | grep -Eq "bitrate ${BITRATE}.*state (ERROR-ACTIVE|ERROR-WARNING)|state UP"; then
    echo "${selected_interface} already appears configured; preserving the live interface." | tee -a "${LOG_TXT}"
  else
    run_step "set_down_${selected_interface}" "${sudo_cmd[@]}" ip link set "${selected_interface}" down || true
    if ! run_step "set_type_${selected_interface}" "${sudo_cmd[@]}" ip link set "${selected_interface}" type can bitrate "${BITRATE}" restart-ms "${RESTART_MS}"; then
      status="warning"
      reason="set_can_bitrate_failed"
    fi
    if ! run_step "set_up_${selected_interface}" "${sudo_cmd[@]}" ip link set "${selected_interface}" up; then
      status="warning"
      reason="set_can_interface_up_failed"
    fi
  fi
  run_step "show_${selected_interface}" ip -details -statistics link show "${selected_interface}" || true
else
  echo "No can* interface appeared within ${WAIT_SECONDS}s. Plug in the InnoMaker adapter and rerun this helper." | tee -a "${LOG_TXT}"
  status="not_present"
  reason="socketcan_interface_not_found"
fi

python3 - <<'PY' "${LOG_JSON}" "${status}" "${reason}" "${selected_interface}" "${INTERFACE}" "${BITRATE}" "${RESTART_MS}" "${WAIT_SECONDS}" "${usb_line}" "${LOG_TXT}"
import json, sys, time
from pathlib import Path
path, status, reason, selected, requested, bitrate, restart_ms, wait_seconds, usb_line, log_path = sys.argv[1:]
payload = {
    "display_name": "Koala Kan Kommander CAN setup",
    "adapter_target": "InnoMaker USB to CAN Converter kit",
    "requested_interface": requested,
    "selected_interface": selected or None,
    "bitrate": int(bitrate),
    "restart_ms": int(restart_ms),
    "wait_seconds": int(wait_seconds),
    "status": status,
    "reason": reason,
    "firmware_flash_required": False,
    "kernel_driver_expected": "gs_usb/SocketCAN",
    "usb_match": usb_line or None,
    "log_path": log_path,
    "updated_at": time.time(),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(payload, sort_keys=True))
PY

echo "CAN setup artifact: ${LOG_JSON}"

if [[ "${STRICT_CAN_SETUP}" == "1" && "${status}" != "ok" ]]; then
  exit 1
fi
exit 0
