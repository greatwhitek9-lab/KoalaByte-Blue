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

wait_for_serial_device() {
  local path="$1"
  local timeout="${2:-15}"
  local deadline=$(( $(date +%s) + timeout ))
  while (( $(date +%s) < deadline )); do
    if is_serial_device "${path}"; then
      return 0
    fi
    sleep 0.25
  done
  is_serial_device "${path}"
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
REENUMERATE_WAIT_SECONDS="${KOALABYTE_T114_REENUMERATE_WAIT_SECONDS:-15}"

# A UF2 handoff or normal T114 reset temporarily removes the USB CDC node.
# Keep trusting only the configured stable KoalaByte alias, but give udev time
# to recreate it before falling back or asking systemd to retry.
if [[ -n "${CONFIGURED_PRIMARY_PORT}" ]] && ! is_serial_device "${CONFIGURED_PRIMARY_PORT}"; then
  case "${CONFIGURED_PRIMARY_PORT}" in
    /dev/koalabyte-heltec|/dev/koalabyte-heltec-t114|/dev/koalabyte-nrf52840)
      echo "Waiting up to ${REENUMERATE_WAIT_SECONDS}s for T114 serial re-enumeration: ${CONFIGURED_PRIMARY_PORT}" >&2
      wait_for_serial_device "${CONFIGURED_PRIMARY_PORT}" "${REENUMERATE_WAIT_SECONDS}" || true
      ;;
  esac
fi

if is_serial_device "${CONFIGURED_PRIMARY_PORT}"; then
  PRIMARY_PORT="${CONFIGURED_PRIMARY_PORT}"
else
  if [[ -n "${CONFIGURED_PRIMARY_PORT}" ]]; then
    echo "Ignoring invalid Heltec serial path from runtime environment: ${CONFIGURED_PRIMARY_PORT}" >&2
  fi
  if is_serial_device /dev/koalabyte-heltec; then
    DEFAULT_PRIMARY_PORT="/dev/koalabyte-heltec"
  elif is_serial_device /dev/koalabyte-heltec-t114; then
    DEFAULT_PRIMARY_PORT="/dev/koalabyte-heltec-t114"
  else
    DEFAULT_PRIMARY_PORT=""
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
