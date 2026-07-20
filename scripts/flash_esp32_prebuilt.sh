#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

CHECK_ONLY=0
ESP32_PORT="${ESP32_PORT:-}"
ESP32_BAUD="${ESP32_BAUD:-460800}"
ESP32_SKIP_ERASE="${ESP32_SKIP_ERASE:-0}"
ALLOW_UNVERIFIED_ESP32_IMAGE="${ALLOW_UNVERIFIED_ESP32_IMAGE:-0}"
EXPECTED_BASENAME="koalabyte-esp32-s3-dualeye-v0.9.8-killerkoala-wake-session-full-flash.bin"
STATUS_PATH="${KOALABYTE_ESP32_FLASH_STATUS_PATH:-logs/one_shot/esp32_prebuilt_flash_status.json}"

usage() {
  cat <<'USAGE'
Flash the hash-verified KoalaByte ESP32-S3 DualEye v0.9.8 full-flash image.

Usage:
  ESP32_PORT=/dev/ttyACM0 bash scripts/flash_esp32_prebuilt.sh
  bash scripts/flash_esp32_prebuilt.sh --check-only

Optional environment:
  ESP32_PREBUILT_IMAGE=/absolute/path/to/full-flash.bin
  KOALABYTE_ESP32_FIRMWARE_PACKAGE=/path/to/unzipped/firmware-package
  ESP32_BAUD=460800
  ESP32_SKIP_ERASE=1
  ALLOW_UNVERIFIED_ESP32_IMAGE=1   # emergency-only; not recommended
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only|--dry-run)
      CHECK_ONLY=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

mkdir -p "$(dirname "${STATUS_PATH}")"

write_status() {
  local status="$1"
  local reason="$2"
  local image="${3:-}"
  local sha256="${4:-}"
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${image}" "${sha256}" "${ESP32_PORT}" "${CHECK_ONLY}" <<'PY'
import json
import sys
import time
from pathlib import Path

path, status, reason, image, sha256, port, check_only = sys.argv[1:]
payload = {
    "status": status,
    "reason": reason,
    "image": image or None,
    "sha256": sha256 or None,
    "port": port or None,
    "check_only": check_only == "1",
    "updated_at": time.time(),
}
Path(path).parent.mkdir(parents=True, exist_ok=True)
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
PY
}

