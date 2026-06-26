#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE="${INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE:-auto}"
STRICT_DUALEYE_VOICE_BRIDGE_SERVICE="${STRICT_DUALEYE_VOICE_BRIDGE_SERVICE:-0}"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/pi-companion/.venv/bin/python}"
ESP32_MIC_PORT="${KOALABYTE_ESP32_MIC_PORT:-${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-/dev/koalabyte-esp32-dualeye}}}"
SERVICE_NAME="koalabyte-dualeye-voice-bridge.service"
STATUS_PATH="${REPO_ROOT}/logs/killerkoala/esp32_dualeye_voice_bridge_service_status.json"

usage() {
  cat <<'EOF'
Install/start the KoalaByte ESP32-S3 DualEye built-in mic voice bridge service.

Default behavior is non-failing so the one-shot installer is not blocked if the
ESP32 is not plugged in yet. Set STRICT_DUALEYE_VOICE_BRIDGE_SERVICE=1 to fail
when systemd or service installation is unavailable.

Useful env:
  KOALABYTE_ESP32_MIC_PORT=/dev/koalabyte-esp32-dualeye
  KOALABYTE_ESP32_FACE_PORT=/dev/ttyUSB0
  ESP32_PORT=/dev/ttyUSB0
  INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE=auto|1|0
  STRICT_DUALEYE_VOICE_BRIDGE_SERVICE=1|0
EOF
}

for arg in "$@"; do
  case "${arg}" in
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: ${arg}" >&2
      usage >&2
      exit 2
      ;;
  esac
done

mkdir -p "$(dirname "${STATUS_PATH}")"

write_status() {
  local status="$1"
  local reason="$2"
  python3 - <<'PY' "${STATUS_PATH}" "${status}" "${reason}" "${ESP32_MIC_PORT}" "${SERVICE_NAME}"
import json, sys, time
path, status, reason, port, service = sys.argv[1:]
payload = {
    "status": status,
    "reason": reason,
    "port": port,
    "service": service,
    "required_for_install": False,
    "updated_at": time.time(),
}
open(path, "w", encoding="utf-8").write(json.dumps(payload, indent=2, sort_keys=True))
PY
}

case "${INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE}" in
  0|false|False|no|NO|skip|SKIP)
    echo "Skipping ESP32 DualEye voice bridge service."
    write_status "skipped" "disabled by INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE"
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES)
    ;;
  *)
    echo "Unknown INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE=${INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE}. Use auto, 1, or 0." >&2
    exit 2
    ;;
esac

if ! command -v systemctl >/dev/null 2>&1; then
  write_status "warning" "systemctl not available; run scripts/run_esp32_dualeye_voice_bridge.py manually"
  [[ "${STRICT_DUALEYE_VOICE_BRIDGE_SERVICE}" == "1" ]] && exit 1
  exit 0
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  write_status "warning" "Pi venv Python not found at ${PYTHON_BIN}; run scripts/install_pi.sh first"
  [[ "${STRICT_DUALEYE_VOICE_BRIDGE_SERVICE}" == "1" ]] && exit 1
  exit 0
fi

service_file="/etc/systemd/system/${SERVICE_NAME}"
service_body="[Unit]
Description=KoalaByte ESP32-S3 DualEye built-in mic voice bridge
After=network.target bluetooth.target

[Service]
Type=simple
WorkingDirectory=${REPO_ROOT}
Environment=PYTHONPATH=${REPO_ROOT}/pi-companion
Environment=KOALABYTE_ESP32_MIC_PORT=${ESP32_MIC_PORT}
ExecStart=${PYTHON_BIN} ${REPO_ROOT}/scripts/run_esp32_dualeye_voice_bridge.py --port ${ESP32_MIC_PORT} --seconds 31536000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"

if [[ "${EUID}" -eq 0 ]]; then
  printf '%s' "${service_body}" > "${service_file}"
elif command -v sudo >/dev/null 2>&1; then
  printf '%s' "${service_body}" | sudo tee "${service_file}" >/dev/null
else
  write_status "warning" "not root and sudo unavailable; cannot install systemd service"
  [[ "${STRICT_DUALEYE_VOICE_BRIDGE_SERVICE}" == "1" ]] && exit 1
  exit 0
fi

if [[ "${EUID}" -eq 0 ]]; then
  systemctl daemon-reload || true
  systemctl enable "${SERVICE_NAME}" || true
  systemctl restart "${SERVICE_NAME}" || true
else
  sudo systemctl daemon-reload || true
  sudo systemctl enable "${SERVICE_NAME}" || true
  sudo systemctl restart "${SERVICE_NAME}" || true
fi

write_status "ok" "ESP32 DualEye built-in mic voice bridge service installed; it will wait/restart until the ESP32 serial port is present"
echo "ESP32 DualEye built-in mic voice bridge service installed: ${SERVICE_NAME}"
