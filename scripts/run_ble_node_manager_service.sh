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

is_serial_device() {
  [[ -n "${1:-}" && -c "${1}" ]]
}

if is_serial_device /dev/koalabyte-heltec; then
  DEFAULT_PRIMARY_PORT="/dev/koalabyte-heltec"
elif is_serial_device /dev/koalabyte-heltec-t114; then
  DEFAULT_PRIMARY_PORT="/dev/koalabyte-heltec-t114"
else
  # Never guess ttyACM0/ttyUSB0: either may be the ESP32 serial owner.
  DEFAULT_PRIMARY_PORT=""
fi

CONFIGURED_PRIMARY_PORT="${KOALABYTE_PRIMARY_BLE_PORT:-${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-${KOALABYTE_NRF_BLE_PORT:-${NRF_BLE_PORT:-}}}}}"
if is_serial_device "${CONFIGURED_PRIMARY_PORT}"; then
  PRIMARY_PORT="${CONFIGURED_PRIMARY_PORT}"
else
  if [[ -n "${CONFIGURED_PRIMARY_PORT}" ]]; then
    echo "Ignoring invalid Heltec serial path from runtime environment: ${CONFIGURED_PRIMARY_PORT}" >&2
  fi
  PRIMARY_PORT="${DEFAULT_PRIMARY_PORT}"
fi

ESP="${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-}}"
mkdir -p "${ROOT}/logs/ble_nodes"

args=("${ROOT}/scripts/run_ble_node_manager.py" --duration 0 --primary-port "${PRIMARY_PORT}" --log-dir "${ROOT}/logs/ble_nodes")

# The DualEye voice bridge owns the ESP32 serial port in production and performs
# Pi/ESP32 BLE role election over that connection. Direct ownership here remains
# available only for explicit manual diagnostics.
if [[ "${KOALABYTE_BLE_MANAGER_OWNS_ESP32:-0}" == "1" && -n "${ESP}" ]]; then
  args+=(--esp32-port "${ESP}")
fi
if [[ "${KOALABYTE_PI_BLUEZ_NODE:-1}" == "0" ]]; then
  args+=(--no-pi-bluez)
fi

exec "${PY}" "${args[@]}"