find_image() {
  local candidate=""
  if [[ -n "${ESP32_PREBUILT_IMAGE:-}" ]]; then
    printf '%s\n' "${ESP32_PREBUILT_IMAGE}"
    return 0
  fi
  if [[ -n "${KOALABYTE_ESP32_FIRMWARE_PACKAGE:-}" ]]; then
    candidate="${KOALABYTE_ESP32_FIRMWARE_PACKAGE%/}/${EXPECTED_BASENAME}"
    if [[ -f "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  fi
  for candidate in \
    "firmware/prebuilt/esp32/${EXPECTED_BASENAME}" \
    "releases/koalabyte-esp32-s3-dualeye-v0.9.8-killerkoala-wake-session/${EXPECTED_BASENAME}" \
    "${HOME}/Downloads/koalabyte-esp32-s3-dualeye-v0.9.8-killerkoala-wake-session/${EXPECTED_BASENAME}"; do
    if [[ -f "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

verify_image() {
  local image="$1"
  local image_dir image_name expected actual sums manifest
  image_dir="$(cd "$(dirname "${image}")" && pwd)"
  image_name="$(basename "${image}")"
  actual="$(sha256sum "${image}" | awk '{print $1}')"
  sums="${image_dir}/SHA256SUMS.txt"
  manifest="${REPO_ROOT}/firmware/prebuilt/manifest.json"

  expected=""
  if [[ -f "${sums}" ]]; then
    expected="$(awk -v name="${image_name}" '$2 == name || $2 == "*" name {print $1; exit}' "${sums}")"
  fi
  if [[ -z "${expected}" && -f "${manifest}" ]]; then
    expected="$(python3 - "${manifest}" "${image_name}" <<'PY'
import json
import sys
from pathlib import Path

manifest_path, image_name = sys.argv[1:]
data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
entries = data.get("files", data)
if isinstance(entries, dict):
    for key, value in entries.items():
        if Path(key).name != image_name:
            continue
        if isinstance(value, str):
            print(value)
        elif isinstance(value, dict):
            print(value.get("sha256", ""))
        break
PY
)"
  fi

  if [[ -z "${expected}" ]]; then
    if [[ "${ALLOW_UNVERIFIED_ESP32_IMAGE}" == "1" ]]; then
      echo "WARNING: no published SHA-256 found; proceeding only because ALLOW_UNVERIFIED_ESP32_IMAGE=1." >&2
      printf '%s\n' "${actual}"
      return 0
    fi
    echo "No SHA-256 entry found for ${image_name}. Refusing an unverified firmware flash." >&2
    echo "Keep SHA256SUMS.txt beside the image or provide firmware/prebuilt/manifest.json." >&2
    return 1
  fi

  expected="$(printf '%s' "${expected}" | tr '[:upper:]' '[:lower:]')"
  actual="$(printf '%s' "${actual}" | tr '[:upper:]' '[:lower:]')"
  if [[ "${actual}" != "${expected}" ]]; then
    echo "Firmware SHA-256 mismatch." >&2
    echo "Expected: ${expected}" >&2
    echo "Actual:   ${actual}" >&2
    return 1
  fi
  printf '%s\n' "${actual}"
}

discover_port() {
  if [[ -n "${ESP32_PORT}" ]]; then
    return 0
  fi
  if [[ -f scripts/discover_koalabyte_ports.py ]]; then
    echo "Auto-discovering ESP32-S3 DualEye port..."
    python3 scripts/discover_koalabyte_ports.py --profile heltec >/tmp/koalabyte_ports_discovery.json 2>/tmp/koalabyte_ports_discovery.err || true
    if [[ -f logs/preflight/koalabyte_ports.env ]]; then
      # shellcheck disable=SC1091
      source logs/preflight/koalabyte_ports.env
      ESP32_PORT="${ESP32_PORT:-${KOALABYTE_ESP32_FACE_PORT:-${KOALABYTE_ESP32_DUALEYE_BY_ID:-}}}"
    fi
  fi
  [[ -n "${ESP32_PORT}" ]]
}

select_python() {
  local candidate
  for candidate in \
    "${PYTHON_BIN:-}" \
    "${REPO_ROOT}/pi-companion/.venv/bin/python" \
    "python3"; do
    [[ -n "${candidate}" ]] || continue
    if [[ -x "${candidate}" ]] || command -v "${candidate}" >/dev/null 2>&1; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

IMAGE="$(find_image || true)"
if [[ -z "${IMAGE}" || ! -f "${IMAGE}" ]]; then
  write_status "ESP32_PREBUILT_IMAGE_MISSING" "v0.9.8 full-flash image not found"
  echo "ESP32-S3 v0.9.8 prebuilt image not found." >&2
  echo "Set ESP32_PREBUILT_IMAGE or KOALABYTE_ESP32_FIRMWARE_PACKAGE." >&2
  exit 1
fi
IMAGE="$(cd "$(dirname "${IMAGE}")" && pwd)/$(basename "${IMAGE}")"
SHA256="$(verify_image "${IMAGE}")"

if [[ "${CHECK_ONLY}" == "1" ]]; then
  write_status "ESP32_PREBUILT_CHECK_OK" "image and SHA-256 verified; no device access performed" "${IMAGE}" "${SHA256}"
  echo "Verified ESP32-S3 v0.9.8 prebuilt image: ${IMAGE}"
  echo "SHA-256: ${SHA256}"
  exit 0
fi

if ! discover_port; then
  write_status "ESP32_PORT_NOT_FOUND" "no ESP32-S3 serial port was discovered" "${IMAGE}" "${SHA256}"
  echo "ESP32_PORT was not supplied or auto-discovered." >&2
  exit 1
fi

PY="$(select_python)"
if ! "${PY}" -m esptool version >/dev/null 2>&1; then
  "${PY}" -m pip install --user "esptool==4.11.0"
fi

write_status "ESP32_PREBUILT_FLASH_RUNNING" "verified full-flash write started" "${IMAGE}" "${SHA256}"
"${PY}" -m esptool --chip esp32s3 --port "${ESP32_PORT}" chip_id
if [[ "${ESP32_SKIP_ERASE}" != "1" ]]; then
  "${PY}" -m esptool --chip esp32s3 --port "${ESP32_PORT}" erase_flash
fi
"${PY}" -m esptool --chip esp32s3 --port "${ESP32_PORT}" --baud "${ESP32_BAUD}" write_flash -z 0x0 "${IMAGE}"
"${PY}" -m esptool --chip esp32s3 --port "${ESP32_PORT}" verify_flash 0x0 "${IMAGE}"
write_status "ESP32_PREBUILT_FLASH_OK" "verified v0.9.8 full-flash write completed" "${IMAGE}" "${SHA256}"

echo "ESP32-S3 DualEye v0.9.8 prebuilt flash and verification complete. Press RESET once."
