#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${KOALABYTE_FIRMWARE_MANIFEST:-${REPO_ROOT}/firmware/prebuilt/manifest.json}"
STATUS_PATH="${KOALABYTE_ESP32_PREBUILT_FLASH_STATUS:-${REPO_ROOT}/logs/one_shot/esp32_prebuilt_flash_status.json}"
STATE_PATH="${KOALABYTE_PERIPHERAL_STATE_PATH:-${REPO_ROOT}/logs/one_shot/peripheral_firmware_state.json}"
ESP32_PORT="${ESP32_PORT:-${KOALABYTE_ESP32_MIC_PORT:-${KOALABYTE_ESP32_FACE_PORT:-/dev/koalabyte-esp32-dualeye}}}"
FLASH_MODE="${FLASH_ESP32:-auto}"
FORCE="${FORCE_ESP32_FLASH:-0}"
BAUD="${ESP32_FLASH_BAUD:-460800}"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/pi-companion/.venv/bin/python}"
PACKAGE_DIR="${KOALABYTE_ESP32_FIRMWARE_PACKAGE:-}"
DIRECT_IMAGE="${ESP32_PREBUILT_IMAGE:-}"

mkdir -p "$(dirname "${STATUS_PATH}")" "$(dirname "${STATE_PATH}")"

manifest_value() {
  python3 - <<'PY' "${MANIFEST}" "$1"
import json, sys
manifest, key = sys.argv[1:]
data = json.load(open(manifest, encoding="utf-8"))["esp32_s3_dualeye"]
print(data.get(key, ""))
PY
}

write_status() {
  local status="$1" reason="$2" image="${3:-}" expected="${4:-}"
  python3 - <<'PY' "${STATUS_PATH}" "${status}" "${reason}" "${ESP32_PORT}" "${image}" "${expected}" "${FLASH_MODE}"
import json, sys, time
from pathlib import Path
path, status, reason, port, image, expected, mode = sys.argv[1:]
payload = {
    "status": status,
    "reason": reason,
    "port": port,
    "image": image,
    "expected_sha256": expected,
    "flash_mode": mode,
    "target": "esp32-s3-dualeye",
    "updated_at": time.time(),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(payload, sort_keys=True))
PY
}

case "${FLASH_MODE}" in
  0|false|False|no|NO|skip|SKIP)
    write_status "ESP32_FLASH_SKIPPED" "Disabled by FLASH_ESP32 configuration."
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES) ;;
  *) echo "Unsupported FLASH_ESP32=${FLASH_MODE}; use auto, 1, or 0." >&2; exit 2 ;;
esac

if [[ ! -f "${MANIFEST}" ]]; then
  write_status "ESP32_MANIFEST_MISSING" "Prebuilt firmware manifest is missing."
  exit 1
fi

relative="$(manifest_value file)"
expected="$(manifest_value sha256)"
version="$(manifest_value version)"
basename="$(basename "${relative}")"
repo_image="${REPO_ROOT}/${relative}"
image=""

if [[ -n "${DIRECT_IMAGE}" ]]; then
  image="${DIRECT_IMAGE}"
elif [[ -n "${PACKAGE_DIR}" && -f "${PACKAGE_DIR%/}/${basename}" ]]; then
  image="${PACKAGE_DIR%/}/${basename}"
elif [[ -f "${repo_image}" ]]; then
  image="${repo_image}"
fi

if [[ -z "${image}" || ! -f "${image}" ]]; then
  if [[ "${FLASH_MODE}" == "auto" || "${FLASH_MODE}" == "AUTO" ]]; then
    write_status "ESP32_PREBUILT_NOT_INCLUDED" "Release image not found; preserving connected firmware. Set KOALABYTE_ESP32_FIRMWARE_PACKAGE to the extracted ZIP folder." "${repo_image}" "${expected}"
    exit 0
  fi
  write_status "ESP32_PREBUILT_MISSING" "Required prebuilt full-flash image is missing. Set KOALABYTE_ESP32_FIRMWARE_PACKAGE or ESP32_PREBUILT_IMAGE." "${repo_image}" "${expected}"
  exit 1
fi
image="$(cd "$(dirname "${image}")" && pwd)/$(basename "${image}")"

