#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

BUNDLE_DIR="${KOALABYTE_FIRMWARE_BUNDLE_DIR:-${ROOT}/releases/koalabyte-blue-current}"
ESP32_DIR="${BUNDLE_DIR}/esp32"
STATUS_PATH="${ESP32_FLASH_STATUS_PATH:-${ROOT}/logs/deployment/esp32_flash_status.json}"
PORT="${ESP32_PORT:-${KOALABYTE_ESP32_FACE_PORT:-${KOALABYTE_ESP32_DUALEYE_BY_ID:-}}}"
BAUD="${ESP32_UPLOAD_BAUD:-460800}"
FALLBACK_BAUD="${ESP32_UPLOAD_FALLBACK_BAUD:-115200}"
WAIT_SECONDS="${ESP32_FLASH_WAIT_SECONDS:-45}"
CHECK_ONLY=0

INSTALL_USER="${SUDO_USER:-${USER:-$(id -un)}}"
INSTALL_HOME="${HOME}"
if command -v getent >/dev/null 2>&1; then
  resolved_home="$(getent passwd "${INSTALL_USER}" | cut -d: -f6 || true)"
  [[ -n "${resolved_home}" ]] && INSTALL_HOME="${resolved_home}"
fi
PLATFORMIO_CORE_DIR="${PLATFORMIO_CORE_DIR:-${INSTALL_HOME}/.platformio}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) CHECK_ONLY=1 ;;
    -h|--help) echo "Usage: bash scripts/flash_esp32_dualeye_current.sh [--check-only]"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done
mkdir -p "${ROOT}/logs/deployment" "${ROOT}/logs/preflight"

