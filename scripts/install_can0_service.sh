#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE="koalabyte-can0.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE}"
ENV_PATH="/etc/default/koalabyte-can0"
UDEV_RULE_PATH="/etc/udev/rules.d/80-koalabyte-can-hotplug.rules"
INSTALL_CAN0_SERVICE="${INSTALL_CAN0_SERVICE:-auto}"
STRICT_CAN0_SERVICE="${STRICT_CAN0_SERVICE:-0}"
CAN_INTERFACE="${CAN_INTERFACE:-can0}"
CAN_BITRATE="${CAN_BITRATE:-500000}"
CAN_RESTART_MS="${CAN_RESTART_MS:-100}"
CAN_WAIT_SECONDS="${CAN_WAIT_SECONDS:-30}"
STRICT_CAN_SETUP="${STRICT_CAN_SETUP:-0}"
SERVICE_USER="${KOALABYTE_SERVICE_USER:-${SUDO_USER:-${USER:-pi}}}"
SERVICE_GROUP="${KOALABYTE_SERVICE_GROUP:-${SERVICE_USER}}"
LOG_DIR="${ROOT}/logs/koala_kan_kommander"

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

if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
  echo "KoalaByte CAN service user does not exist: ${SERVICE_USER}" >&2
  [[ "${STRICT_CAN0_SERVICE}" == "1" ]] && exit 1
  SERVICE_USER="${SUDO_USER:-${USER:-pi}}"
  SERVICE_GROUP="${SERVICE_USER}"
fi

"${sudo_cmd[@]}" install -d -m 0775 -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" "${LOG_DIR}"
"${sudo_cmd[@]}" touch "${LOG_DIR}/can0_service.log" "${LOG_DIR}/can0_service.err"
"${sudo_cmd[@]}" chown "${SERVICE_USER}:${SERVICE_GROUP}" "${LOG_DIR}/can0_service.log" "${LOG_DIR}/can0_service.err"
"${sudo_cmd[@]}" chmod 0664 "${LOG_DIR}/can0_service.log" "${LOG_DIR}/can0_service.err"
chmod +x "${ROOT}/scripts/run_can0_service.sh" "${ROOT}/scripts/setup_can0.sh"

cat > /tmp/koalabyte-can0.env <<ENVEOF
CAN_INTERFACE=${CAN_INTERFACE}
CAN_BITRATE=${CAN_BITRATE}
CAN_RESTART_MS=${CAN_RESTART_MS}
CAN_WAIT_SECONDS=${CAN_WAIT_SECONDS}
STRICT_CAN_SETUP=${STRICT_CAN_SETUP}
KOALABYTE_SERVICE_USER=${SERVICE_USER}
KOALABYTE_SERVICE_GROUP=${SERVICE_GROUP}
CAN_SETUP_OUTPUT_DIR=${LOG_DIR}
KOALABYTE_CAN_ENV_FILE=${ROOT}/logs/preflight/koalabyte_ports.env
ENVEOF

cat > /tmp/${SERVICE} <<SERVICEEOF
[Unit]
Description=KoalaByte CAN interface setup for InnoMaker SocketCAN adapter
Documentation=https://github.com/INNO-MAKER/usb2can
After=systemd-udev-settle.service
Wants=systemd-udev-settle.service

[Service]
Type=oneshot
WorkingDirectory=${ROOT}
EnvironmentFile=-${ENV_PATH}
ExecStart=${ROOT}/scripts/run_can0_service.sh
TimeoutStartSec=$((CAN_WAIT_SECONDS + 20))
RemainAfterExit=no
StandardOutput=append:${LOG_DIR}/can0_service.log
StandardError=append:${LOG_DIR}/can0_service.err

[Install]
WantedBy=multi-user.target
SERVICEEOF

cat > /tmp/80-koalabyte-can-hotplug.rules <<'RULEEOF'
# Re-run the idempotent KoalaByte SocketCAN setup whenever a Linux can* network
# interface appears. This is vendor-neutral and works with one- or two-channel
# InnoMaker adapters exposed by the kernel SocketCAN driver.
ACTION=="add", SUBSYSTEM=="net", KERNEL=="can*", TAG+="systemd", ENV{SYSTEMD_WANTS}+="koalabyte-can0.service"
RULEEOF

"${sudo_cmd[@]}" install -m 0644 /tmp/koalabyte-can0.env "${ENV_PATH}"
"${sudo_cmd[@]}" install -m 0644 /tmp/${SERVICE} "${SERVICE_PATH}"
"${sudo_cmd[@]}" install -m 0644 /tmp/80-koalabyte-can-hotplug.rules "${UDEV_RULE_PATH}"
"${sudo_cmd[@]}" systemctl daemon-reload
if command -v udevadm >/dev/null 2>&1; then
  "${sudo_cmd[@]}" udevadm control --reload-rules
  "${sudo_cmd[@]}" udevadm trigger --subsystem-match=net || true
fi
"${sudo_cmd[@]}" systemctl enable "${SERVICE}"
"${sudo_cmd[@]}" systemctl restart "${SERVICE}" || {
  echo "KoalaByte CAN service installed but setup did not complete. The service will run again when a can* interface is hot-plugged." >&2
  echo "Check logs/koala_kan_kommander/can0_service.err and can0_service.log." >&2
  [[ "${STRICT_CAN0_SERVICE}" == "1" ]] && exit 1
}

# systemd runs the setup as root, but operators also run setup_can0.sh directly.
# Restore shared log ownership after the initial service start so both paths work.
"${sudo_cmd[@]}" chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${LOG_DIR}"
"${sudo_cmd[@]}" chmod -R u+rwX,g+rwX "${LOG_DIR}"

echo "KoalaByte CAN setup service installed: ${SERVICE}"
echo "SocketCAN hot-plug rule installed: ${UDEV_RULE_PATH}"
echo "CAN logs are writable by ${SERVICE_USER}:${SERVICE_GROUP}: ${LOG_DIR}"