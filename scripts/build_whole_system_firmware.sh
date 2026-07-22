#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

CHECK_ONLY=0
SKIP_ESP32=0
SKIP_T114=0
BUNDLE_DIR="${KOALABYTE_FIRMWARE_BUNDLE_DIR:-${ROOT}/releases/koalabyte-blue-current}"
ESP32_BUILD="${ROOT}/firmware/esp32-dualeye/.pio/build/esp32s3_dualeye"
T114_BUILD="${T114_COMBINED_BUILD_DIR:-${ROOT}/build/t114-combined-safe}"
STATUS_PATH="${KOALABYTE_FIRMWARE_BUILD_STATUS:-${ROOT}/logs/deployment/firmware_build_status.json}"
ESP32_TOOLS_VENV="${ESP32_TOOLS_VENV:-${HOME}/.venvs/platformio}"
PIO_BIN="${PIO_BIN:-}"

usage() {
  cat <<'EOF'
Build the complete KoalaByte Blue peripheral firmware bundle.

Usage:
  bash scripts/build_whole_system_firmware.sh
  bash scripts/build_whole_system_firmware.sh --check-only
  bash scripts/build_whole_system_firmware.sh --skip-esp32
  bash scripts/build_whole_system_firmware.sh --skip-t114

All selected device toolchains and build dependencies are installed and validated
before the first project build begins.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) CHECK_ONLY=1 ;;
    --skip-esp32) SKIP_ESP32=1 ;;
    --skip-t114) SKIP_T114=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

mkdir -p "${ROOT}/logs/deployment" "${BUNDLE_DIR}/esp32" "${BUNDLE_DIR}/t114"

