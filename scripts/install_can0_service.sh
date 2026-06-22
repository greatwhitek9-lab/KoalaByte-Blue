#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE="koalabyte-can0.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE}"
ENV_PATH="/etc/default/koalabyte-can0"
INSTALL_CAN0_SERVICE="${INSTALL_CAN0_SERVICE:-auto}"
STRICT_CAN0_SERVICE="${STRICT_CAN0_SERVICE:-0}"
CAN_INTERFACE="${CAN_INTERFACE:-can0}"
CAN_BITRATE="${CAN_BITRATE:-500000}"
STRICT_CAN_SETUP="${STRICT_CAN_SETUP:-0}"

case "${INSTALL_CAN0_SERVICE}" in
  0|false|False|no|NO|skip|SKIP)
    echo "Skipping KoalaByte CAN service install by request."
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES)
    ;;
  *) echo "Unknown INSTALL_CAN0_SERVICE value: ${INSTALL_CAN0_SERVICE}" >&2; exit 2 ;;
esac

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl not found; cannot install persistent CAN setup service." >&2
  [[ "${STRICT_CAN0_SERVICE}" == "1" ]] && exit 1
  exit 0
fi

if [[ "${EUID}" -eq 0 ]]; then
  sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then
  sudo_cmd=(sudo)
else
  echo "Root or sudo is required to install the CAN setup service." >&2
  [[ "${STRICT_CAN0_SERVICE}" == "1" ]] && exit 1
  exit 0
fi

mkdir -p "${ROOT}/logs/koala_kan_kommander"
chmod +x "${ROOT}/scripts/run_can0_service.sh" "${ROOT}/scripts/setup_can0.sh"

cat > /tmp/koalabyte-can0.env <<ENVEOF
CAN_INTERFACE=${CAN_INTERFACE}
CAN_BITRATE=${CAN_BITRATE}
STRICT_CAN_SETUP=${STRICT_CAN_SETUP}
KOALABYTE_CAN_ENV_FILE=${ROOT}/logs/preflight/koalabyte_ports.env
ENVEOF

cat > /tmp/${SERVICE} <<SERVICEEOF
[Unit]
Description=KoalaByte CAN interface setup for InnoMaker SocketCAN adapter
After=systemd-udev-settle.service network.target
Wants=systemd-udev-settle.service

[Service]
Type=oneshot
WorkingDirectory=${ROOT}
EnvironmentFile=-${ENV_PATH}
ExecStart=${ROOT}/scripts/run_can0_service.sh
RemainAfterExit=yes
StandardOutput=append:${ROOT}/logs/koala_kan_kommander/can0_service.log
StandardError=append:${ROOT}/logs/koala_kan_kommander/can0_service.err

[Install]
WantedBy=multi-user.target
SERVICEEOF

"${sudo_cmd[@]}" install -m 0644 /tmp/koalabyte-can0.env "${ENV_PATH}"
"${sudo_cmd[@]}" install -m 0644 /tmp/${SERVICE} "${SERVICE_PATH}"
"${sudo_cmd[@]}" systemctl daemon-reload
"${sudo_cmd[@]}" systemctl enable "${SERVICE}"
"${sudo_cmd[@]}" systemctl restart "${SERVICE}" || {
  echo "KoalaByte CAN service installed but setup did not complete. Check logs/koala_kan_kommander/can0_service.err." >&2
  [[ "${STRICT_CAN0_SERVICE}" == "1" ]] && exit 1
}

echo "KoalaByte CAN setup service installed: ${SERVICE}"
