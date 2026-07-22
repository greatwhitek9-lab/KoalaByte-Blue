#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

BUNDLE_DIR="${KOALABYTE_FIRMWARE_BUNDLE_DIR:-${ROOT}/releases/koalabyte-blue-current}"
ESP32_DIR="${BUNDLE_DIR}/esp32"
STATUS_PATH="${ESP32_FLASH_STATUS_PATH:-${ROOT}/logs/deployment/esp32_flash_status.json}"
PORT="${ESP32_PORT:-${KOALABYTE_ESP32_FACE_PORT:-${KOALABYTE_ESP32_DUALEYE_BY_ID:-}}}"
BAUD="${ESP32_UPLOAD_BAUD:-460800}"
WAIT_SECONDS="${ESP32_FLASH_WAIT_SECONDS:-35}"
CHECK_ONLY=0

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
  local status="$1" reason="$2"
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${PORT}" "${ESP32_DIR}" <<'PY'
import json, sys, time
from pathlib import Path
path, status, reason, port, bundle = sys.argv[1:]
Path(path).write_text(json.dumps({
    "status": status, "reason": reason, "port": port, "bundle_dir": bundle,
    "chip": "esp32s3", "identity_probe_required": True,
    "serial_privilege_fallback": True, "updated_at": time.time(),
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
esptool="$(find "${HOME}/.platformio/packages/tool-esptoolpy" -maxdepth 4 -type f \
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
  write_status check_only_ready "ESP32 bundle, esptool, and identity-probe contract validated."
  exit 0
fi

if [[ -z "${PORT}" ]]; then
  PYTHONPATH=pi-companion python3 scripts/discover_koalabyte_ports.py --profile heltec --output-dir logs/preflight >/dev/null 2>&1 || true
  if [[ -f logs/preflight/koalabyte_ports.env ]]; then
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

write_status flashing "Writing complete ESP32-S3 image set after chip verification."
echo "Flashing verified ESP32-S3 DualEye on ${PORT}..."
run_esptool_for_port "${PORT}" --chip esp32s3 --port "${PORT}" --baud "${BAUD}" \
  --before default_reset --after hard_reset write_flash -z \
  --flash_mode qio --flash_freq 80m --flash_size 16MB \
  0x00000000 "${ESP32_DIR}/bootloader.bin" \
  0x00008000 "${ESP32_DIR}/partitions.bin" \
  0x0000e000 "${ESP32_DIR}/boot_app0.bin" \
  0x00010000 "${ESP32_DIR}/firmware.bin" \
  0x00cb0000 "${ESP32_DIR}/srmodels.bin"

deadline=$(( $(date +%s) + WAIT_SECONDS ))
verify_port=""
while (( $(date +%s) < deadline )); do
  for candidate in /dev/koalabyte-esp32-dualeye "${PORT}"; do
    if [[ -n "${candidate}" && -e "${candidate}" ]]; then verify_port="${candidate}"; break 2; fi
  done
  sleep 1
done
[[ -n "${verify_port}" ]] || {
  write_status flashed_unverified "ESP32 write completed, but its runtime path did not return."
  exit 1
}

verify_runner=(python3)
if [[ ! -r "${verify_port}" || ! -w "${verify_port}" ]] && command -v sudo >/dev/null 2>&1; then
  verify_runner=(sudo env "PYTHONPATH=${ROOT}/pi-companion" python3)
fi
if PYTHONPATH=pi-companion "${verify_runner[@]}" - "${verify_port}" <<'PY'
import json, sys, time
import serial
port = sys.argv[1]
with serial.Serial(port, 115200, timeout=0.3, write_timeout=1.0) as ser:
    time.sleep(1.0)
    ser.reset_input_buffer()
    ser.write(b'{"type":"node_status"}\n')
    ser.flush()
    deadline = time.time() + 8
    while time.time() < deadline:
        line = ser.readline().decode("utf-8", errors="replace").strip()
        if not line:
            continue
        try: payload = json.loads(line)
        except Exception: continue
        if payload.get("type") == "node_status" and payload.get("device") == "esp32-s3-dualeye":
            print(json.dumps(payload, sort_keys=True))
            raise SystemExit(0)
raise SystemExit(1)
PY
then
  write_status flashed "ESP32 image set flashed and node_status verified."
  echo "ESP32-S3 firmware flash complete."
else
  write_status flashed_unverified "ESP32 image write completed, but node_status verification failed."
  exit 1
fi
