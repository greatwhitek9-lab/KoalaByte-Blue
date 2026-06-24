#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

STATUS_PATH="${HELTEC_MOUTH_STATUS_PATH:-logs/heltec_mouth_flash_status.json}"
HELTEC_UPLOAD_PORT="${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-}}"
BUILD_ONLY="${BUILD_ONLY:-0}"
NO_MONITOR="${NO_MONITOR:-1}"

mkdir -p "$(dirname "${STATUS_PATH}")"

json_escape() {
  python3 - <<'PY' "$1"
import json, sys
print(json.dumps(sys.argv[1]))
PY
}

write_status() {
  local status="$1"
  local reason="$2"
  cat > "${STATUS_PATH}" <<JSON
{
  "status": $(json_escape "${status}"),
  "reason": $(json_escape "${reason}"),
  "firmware_dir": "firmware/heltec-mouth",
  "upload_port": $(json_escape "${HELTEC_UPLOAD_PORT}"),
  "updated_at": $(date +%s)
}
JSON
}

if ! command -v pio >/dev/null 2>&1; then
  write_status "missing_platformio" "PlatformIO is required for Heltec color-mouth firmware."
  echo "PlatformIO is required. Install with: python3 -m pip install -U platformio" >&2
  exit 1
fi

if [[ ! -f firmware/heltec-mouth/platformio.ini ]]; then
  write_status "missing_firmware" "firmware/heltec-mouth/platformio.ini is missing."
  echo "Missing firmware/heltec-mouth/platformio.ini" >&2
  exit 1
fi

echo "== Heltec Mesh Node T114 USB color-mouth firmware =="
if [[ "${BUILD_ONLY}" == "1" || "${1:-}" == "--build-only" ]]; then
  pio run -d firmware/heltec-mouth
  write_status "built" "Heltec color-mouth firmware build completed."
  exit 0
fi

if [[ -n "${HELTEC_UPLOAD_PORT}" ]]; then
  pio run -d firmware/heltec-mouth -t upload --upload-port "${HELTEC_UPLOAD_PORT}"
else
  pio run -d firmware/heltec-mouth -t upload
fi
write_status "flashed" "Heltec color-mouth firmware upload completed."

if [[ "${NO_MONITOR}" != "1" ]]; then
  if [[ -n "${HELTEC_UPLOAD_PORT}" ]]; then
    pio device monitor -d firmware/heltec-mouth -p "${HELTEC_UPLOAD_PORT}" -b "${KOALABYTE_FACE_BAUD:-115200}"
  else
    pio device monitor -d firmware/heltec-mouth -b "${KOALABYTE_FACE_BAUD:-115200}"
  fi
fi
