#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

STATUS_PATH="${ESP32_PREFLIGHT_STATUS_PATH:-${ROOT}/logs/preflight/esp32_chip_probe.json}"
ENV_PATH="${ESP32_PREFLIGHT_ENV_PATH:-${ROOT}/logs/preflight/esp32_chip_probe.env}"
PORT="${ESP32_PORT:-${KOALABYTE_ESP32_FACE_PORT:-${KOALABYTE_ESP32_DUALEYE_BY_ID:-}}}"
INSTALL_USER="${SUDO_USER:-${USER:-$(id -un)}}"
INSTALL_HOME="${HOME}"
if command -v getent >/dev/null 2>&1; then
  resolved_home="$(getent passwd "${INSTALL_USER}" | cut -d: -f6 || true)"
  [[ -n "${resolved_home}" ]] && INSTALL_HOME="${resolved_home}"
fi
PLATFORMIO_CORE_DIR="${PLATFORMIO_CORE_DIR:-${INSTALL_HOME}/.platformio}"

mkdir -p "${ROOT}/logs/preflight"

write_status() {
  local status="$1" reason="$2"
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${PORT}" <<'PY'
import json, sys, time
from pathlib import Path
path, status, reason, port = sys.argv[1:]
Path(path).write_text(json.dumps({
    "status": status,
    "reason": reason,
    "port": port,
    "chip": "esp32s3",
    "probe": "esptool chip_id",
    "non_writing": True,
    "updated_at": time.time(),
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

PLATFORMIO_CORE_DIR="${PLATFORMIO_CORE_DIR}" STRICT_ESP32_TOOLS=1 \
  bash scripts/setup_esp32_tools.sh
esptool="$(find "${PLATFORMIO_CORE_DIR}/packages/tool-esptoolpy" -maxdepth 4 -type f \
  \( -name 'esptool.py' -o -name 'esptool' \) -print -quit 2>/dev/null || true)"
[[ -n "${esptool}" ]] || esptool="$(command -v esptool.py || command -v esptool || true)"
[[ -n "${esptool}" && -f "${esptool}" ]] || {
  write_status missing_esptool "An executable esptool file was not found."
  exit 1
}
if [[ "${esptool}" == *.py ]]; then runner=(python3 "${esptool}"); else runner=("${esptool}"); fi

run_esptool_for_port() {
  local candidate="$1"; shift
  if [[ -r "${candidate}" && -w "${candidate}" ]]; then
    "${runner[@]}" "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "${runner[@]}" "$@"
  else
    "${runner[@]}" "$@"
  fi
}

probe_esp32s3() {
  local candidate="$1" output
  [[ -e "${candidate}" ]] || return 1
  output="$(run_esptool_for_port "${candidate}" --chip esp32s3 --port "${candidate}" \
    --before default_reset --after no_reset chip_id 2>&1 || true)"
  grep -Eqi 'ESP32-S3|ESP32S3' <<<"${output}"
}

if [[ -z "${PORT}" ]]; then
  PYTHONPATH=pi-companion python3 scripts/discover_koalabyte_ports.py \
    --profile heltec --output-dir logs/preflight >/dev/null 2>&1 || true
  if [[ -f logs/preflight/koalabyte_ports.env ]]; then
    # shellcheck disable=SC1091
    source logs/preflight/koalabyte_ports.env
    PORT="${ESP32_PORT:-${KOALABYTE_ESP32_FACE_PORT:-${KOALABYTE_ESP32_DUALEYE_BY_ID:-}}}"
  fi
fi

if [[ -n "${PORT}" ]] && ! probe_esp32s3 "${PORT}"; then
  echo "Configured/discovered port did not identify as ESP32-S3: ${PORT}" >&2
  PORT=""
fi

if [[ -z "${PORT}" ]]; then
  shopt -s nullglob
  candidates=(
    /dev/koalabyte-esp32-dualeye
    /dev/serial/by-id/*Espressif*
    /dev/serial/by-id/*ESP32*
    /dev/ttyACM*
    /dev/ttyUSB*
  )
  shopt -u nullglob
  for candidate in "${candidates[@]}"; do
    [[ "${candidate}" == *heltec* ]] && continue
    if probe_esp32s3 "${candidate}"; then
      PORT="${candidate}"
      break
    fi
  done
fi

if [[ -z "${PORT}" || ! -e "${PORT}" ]]; then
  write_status not_found "No serial candidate answered an ESP32-S3 chip_id probe."
  rm -f "${ENV_PATH}"
  echo "ESP32-S3 DualEye preflight failed. Connect it, or hold BOOT while retrying." >&2
  exit 1
fi

probe_esp32s3 "${PORT}" || {
  write_status identity_failed "Final ESP32-S3 chip_id confirmation failed."
  rm -f "${ENV_PATH}"
  exit 1
}

printf 'ESP32_PORT=%q\n' "${PORT}" >"${ENV_PATH}"
printf 'KOALABYTE_ESP32_FACE_PORT=%q\n' "${PORT}" >>"${ENV_PATH}"
write_status ready "ESP32-S3 positively identified with a non-writing chip_id probe."
echo "ESP32-S3 preflight verified: ${PORT}"
