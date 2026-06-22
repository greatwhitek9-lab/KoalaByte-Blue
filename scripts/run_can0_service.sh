#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

ENV_FILE="${KOALABYTE_CAN_ENV_FILE:-logs/preflight/koalabyte_ports.env}"
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

CAN_INTERFACE="${CAN_INTERFACE:-can0}"
CAN_BITRATE="${CAN_BITRATE:-500000}"
STRICT_CAN_SETUP="${STRICT_CAN_SETUP:-0}"

exec bash scripts/setup_can0.sh --interface "${CAN_INTERFACE}" --bitrate "${CAN_BITRATE}"
