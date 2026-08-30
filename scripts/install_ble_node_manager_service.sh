#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE="koalabyte-ble-node-manager.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE}"
ENV_PATH="/etc/default/koalabyte-ble-node-manager"
INSTALL_SERVICE="${INSTALL_BLE_NODE_MANAGER_SERVICE:-auto}"
STRICT_SERVICE="${STRICT_BLE_NODE_MANAGER_SERVICE:-0}"
PY="${PYTHON_BIN:-${ROOT}/pi-companion/.venv/bin/python}"
SERVICE_USER="${KOALABYTE_SERVICE_USER:-${SUDO_USER:-${USER:-pi}}}"
SERVICE_GROUP="${KOALABYTE_SERVICE_GROUP:-}"
SERIAL_BUS_DIR="${KOALABYTE_SERIAL_BUS_DIR:-${ROOT}/logs/runtime/serial_bus}"

is_serial_device() {
  [[ -n "${1:-}" && -c "${1}" ]]
}

if is_serial_device /dev/koalabyte-heltec; then
  DEFAULT_PRIMARY_PORT="/dev/koalabyte-heltec"
elif is_serial_device /dev/koalabyte-heltec-t114; then
  DEFAULT_PRIMARY_PORT="/dev/koalabyte-heltec-t114"
elif is_serial_device /dev/koalabyte-nrf52840; then
  DEFAULT_PRIMARY_PORT="/dev/koalabyte-nrf52840"
else
  DEFAULT_PRIMARY_PORT="/dev/koalabyte-heltec"
fi
PRIMARY_PORT="${KOALABYTE_PRIMARY_BLE_PORT:-${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-${KOALABYTE_NRF_BLE_PORT:-${NRF_BLE_PORT:-${DEFAULT_PRIMARY_PORT}}}}}}"
if ! is_serial_device "${PRIMARY_PORT}" && is_serial_device "${DEFAULT_PRIMARY_PORT}"; then
  echo "Ignoring invalid configured Heltec serial path during service install: ${PRIMARY_PORT}" >&2
  PRIMARY_PORT="${DEFAULT_PRIMARY_PORT}"
fi
ESP="${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-/dev/koalabyte-esp32-dualeye}}"
PI_BLUEZ="${KOALABYTE_PI_BLUEZ_NODE:-1}"

case "${INSTALL_SERVICE}" in
  0|false|False|no|NO|skip|SKIP) echo "Skipping KoalaByte BLE node manager service."; exit 0 ;;
  auto|AUTO|1|true|True|yes|YES) ;;
  *) echo "Unknown INSTALL_BLE_NODE_MANAGER_SERVICE=${INSTALL_SERVICE}" >&2; exit 2 ;;
esac

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl not found; cannot install BLE node manager service." >&2
  [[ "${STRICT_SERVICE}" == "1" ]] && exit 1
  exit 0
fi
if [[ ! -x "${PY}" ]]; then PY="$(command -v python3 || true)"; fi
if [[ -z "${PY}" || ! -x "${PY}" ]]; then
  echo "No Python executable found for BLE node manager service." >&2
  [[ "${STRICT_SERVICE}" == "1" ]] && exit 1
  exit 0
fi
[[ -f "${ROOT}/scripts/run_ble_node_manager.py" ]] || {
  echo "Missing scripts/run_ble_node_manager.py" >&2
  exit 1
}
id "${SERVICE_USER}" >/dev/null 2>&1 || {
  echo "Service user does not exist: ${SERVICE_USER}" >&2
  exit 1
}
[[ -n "${SERVICE_GROUP}" ]] || SERVICE_GROUP="$(id -gn "${SERVICE_USER}")"

if [[ "${EUID}" -eq 0 ]]; then sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then sudo_cmd=(sudo)
else
  echo "Root or sudo is required to install the systemd service." >&2
  [[ "${STRICT_SERVICE}" == "1" ]] && exit 1
  exit 0
fi

mkdir -p "${ROOT}/logs/ble_nodes" "${ROOT}/logs/preflight" "${SERIAL_BUS_DIR}"
PYTHONPATH="${ROOT}/pi-companion${PYTHONPATH:+:${PYTHONPATH}}" python3 \
  "${ROOT}/scripts/discover_koalabyte_ports.py" --profile heltec \
  --output-dir "${ROOT}/logs/preflight" || true
"${sudo_cmd[@]}" chown -R "${SERVICE_USER}:${SERVICE_GROUP}" \
  "${ROOT}/logs/ble_nodes" "${ROOT}/logs/preflight" "${SERIAL_BUS_DIR}" || true

env_tmp="$(mktemp)"
cat >"${env_tmp}" <<ENVEOF
KOALABYTE_PRIMARY_BLE_PORT=${PRIMARY_PORT}
KOALABYTE_HELTEC_USB_PORT=${PRIMARY_PORT}
KOALABYTE_ESP32_FACE_PORT=${ESP}
KOALABYTE_PI_BLUEZ_NODE=${PI_BLUEZ}
KOALABYTE_BLE_MANAGER_OWNS_ESP32=0
KOALABYTE_BLE_ROLE_CHECK_SECONDS=30
KOALABYTE_SERIAL_BUS_DIR=${SERIAL_BUS_DIR}
PYTHON_BIN=${PY}
KOALABYTE_PORT_ENV_FILE=${ROOT}/logs/preflight/koalabyte_ports.env
ENVEOF

service_tmp="$(mktemp)"
cat >"${service_tmp}" <<SERVICEEOF
[Unit]
Description=KoalaByte BLE Node Manager - exclusive Heltec serial owner
After=network-online.target bluetooth.service systemd-udev-settle.service
Wants=network-online.target bluetooth.service systemd-udev-settle.service
StartLimitIntervalSec=0

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${ROOT}
Environment=PYTHONPATH=${ROOT}/pi-companion
Environment=PATH=${ROOT}/pi-companion/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=KOALABYTE_SERIAL_BUS_DIR=${SERIAL_BUS_DIR}
EnvironmentFile=-${ENV_PATH}
ExecStart=/usr/bin/bash ${ROOT}/scripts/run_ble_node_manager_service.sh
Restart=always
RestartSec=5
TimeoutStopSec=15
StandardOutput=append:${ROOT}/logs/ble_nodes/service.log
StandardError=append:${ROOT}/logs/ble_nodes/service.err

[Install]
WantedBy=multi-user.target
SERVICEEOF

"${sudo_cmd[@]}" install -m 0644 "${env_tmp}" "${ENV_PATH}"
"${sudo_cmd[@]}" install -m 0644 "${service_tmp}" "${SERVICE_PATH}"
rm -f "${env_tmp}" "${service_tmp}"
"${sudo_cmd[@]}" systemctl daemon-reload
"${sudo_cmd[@]}" systemctl reset-failed "${SERVICE}" >/dev/null 2>&1 || true
"${sudo_cmd[@]}" systemctl enable "${SERVICE}"
"${sudo_cmd[@]}" systemctl restart "${SERVICE}" || true

sleep 1
if "${sudo_cmd[@]}" systemctl is-active --quiet "${SERVICE}"; then
  echo "KoalaByte BLE node manager is active for ${SERVICE_USER}:${SERVICE_GROUP}."
else
  echo "BLE node manager is waiting for the Heltec or restarting; final health gate will verify it." >&2
  [[ "${STRICT_SERVICE}" == "1" ]] && exit 1
fi
