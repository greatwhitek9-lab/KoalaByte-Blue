#!/usr/bin/env bash
set -euo pipefail

INTERFACE="${VCAN_INTERFACE:-vcan0}"
STRICT_VCAN_SETUP="${STRICT_VCAN_SETUP:-0}"
LOG_DIR="logs/koala_kan_kommander"
mkdir -p "${LOG_DIR}"

usage() {
  cat <<'EOF'
KoalaByte virtual CAN setup helper

Usage:
  bash scripts/setup_vcan0.sh
  VCAN_INTERFACE=vcan0 bash scripts/setup_vcan0.sh

This creates a local-only virtual CAN interface for Koala Kan software tests without physical CAN hardware.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --interface) INTERFACE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ "${EUID}" -eq 0 ]]; then
  sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then
  sudo_cmd=(sudo)
else
  echo "Root or sudo is required to create ${INTERFACE}." >&2
  [[ "${STRICT_VCAN_SETUP}" == "1" ]] && exit 1
  exit 0
fi

if ! command -v ip >/dev/null 2>&1; then
  echo "ip command missing; install iproute2." >&2
  [[ "${STRICT_VCAN_SETUP}" == "1" ]] && exit 1
  exit 0
fi

"${sudo_cmd[@]}" modprobe vcan || true
if ! ip link show "${INTERFACE}" >/dev/null 2>&1; then
  "${sudo_cmd[@]}" ip link add dev "${INTERFACE}" type vcan
fi
"${sudo_cmd[@]}" ip link set up "${INTERFACE}"
ip -details link show "${INTERFACE}" | tee "${LOG_DIR}/${INTERFACE}_setup.log"
cat > "${LOG_DIR}/${INTERFACE}_setup.json" <<JSON
{
  "interface": "${INTERFACE}",
  "type": "vcan",
  "purpose": "Koala Kan local software self-test without physical CAN hardware",
  "setup_complete": true
}
JSON
