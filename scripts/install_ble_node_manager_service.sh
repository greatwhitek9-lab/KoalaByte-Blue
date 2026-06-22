#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="koalabyte-ble-node-manager.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"
ENV_PATH="/etc/default/koalabyte-ble-node-manager"
INSTALL_BLE_NODE_MANAGER_SERVICE="${INSTALL_BLE_NODE_MANAGER_SERVICE:-auto}"
STRICT_BLE_NODE_MANAGER_SERVICE="${STRICT_BLE_NODE_MANAGER_SERVICE:-0}"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/pi-companion/.venv/bin/python}"

if [[ -e /dev/koalabyte-heltec ]]; then
  DEFAULT_HELTEC_PORT="/dev/koalabyte-heltec"
else
  DEFAULT_HELTEC_PORT="/dev/ttyACM0"
fi
HELTEC_RUNTIME_PORT="${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-${DEFAULT_HELTEC_PORT}}}"
ESP32_RUNTIME_PORT="${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-}}"

case "${INSTALL_BLE_NODE_MANAGER_SERVICE}" in
  0|false|False|no|NO|skip|SKIP)
    echo "Skipping KoalaByte BLE node manager service install by request."
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES)
    ;;
  *) echo "Unknown INSTALL_BLE_NODE_MANAGER_SERVICE value: ${INSTALL_BLE_NODE_MANAGER_SERVICE}" >&2; exit 2 ;;
esac

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl not found; cannot install persistent BLE node manager service on this OS." >&2
  [[ "${STRICT_BLE_NODE_MANAGER_SERVICE}" == "1" ]] && exit 1
  exit 0
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  else
    echo "No Python executable found for BLE node manager service." >&2
    [[ "${STRICT_BLE_NODE_MANAGER_SERVICE}" == "1" ]] && exit 1
    exit 0
  fi
fi

if [[ ! -f "${REPO_ROOT}/scripts/run_ble_node_manager.py" ]]; then
  echo "Missing scripts/run_ble_node_manager.py; cannot install BLE node manager service." >&2
  [[ "${STRICT_BLE_NODE_MANAGER_SERVICE}" == "1" ]] && exit 1
  exit 0
fi

if [[ "${EUID}" -eq 0 ]]; then
  sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then
  sudo_cmd=(sudo)
else
  echo "Root or sudo is required to install the systemd service." >&2
  [[ "${STRICT_BLE_NODE_MANAGER_SERVICE}" == "1" ]] && exit 1
  exit 0
fi

mkdir -p "${REPO_ROOT}/logs/ble_nodes" "${REPO_ROOT}/logs/preflight"
chmod +x "${REPO_ROOT}/scripts/run_ble_node_manager_service.sh"
PYTHONPATH="${REPO_ROOT}/pi-companion${PYTHONPATH:+:${PYTHONPATH}}" python3 "${REPO_ROOT}/scripts/discover_koalabyte_ports.py" --profile heltec --output-dir "${REPO_ROOT}/logs/preflight" || true

cat > /tmp/koalabyte-ble-node-manager.env <<ENVEOF
KOALABYTE_HELTEC_USB_PORT=${HELTEC_RUNTIME_PORT}
KOALABYTE_ESP32_FACE_PORT=${ESP32_RUNTIME_PORT}
PYTHON_BIN=${PYTHON_BIN}
KOALABYTE_PORT_ENV_FILE=${REPO_ROOT}/logs/preflight/koalabyte_ports.env
ENVEOF

cat > /tmp/${SERVICE_NAME} <<SERVICEEOF
[Unit]
Description=KoalaByte BLE Node Manager - Heltec T114 primary BLE node
After=network-online.target bluetooth.service systemd-udev-settle.service
Wants=network-online.target bluetooth.service systemd-udev-settle.service

[Service]
Type=simple
WorkingDirectory=${REPO_ROOT}
EnvironmentFile=-${ENV_PATH}
ExecStart=${REPO_ROOT}/scripts/run_ble_node_manager_service.sh
Restart=always
RestartSec=5
StandardOutput=append:${REPO_ROOT}/logs/ble_nodes/service.log
StandardError=append:${REPO_ROOT}/logs/ble_nodes/service.err

[Install]
WantedBy=multi-user.target
SERVICEEOF

"${sudo_cmd[@]}" install -m 0644 /tmp/koalabyte-ble-node-manager.env "${ENV_PATH}"
"${sudo_cmd[@]}" install -m 0644 /tmp/${SERVICE_NAME} "${SERVICE_PATH}"
"${sudo_cmd[@]}" systemctl daemon-reload
"${sudo_cmd[@]}" systemctl enable "${SERVICE_NAME}"
"${sudo_cmd[@]}" systemctl restart "${SERVICE_NAME}"

sleep 1
if "${sudo_cmd[@]}" systemctl is-active --quiet "${SERVICE_NAME}"; then
  echo "KoalaByte BLE node manager service is active."
else
  echo "KoalaByte BLE node manager service was installed but is not active yet. Check logs/ble_nodes/service.err or journalctl -u ${SERVICE_NAME}." >&2
  [[ "${STRICT_BLE_NODE_MANAGER_SERVICE}" == "1" ]] && exit 1
fi
