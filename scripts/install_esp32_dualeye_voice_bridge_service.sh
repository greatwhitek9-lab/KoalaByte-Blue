#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE="${INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE:-auto}"
STRICT_DUALEYE_VOICE_BRIDGE_SERVICE="${STRICT_DUALEYE_VOICE_BRIDGE_SERVICE:-0}"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/pi-companion/.venv/bin/python}"
ESP32_MIC_PORT="${KOALABYTE_ESP32_MIC_PORT:-${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-/dev/koalabyte-esp32-dualeye}}}"
SERVICE_NAME="koalabyte-dualeye-voice-bridge.service"
STATUS_PATH="${REPO_ROOT}/logs/killerkoala/esp32_dualeye_voice_bridge_service_status.json"
SERVICE_USER="${KOALABYTE_SERVICE_USER:-${SUDO_USER:-${USER:-pi}}}"
SERVICE_GROUP="${KOALABYTE_SERVICE_GROUP:-${SERVICE_USER}}"

usage() {
  cat <<'EOF'
Install/start the KoalaByte ESP32-S3 DualEye voice bridge service.

The service is non-fatal by default when the ESP32 is disconnected. It runs as
KOALABYTE_SERVICE_USER and restarts until the stable serial alias is present.
EOF
}

for arg in "$@"; do
  case "${arg}" in
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: ${arg}" >&2; usage >&2; exit 2 ;;
  esac
done

mkdir -p "$(dirname "${STATUS_PATH}")"

write_status() {
  local status="$1" reason="$2"
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${ESP32_MIC_PORT}" "${SERVICE_NAME}" "${SERVICE_USER}" <<'PY'
import json, sys, time
path, status, reason, port, service, user = sys.argv[1:]
payload = {
    "status": status,
    "reason": reason,
    "port": port,
    "service": service,
    "service_user": user,
    "required_for_install": False,
    "updated_at": time.time(),
}
open(path, "w", encoding="utf-8").write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY
}

case "${INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE}" in
  0|false|False|no|NO|skip|SKIP)
    echo "Skipping ESP32 DualEye voice bridge service."
    write_status "skipped" "disabled by configuration"
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES) ;;
  *) echo "Unknown INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE=${INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE}" >&2; exit 2 ;;
esac

if ! command -v systemctl >/dev/null 2>&1; then
  write_status "warning" "systemctl unavailable"
  [[ "${STRICT_DUALEYE_VOICE_BRIDGE_SERVICE}" == "1" ]] && exit 1
  exit 0
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi
if [[ -z "${PYTHON_BIN}" || ! -x "${PYTHON_BIN}" ]]; then
  write_status "warning" "Python runtime unavailable"
  [[ "${STRICT_DUALEYE_VOICE_BRIDGE_SERVICE}" == "1" ]] && exit 1
  exit 0
fi

id "${SERVICE_USER}" >/dev/null 2>&1 || { write_status "error" "service user missing"; exit 1; }

if [[ "${EUID}" -eq 0 ]]; then
  sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then
  sudo_cmd=(sudo)
else
  write_status "warning" "root or sudo required"
  [[ "${STRICT_DUALEYE_VOICE_BRIDGE_SERVICE}" == "1" ]] && exit 1
  exit 0
fi

"${sudo_cmd[@]}" chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${REPO_ROOT}/logs/killerkoala" || true

service_file="/etc/systemd/system/${SERVICE_NAME}"
cat > /tmp/${SERVICE_NAME} <<SERVICEEOF
[Unit]
Description=KoalaByte ESP32-S3 DualEye voice bridge
After=network-online.target bluetooth.target systemd-udev-settle.service
Wants=network-online.target systemd-udev-settle.service

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${REPO_ROOT}
Environment=PYTHONPATH=${REPO_ROOT}/pi-companion
Environment=KOALABYTE_ESP32_MIC_PORT=${ESP32_MIC_PORT}
ExecStart=${PYTHON_BIN} ${REPO_ROOT}/scripts/run_esp32_dualeye_voice_bridge.py --port ${ESP32_MIC_PORT} --seconds 31536000
Restart=always
RestartSec=5
StandardOutput=append:${REPO_ROOT}/logs/killerkoala/dualeye_voice_bridge.log
StandardError=append:${REPO_ROOT}/logs/killerkoala/dualeye_voice_bridge.err

[Install]
WantedBy=multi-user.target
SERVICEEOF

"${sudo_cmd[@]}" install -m 0644 /tmp/${SERVICE_NAME} "${service_file}"
"${sudo_cmd[@]}" systemctl daemon-reload
"${sudo_cmd[@]}" systemctl enable "${SERVICE_NAME}" || true
"${sudo_cmd[@]}" systemctl restart "${SERVICE_NAME}" || true

write_status "ok" "ESP32 DualEye voice bridge installed for ${SERVICE_USER}; service waits/restarts until the serial alias is present"
echo "ESP32 DualEye voice bridge service installed: ${SERVICE_NAME}"