if [[ -z "${expected}" || "${expected}" == "PENDING_RELEASE_WORKFLOW" ]]; then
  write_status "ESP32_HASH_UNPINNED" "Manifest does not contain a final image hash." "${image}" "${expected}"
  exit 1
fi

actual="$(sha256sum "${image}" | awk '{print $1}')"
if [[ "${actual}" != "${expected}" ]]; then
  write_status "ESP32_HASH_MISMATCH" "Refusing to flash an image that does not match the manifest." "${image}" "${expected}"
  exit 1
fi

previous="$(python3 - <<'PY' "${STATE_PATH}"
import json, sys
try:
    print(json.load(open(sys.argv[1], encoding="utf-8")).get("esp32_s3_dualeye", {}).get("sha256", ""))
except Exception:
    print("")
PY
)"
if [[ "${FORCE}" != "1" && "${previous}" == "${expected}" ]]; then
  write_status "ESP32_ALREADY_CURRENT" "Recorded peripheral state already matches bundled image; no reflash performed." "${image}" "${expected}"
  exit 0
fi

if [[ ! -e "${ESP32_PORT}" ]]; then
  for candidate in /dev/koalabyte-esp32-dualeye /dev/ttyACM0 /dev/ttyACM1 /dev/ttyUSB0 /dev/ttyUSB1; do
    if [[ -e "${candidate}" ]]; then ESP32_PORT="${candidate}"; break; fi
  done
fi
if [[ ! -e "${ESP32_PORT}" ]]; then
  if [[ "${FLASH_MODE}" == "auto" || "${FLASH_MODE}" == "AUTO" ]]; then
    write_status "ESP32_NOT_CONNECTED" "Prebuilt image verified, but no ESP32 serial port was found; flashing skipped." "${image}" "${expected}"
    exit 0
  fi
  write_status "ESP32_PORT_MISSING" "ESP32 flash was required but no serial port was found." "${image}" "${expected}"
  exit 1
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

if [[ "${FORCE}" != "1" && ( "${FLASH_MODE}" == "auto" || "${FLASH_MODE}" == "AUTO" ) ]]; then
  set +e
  "${PYTHON_BIN}" "${REPO_ROOT}/scripts/probe_esp32_dualeye_version.py" --port "${ESP32_PORT}"
  probe_rc=$?
  set -e
  case "${probe_rc}" in
    0)
      write_status "ESP32_CURRENT_BY_PROBE" "Connected firmware reports current v0.9.8 wake-session behavior; no reflash performed." "${image}" "${expected}"
      exit 0
      ;;
    10)
      echo "Connected ESP32-S3 was positively identified as older than v0.9.8; flashing verified release image."
      ;;
    *)
      write_status "ESP32_VERSION_UNKNOWN_PRESERVED" "Version could not be positively identified; auto policy preserves firmware. Use FLASH_ESP32=1 for an explicit reflash." "${image}" "${expected}"
      exit 0
      ;;
  esac
fi

"${PYTHON_BIN}" -m pip install --quiet "esptool==4.11.0"
"${PYTHON_BIN}" -m esptool --chip esp32s3 --port "${ESP32_PORT}" chip_id
"${PYTHON_BIN}" -m esptool --chip esp32s3 --port "${ESP32_PORT}" erase_flash
"${PYTHON_BIN}" -m esptool --chip esp32s3 --port "${ESP32_PORT}" --baud "${BAUD}" write_flash -z 0x0 "${image}"
"${PYTHON_BIN}" -m esptool --chip esp32s3 --port "${ESP32_PORT}" verify_flash 0x0 "${image}"

python3 - <<'PY' "${STATE_PATH}" "${expected}" "${version}" "${image}"
import json, sys, time
from pathlib import Path
path, sha, version, image = sys.argv[1:]
try:
    payload = json.load(open(path, encoding="utf-8"))
except Exception:
    payload = {}
payload["esp32_s3_dualeye"] = {
    "sha256": sha,
    "version": version,
    "image": image,
    "flashed_at": time.time(),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
PY
write_status "ESP32_FLASH_VERIFIED" "Full-flash image erased, written, and verified successfully." "${image}" "${expected}"