write_status() {
  local status="$1" reason="$2"
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${BUNDLE_DIR}" "${SKIP_ESP32}" "${SKIP_T114}" <<'PY'
import json, sys, time
from pathlib import Path
path, status, reason, bundle, skip_esp32, skip_t114 = sys.argv[1:]
Path(path).write_text(json.dumps({
    "status": status,
    "reason": reason,
    "bundle_dir": bundle,
    "esp32_included": skip_esp32 != "1",
    "t114_included": skip_t114 != "1",
    "source_build": True,
    "dependencies_gated_before_build": True,
    "updated_at": time.time(),
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

resolve_pio() {
  if [[ -n "${PIO_BIN}" && -x "${PIO_BIN}" ]]; then return 0; fi
  if command -v pio >/dev/null 2>&1; then PIO_BIN="$(command -v pio)"; return 0; fi
  if [[ -x "${ESP32_TOOLS_VENV}/bin/pio" ]]; then PIO_BIN="${ESP32_TOOLS_VENV}/bin/pio"; return 0; fi
  if [[ -x "${HOME}/.local/bin/pio" ]]; then PIO_BIN="${HOME}/.local/bin/pio"; return 0; fi
  return 1
}

validate_sources() {
  bash -n scripts/build_whole_system_firmware.sh
  bash -n scripts/setup_esp32_tools.sh
  bash -n scripts/setup_nrf_connect_sdk_toolchain.sh
  bash -n scripts/build_t114_combined_safe.sh
  python3 -m py_compile scripts/inspect_uf2.py scripts/patch_uf2_family.py scripts/verify_uf2_vector.py
  test -f firmware/esp32-dualeye/platformio.ini
  test -f firmware/esp32-dualeye/partitions.csv
  test -f firmware/t114-combined-safe/prj.conf
  grep -Fq 'CONFIG_BUILD_OUTPUT_UF2=y' firmware/t114-combined-safe/prj.conf
  grep -Fq 'model,    data, spiffs,  0xCB0000' firmware/esp32-dualeye/partitions.csv
}

prepare_all_dependencies() {
  echo "== Prepare all selected device build dependencies =="

  if [[ "${SKIP_ESP32}" != "1" ]]; then
    STRICT_ESP32_TOOLS=1 bash scripts/setup_esp32_tools.sh
    resolve_pio || { echo "PlatformIO executable not found after setup." >&2; return 1; }
    [[ -x "${ESP32_TOOLS_VENV}/bin/edge-tts" || -x "${HOME}/.local/bin/edge-tts" ]] || {
      echo "edge-tts is missing after ESP32 dependency setup." >&2; return 1;
    }
    command -v ffmpeg >/dev/null 2>&1 || {
      echo "ffmpeg is missing after ESP32 dependency setup." >&2; return 1;
    }
    "${PIO_BIN}" --version
    echo "ESP32 dependencies ready: ${PIO_BIN}, edge-tts, ffmpeg"
  fi

  if [[ "${SKIP_T114}" != "1" ]]; then
    INSTALL_NCS_TOOLCHAIN=1 STRICT_NCS_TOOLCHAIN=1 bash scripts/setup_nrf_connect_sdk_toolchain.sh
    test -f "${ROOT}/logs/nrf_connect_sdk_env.sh"
    # shellcheck disable=SC1091
    source "${ROOT}/logs/nrf_connect_sdk_env.sh"
    command -v west >/dev/null 2>&1 || { echo "west is missing after NCS setup." >&2; return 1; }
    command -v cmake >/dev/null 2>&1 || { echo "cmake is missing after NCS setup." >&2; return 1; }
    command -v ninja >/dev/null 2>&1 || { echo "ninja is missing after NCS setup." >&2; return 1; }
    test -d "${NCS_WORKSPACE}/.west"
    test -d "${ZEPHYR_BASE}"
    test -d "${ZEPHYR_SDK_INSTALL_DIR}"
    west --version
    cmake --version | head -n1
    ninja --version
    echo "Heltec dependencies ready: west, CMake, Ninja, NCS, Zephyr SDK"
  fi

  write_status "dependencies_ready" "All selected device dependencies validated before project builds."
}

validate_sources
if [[ "${CHECK_ONLY}" == "1" ]]; then
  write_status "check_only_ready" "Whole-system firmware source/build contract validated."
  echo "Whole-system firmware build contract ready."
  exit 0
fi

prepare_all_dependencies

rm -rf "${BUNDLE_DIR}"
mkdir -p "${BUNDLE_DIR}/esp32" "${BUNDLE_DIR}/t114"

if [[ "${SKIP_ESP32}" != "1" ]]; then
  echo "== Build ESP32-S3 DualEye =="
  echo "Using PlatformIO: ${PIO_BIN}"
  PATH="${ESP32_TOOLS_VENV}/bin:${HOME}/.local/bin:${PATH}" "${PIO_BIN}" run -d firmware/esp32-dualeye

  boot_app0="$(find "${HOME}/.platformio/packages" -path '*/tools/partitions/boot_app0.bin' -print -quit)"
  srmodels="$(find "${HOME}/.platformio/packages" -path '*/esp_sr/srmodels.bin' -print -quit)"
  for file in bootloader.bin partitions.bin firmware.bin; do
    test -f "${ESP32_BUILD}/${file}"
    cp "${ESP32_BUILD}/${file}" "${BUNDLE_DIR}/esp32/${file}"
  done
  test -n "${boot_app0}" && test -f "${boot_app0}"
  test -n "${srmodels}" && test -f "${srmodels}"
  cp "${boot_app0}" "${BUNDLE_DIR}/esp32/boot_app0.bin"
  cp "${srmodels}" "${BUNDLE_DIR}/esp32/srmodels.bin"
fi

if [[ "${SKIP_T114}" != "1" ]]; then
  echo "== Build Heltec T114 UF2 =="
  # Environment was validated before any project build; reload only in this process.
  # shellcheck disable=SC1091
  source "${ROOT}/logs/nrf_connect_sdk_env.sh"
  STRICT_T114_COMBINED_BUILD=1 bash scripts/build_t114_combined_safe.sh

  raw="${T114_BUILD}/zephyr/zephyr.uf2"
  output="${BUNDLE_DIR}/t114/koalabyte-t114-current.uf2"
  test -f "${raw}"
  python3 scripts/patch_uf2_family.py "${raw}" "${output}" 0x239a0071
  python3 scripts/verify_uf2_vector.py "${output}" \
    --vector-address 0x26000 \
    --application-min 0x26000 \
    --application-max 0xec000 \
    --family 0x239a0071 > "${BUNDLE_DIR}/t114/vector-validation.txt"
  grep -Fq 'Reset handler range valid: true' "${BUNDLE_DIR}/t114/vector-validation.txt"
fi

source_commit="unknown"
if command -v git >/dev/null 2>&1 && git rev-parse HEAD >/dev/null 2>&1; then
  source_commit="$(git rev-parse HEAD)"
fi

python3 - "${BUNDLE_DIR}" "${source_commit}" "${SKIP_ESP32}" "${SKIP_T114}" <<'PY'
import hashlib, json, sys, time
from pathlib import Path
bundle = Path(sys.argv[1])
source_commit = sys.argv[2]
skip_esp32 = sys.argv[3] == "1"
skip_t114 = sys.argv[4] == "1"

def record(path: Path, address=None):
    data = path.read_bytes()
    item = {"path": str(path.relative_to(bundle)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    if address is not None:
        item["flash_address"] = address
    return item

esp32 = []
for name, address in (("bootloader.bin", "0x00000000"), ("partitions.bin", "0x00008000"),
                      ("boot_app0.bin", "0x0000e000"), ("firmware.bin", "0x00010000"),
                      ("srmodels.bin", "0x00cb0000")):
    path = bundle / "esp32" / name
    if path.exists(): esp32.append(record(path, address))

t114_path = bundle / "t114" / "koalabyte-t114-current.uf2"
manifest = {
    "schema": 1, "bundle": "koalabyte-blue-current", "source_commit": source_commit,
    "built_at": time.time(), "dependencies_gated_before_build": True,
    "esp32": {"target": "Waveshare ESP32-S3 DualEye 1.28 non-touch", "included": not skip_esp32,
              "chip": "esp32s3", "flash_mode": "qio", "flash_frequency": "80m",
              "flash_size": "16MB", "files": esp32},
    "t114": {"target": "Heltec T114 / HT-n5262 nRF52840 UF2", "included": not skip_t114,
             "volume_label": "HT-n5262", "family_id": "0x239a0071",
             "application_offset": "0x00026000", "file": record(t114_path) if t114_path.exists() else None},
}
(bundle / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
checksums = []
for path in sorted(bundle.rglob("*")):
    if path.is_file() and path.name != "SHA256SUMS.txt":
        checksums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(bundle)}")
(bundle / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")
PY

write_status "built" "All dependencies passed before builds; current ESP32 and T114 firmware bundled and checksummed."
echo "Firmware bundle ready: ${BUNDLE_DIR}"