write_status() {
  local status="$1" reason="$2" used_baud="${3:-}"
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${PORT}" "${ESP32_DIR}" "${used_baud}" <<'PY'
import json, sys, time
from pathlib import Path
path, status, reason, port, bundle, used_baud = sys.argv[1:]
Path(path).write_text(json.dumps({
    "status": status,
    "reason": reason,
    "port": port,
    "bundle_dir": bundle,
    "chip": "esp32s3",
    "identity_probe_required": True,
    "serial_privilege_fallback": True,
    "write_baud": int(used_baud) if used_baud.isdigit() else None,
    "low_baud_retry_enabled": True,
    "runtime_readiness_polled": True,
    "updated_at": time.time(),
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

required=(bootloader.bin partitions.bin boot_app0.bin firmware.bin srmodels.bin)
for file in "${required[@]}"; do
  [[ -f "${ESP32_DIR}/${file}" ]] || {
    write_status missing_artifact "Missing ESP32 bundle file: ${file}"
    echo "Missing ESP32 bundle file: ${ESP32_DIR}/${file}" >&2
    exit 1
  }
done

STRICT_ESP32_TOOLS=1 bash scripts/setup_esp32_tools.sh
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

if [[ "${CHECK_ONLY}" == "1" ]]; then
  "${runner[@]}" version >/dev/null 2>&1
  write_status check_only_ready "ESP32 bundle, esptool, identity probe, low-baud retry, and runtime polling contracts validated."
  exit 0
fi

if [[ -z "${PORT}" ]]; then
  PYTHONPATH=pi-companion python3 scripts/discover_koalabyte_ports.py --profile heltec --output-dir logs/preflight >/dev/null 2>&1 || true
  if [[ -f logs/preflight/koalabyte_ports.env ]]; then
    # shellcheck disable=SC1091
    source logs/preflight/koalabyte_ports.env
    PORT="${ESP32_PORT:-${KOALABYTE_ESP32_FACE_PORT:-${KOALABYTE_ESP32_DUALEYE_BY_ID:-}}}"
  fi
fi
if [[ -n "${PORT}" ]] && ! probe_esp32s3 "${PORT}"; then
  echo "Configured port did not identify as ESP32-S3: ${PORT}" >&2
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
    if probe_esp32s3 "${candidate}"; then PORT="${candidate}"; break; fi
  done
fi
if [[ -z "${PORT}" || ! -e "${PORT}" ]]; then
  write_status port_missing "No serial candidate answered an ESP32-S3 chip_id probe."
  echo "ESP32-S3 DualEye not found. Connect it, or hold BOOT while retrying." >&2
  exit 1
fi
probe_esp32s3 "${PORT}" || { write_status identity_failed "Final ESP32-S3 identity probe failed."; exit 1; }

flash_at_baud() {
  local upload_baud="$1"
  run_esptool_for_port "${PORT}" --chip esp32s3 --port "${PORT}" --baud "${upload_baud}" \
    --before default_reset --after hard_reset write_flash -z \
    --flash_mode qio --flash_freq 80m --flash_size 16MB \
    0x00000000 "${ESP32_DIR}/bootloader.bin" \
    0x00008000 "${ESP32_DIR}/partitions.bin" \
    0x0000e000 "${ESP32_DIR}/boot_app0.bin" \
    0x00010000 "${ESP32_DIR}/firmware.bin" \
    0x00cb0000 "${ESP32_DIR}/srmodels.bin"
}

write_status flashing "Writing complete ESP32-S3 image set after chip verification." "${BAUD}"
echo "Flashing verified ESP32-S3 DualEye on ${PORT} at ${BAUD} baud..."
used_baud="${BAUD}"
if ! flash_at_baud "${BAUD}"; then
  if [[ "${FALLBACK_BAUD}" == "${BAUD}" ]]; then
    write_status flash_failed "ESP32 image write failed at ${BAUD} baud." "${BAUD}"
    exit 1
  fi
  echo "ESP32 write failed at ${BAUD}; retrying complete image at ${FALLBACK_BAUD} baud..." >&2
  sleep 2
  used_baud="${FALLBACK_BAUD}"
  flash_at_baud "${FALLBACK_BAUD}" || {
    write_status flash_failed "ESP32 image write failed at both ${BAUD} and ${FALLBACK_BAUD} baud." "${FALLBACK_BAUD}"
    exit 1
  }
fi

query_node_status() {
  local candidate="$1" python_runner=(python3)
  [[ -e "${candidate}" ]] || return 1
  if [[ ! -r "${candidate}" || ! -w "${candidate}" ]] && command -v sudo >/dev/null 2>&1; then
    python_runner=(sudo env "PYTHONPATH=${ROOT}/pi-companion" python3)
  fi
  PYTHONPATH=pi-companion "${python_runner[@]}" - "${candidate}" <<'PY'
import json, sys, time
import serial
port = sys.argv[1]
ser = serial.Serial()
ser.port = port
ser.baudrate = 115200
ser.timeout = 0.25
ser.write_timeout = 1.0
ser.dsrdtr = False
ser.rtscts = False
ser.dtr = False
ser.rts = False
ser.open()
try:
    time.sleep(0.35)
    deadline = time.time() + 3.5
    next_request = 0.0
    while time.time() < deadline:
        now = time.time()
        if now >= next_request:
            ser.write(b'{"type":"node_status"}\n')
            ser.flush()
            next_request = now + 0.8
        line = ser.readline().decode("utf-8", errors="replace").strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if payload.get("type") == "node_status" and payload.get("device") == "esp32-s3-dualeye":
            print(json.dumps(payload, sort_keys=True))
            raise SystemExit(0)
finally:
    ser.close()
raise SystemExit(1)
PY
}

deadline=$(( $(date +%s) + WAIT_SECONDS ))
verified_port=""
while (( $(date +%s) < deadline )); do
  PYTHONPATH=pi-companion python3 scripts/discover_koalabyte_ports.py --profile heltec --output-dir logs/preflight >/dev/null 2>&1 || true
  discovered=""
  if [[ -f logs/preflight/koalabyte_ports.env ]]; then
    # shellcheck disable=SC1091
    source logs/preflight/koalabyte_ports.env
    discovered="${ESP32_PORT:-${KOALABYTE_ESP32_FACE_PORT:-${KOALABYTE_ESP32_DUALEYE_BY_ID:-}}}"
  fi
  for candidate in /dev/koalabyte-esp32-dualeye "${discovered}" "${PORT}"; do
    [[ -n "${candidate}" && -e "${candidate}" ]] || continue
    if query_node_status "${candidate}"; then
      verified_port="${candidate}"
      break 2
    fi
  done
  sleep 1
done

if [[ -n "${verified_port}" ]]; then
  PORT="${verified_port}"
  write_status flashed "ESP32 image set flashed and node_status verified after readiness polling." "${used_baud}"
  echo "ESP32-S3 firmware flash complete."
  exit 0
fi

write_status flashed_unverified "ESP32 image write completed, but node_status did not become ready before timeout." "${used_baud}"
echo "ESP32 image write completed, but runtime node_status verification timed out." >&2
exit 1
