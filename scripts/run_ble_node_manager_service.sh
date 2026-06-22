#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON_BIN:-${ROOT}/pi-companion/.venv/bin/python}"
if [[ ! -x "${PY}" ]]; then
  PY="$(command -v python3)"
fi

export PYTHONPATH="${ROOT}/pi-companion${PYTHONPATH:+:${PYTHONPATH}}"
ENV_FILE="${KOALABYTE_PORT_ENV_FILE:-${ROOT}/logs/preflight/koalabyte_ports.env}"
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

if [[ -e /dev/koalabyte-nrf-ble ]]; then
  DEFAULT_NRF_PORT="/dev/koalabyte-nrf-ble"
else
  DEFAULT_NRF_PORT="/dev/ttyACM0"
fi

PORT="${KOALABYTE_NRF_BLE_PORT:-${NRF_BLE_PORT:-${DEFAULT_NRF_PORT}}}"
ESP="${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-}}"
mkdir -p "${ROOT}/logs/ble_nodes"

args=("${ROOT}/scripts/run_ble_node_manager.py" --duration 0 --dongle-port "${PORT}" --log-dir "${ROOT}/logs/ble_nodes")
if [[ -n "${ESP}" ]]; then
  args+=(--esp32-port "${ESP}")
fi
if [[ "${KOALABYTE_PI_BLUEZ_NODE:-1}" == "0" ]]; then
  args+=(--no-pi-bluez)
fi

exec "${PY}" "${args[@]}"
