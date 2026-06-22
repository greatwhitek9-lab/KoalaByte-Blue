#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERFACE="${CAN_INTERFACE:-can0}"
BITRATE="${CAN_BITRATE:-500000}"
STRICT_CAN_SETUP="${STRICT_CAN_SETUP:-0}"
OUTPUT_DIR="${CAN_SETUP_OUTPUT_DIR:-${REPO_ROOT}/logs/koala_kan_kommander}"

usage() {
  cat <<'EOF'
KoalaByte Blue SocketCAN setup helper for InnoMaker USB-to-CAN

Usage:
  bash scripts/setup_can0.sh
  bash scripts/setup_can0.sh --interface can0 --bitrate 500000
  STRICT_CAN_SETUP=1 bash scripts/setup_can0.sh

Environment:
  CAN_INTERFACE       SocketCAN interface name. Default: can0
  CAN_BITRATE         CAN bitrate. Default: 500000
  STRICT_CAN_SETUP    1 fails if modules/interface setup fails. Default: 0

This helper loads Linux CAN modules, then configures the CAN interface only if it exists.
It does not flash or modify the InnoMaker adapter firmware.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --interface)
      INTERFACE="${2:-}"
      shift 2
      ;;
    --bitrate)
      BITRATE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

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

for module in can can_raw can_dev; do
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

if ! command -v ip >/dev/null 2>&1; then
  echo "ip command not found; cannot configure ${INTERFACE}" | tee -a "${LOG_TXT}"
  status="warning"
  reason="ip_command_not_found"
elif ip link show "${INTERFACE}" >/dev/null 2>&1; then
  run_step "set_down_${INTERFACE}" "${sudo_cmd[@]}" ip link set "${INTERFACE}" down || true
  if ! run_step "set_type_${INTERFACE}" "${sudo_cmd[@]}" ip link set "${INTERFACE}" type can bitrate "${BITRATE}"; then
    status="warning"
    reason="set_can_bitrate_failed"
  fi
  if ! run_step "set_up_${INTERFACE}" "${sudo_cmd[@]}" ip link set up "${INTERFACE}"; then
    status="warning"
    reason="set_can_interface_up_failed"
  fi
  run_step "show_${INTERFACE}" ip -details -statistics link show "${INTERFACE}" || true
else
  echo "${INTERFACE} does not exist yet. Plug in the InnoMaker adapter and rerun this helper." | tee -a "${LOG_TXT}"
  status="not_present"
  reason="socketcan_interface_not_found"
fi

cat > "${LOG_JSON}" <<JSON
{
  "display_name": "Koala Kan Kommander CAN setup",
  "adapter_target": "InnoMaker USB to CAN Converter kit",
  "interface": "${INTERFACE}",
  "bitrate": ${BITRATE},
  "status": "${status}",
  "reason": "${reason}",
  "firmware_flash_required": false,
  "commands_requested": [
    "sudo modprobe can",
    "sudo modprobe can_raw",
    "sudo modprobe can_dev",
    "sudo ip link set ${INTERFACE} type can bitrate ${BITRATE}",
    "sudo ip link set up ${INTERFACE}",
    "ip link show ${INTERFACE}"
  ],
  "log_path": "${LOG_TXT}"
}
JSON

echo "CAN setup artifact: ${LOG_JSON}"

if [[ "${STRICT_CAN_SETUP}" == "1" && "${status}" != "ok" ]]; then
  exit 1
fi
exit 0
