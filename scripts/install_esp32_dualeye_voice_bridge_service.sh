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
KILLERKOALA_LLM_MODEL="${KILLERKOALA_LLM_MODEL:-killerkoala-tinyllama:latest}"
KILLERKOALA_OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
KILLERKOALA_TTS_VOICE="${KILLERKOALA_TTS_VOICE:-en-AU-WilliamNeural}"
KILLERKOALA_ENV_DIR="${KILLERKOALA_ENV_DIR:-/etc/koalabyte-blue}"
KILLERKOALA_ENV_FILE="${KILLERKOALA_ENV_FILE:-${KILLERKOALA_ENV_DIR}/killerkoala.env}"

usage() {
  cat <<'EOF_USAGE'
Install/start the KoalaByte ESP32-S3 DualEye voice bridge service.

The Waveshare handles its saved wake/basic vocabulary locally. The service owns
Pi execution, TinyLlama conversation/web research, William Australian TTS, and
synchronized DualEye/T114 expression animation. It restarts until the stable
ESP32 serial alias is present.

Optional private environment file:
  /etc/koalabyte-blue/killerkoala.env

Supported entries include:
  BRAVE_SEARCH_API_KEY=...
  KILLERKOALA_WEB_SEARCH=auto|always|off
  KILLERKOALA_DIALOGUE_TURNS=4
EOF_USAGE
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
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${ESP32_MIC_PORT}" "${SERVICE_NAME}" "${SERVICE_USER}" "${KILLERKOALA_LLM_MODEL}" "${KILLERKOALA_TTS_VOICE}" "${KILLERKOALA_ENV_FILE}" <<'PY'
import json, sys, time
path, status, reason, port, service, user, model, voice, env_file = sys.argv[1:]
payload = {
    "status": status,
    "reason": reason,
    "port": port,
    "service": service,
    "service_user": user,
    "waveshare_local_vocabulary_first": True,
    "tinyllama_fallback_model": model,
    "tts_voice_backend": voice,
    "web_search_mode": "auto_when_internet_available",
    "private_environment_file": env_file,
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
"${sudo_cmd[@]}" install -d -m 0750 "${KILLERKOALA_ENV_DIR}"
if [[ ! -f "${KILLERKOALA_ENV_FILE}" ]]; then
  cat >/tmp/killerkoala.env <<'ENVEOF'
# KoalaByte Blue private KillerKoala runtime settings.
# Add a Brave Search API key for broader current web results. Keyless
# DuckDuckGo Instant Answer and Wikipedia fallback remain available.
KILLERKOALA_WEB_SEARCH=auto
KILLERKOALA_DIALOGUE_TURNS=4
# BRAVE_SEARCH_API_KEY=
ENVEOF
  "${sudo_cmd[@]}" install -m 0600 /tmp/killerkoala.env "${KILLERKOALA_ENV_FILE}"
fi

service_file="/etc/systemd/system/${SERVICE_NAME}"
cat > /tmp/${SERVICE_NAME} <<SERVICEEOF
[Unit]
Description=KoalaByte local-vocabulary-first TinyLlama voice and expression bridge
After=network-online.target bluetooth.target systemd-udev-settle.service ollama.service
Wants=network-online.target systemd-udev-settle.service ollama.service

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${REPO_ROOT}
Environment=PYTHONPATH=${REPO_ROOT}/pi-companion
Environment=PATH=${REPO_ROOT}/pi-companion/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=KOALABYTE_ESP32_MIC_PORT=${ESP32_MIC_PORT}
Environment=KILLERKOALA_LLM_MODE=tinyllama
Environment=KILLERKOALA_LLM_MODEL=${KILLERKOALA_LLM_MODEL}
Environment=OLLAMA_HOST=${KILLERKOALA_OLLAMA_HOST}
Environment=KILLERKOALA_TTS_VOICE=${KILLERKOALA_TTS_VOICE}
Environment=KILLERKOALA_WEB_SEARCH=auto
EnvironmentFile=-${KILLERKOALA_ENV_FILE}
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

write_status "ok" "Waveshare local vocabulary, TinyLlama fallback, web research, Australian TTS, and tone-synced display bridge installed for ${SERVICE_USER}"
echo "ESP32 DualEye voice bridge service installed: ${SERVICE_NAME}"
