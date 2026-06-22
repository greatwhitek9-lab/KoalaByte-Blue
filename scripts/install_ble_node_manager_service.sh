#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE="koalabyte-ble-node-manager.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE}"
ENV_PATH="/etc/default/koalabyte-ble-node-manager"
INSTALL_SERVICE="${INSTALL_BLE_NODE_MANAGER_SERVICE:-auto}"
STRICT_SERVICE="${STRICT_BLE_NODE_MANAGER_SERVICE:-0}"
PY="${PYTHON_BIN:-${ROOT}/pi-companion/.venv/bin/python}"
PORT="${KOALABYTE_NRF_BLE_PORT:-${NRF_BLE_PORT:-/dev/ttyACM0}}"
ESP="${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-}}"
PI_BLUEZ="${KOALABYTE_PI_BLUEZ_NODE:-1}"

case "${INSTALL_SERVICE}" in
  0|false|False|no|NO|skip|SKIP)
    echo "Skipping KoalaByte BLE node manager service install by request."
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES)
    ;;
  *)
    echo "Unknown INSTALL_BLE_NODE_MANAGER_SERVICE value: ${INSTALL_SERVICE}" >&2
    exit 2
    ;;
esac

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl not found; cannot install persistent BLE node manager service." >&2
  [[ "${STRICT_SERVICE}" == "1" ]] && exit 1
  exit 0
fi

if [[ ! -x "${PY}" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PY="$(command -v python3)"
  else
    echo "No Python executable found for BLE node manager service." >&2
    [[ "${STRICT_SERVICE}" == "1" ]] && exit 1
    exit 0
  fi
fi

if [[ ! -f "${ROOT}/scripts/run_ble_node_manager.py" ]]; then
  echo "Missing scripts/run_ble_node_manager.py; cannot install BLE node manager service." >&2
  [[ "${STRICT_SERVICE}" == "1" ]] && exit 1
  exit 0
fi

if [[ "${EUID}" -eq 0 ]]; then
  sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then
  sudo_cmd=(sudo)
else
  echo "Root or sudo is required to install the systemd service." >&2
  [[ "${STRICT_SERVICE}" == "1" ]] && exit 1
  exit 0
fi

mkdir -p "${ROOT}/logs/ble_nodes"
chmod +x "${ROOT}/scripts/run_ble_node_manager_service.sh"

cat > /tmp/koalabyte-ble-node-manager.env <<ENVEOF
KOALABYTE_NRF_BLE_PORT=${PORT}
KOALABYTE_ESP32_FACE_PORT=${ESP}
KOALABYTE_PI_BLUEZ_NODE=${PI_BLUEZ}
PYTHON_BIN=${PY}
ENVEOF

cat > /tmp/${SERVICE} <<SERVICEEOF
[Unit]
Description=KoalaByte BLE Node Manager - nRF52840 Dongle primary BLE node
After=network-online.target dev-ttyACM0.device bluetooth.service
Wants=network-online.target bluetooth.service

[Service]
Type=simple
WorkingDirectory=${ROOT}
EnvironmentFile=-${ENV_PATH}
ExecStart=${ROOT}/scripts/run_ble_node_manager_service.sh
Restart=always
RestartSec=5
StandardOutput=append:${ROOT}/logs/ble_nodes/service.log
StandardError=append:${ROOT}/logs/ble_nodes/service.err

[Install]
WantedBy=multi-user.target
SERVICEEOF

"${sudo_cmd[@]}" install -m 0644 /tmp/koalabyte-ble-node-manager.env "${ENV_PATH}"
"${sudo_cmd[@]}" install -m 0644 /tmp/${SERVICE} "${SERVICE_PATH}"
"${sudo_cmd[@]}" systemctl daemon-reload
"${sudo_cmd[@]}" systemctl enable "${SERVICE}"
"${sudo_cmd[@]}" systemctl restart "${SERVICE}"

sleep 1
if "${sudo_cmd[@]}" systemctl is-active --quiet "${SERVICE}"; then
  echo "KoalaByte BLE node manager service is active."
else
  echo "KoalaByte BLE node manager service installed but is not active yet. Check logs/ble_nodes/service.err or journalctl -u ${SERVICE}." >&2
  [[ "${STRICT_SERVICE}" == "1" ]] && exit 1
fi
