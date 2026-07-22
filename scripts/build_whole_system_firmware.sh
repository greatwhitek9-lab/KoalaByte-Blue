#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

CHECK_ONLY=0
SKIP_ESP32=0
SKIP_T114=0
BUNDLE_DIR="${KOALABYTE_FIRMWARE_BUNDLE_DIR:-${ROOT}/releases/koalabyte-blue-current}"
STAGING_DIR="${BUNDLE_DIR}.staging.$$"
PREVIOUS_DIR="${BUNDLE_DIR}.previous"
ESP32_BUILD="${ROOT}/firmware/esp32-dualeye/.pio/build/esp32s3_dualeye"
T114_BUILD="${T114_COMBINED_BUILD_DIR:-${ROOT}/build/t114-combined-safe}"
STATUS_PATH="${KOALABYTE_FIRMWARE_BUILD_STATUS:-${ROOT}/logs/deployment/firmware_build_status.json}"
ESP32_TOOLS_VENV="${ESP32_TOOLS_VENV:-${HOME}/.venvs/platformio}"
PIO_BIN="${PIO_BIN:-}"
PIO_JOBS="${PIO_JOBS:-1}"
CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-1}"
SOURCE_BACKUP_DIR="${ROOT}/logs/deployment/esp32-source-backup"
SOURCE_BACKUP_ACTIVE=0

usage() {
  cat <<'EOF'
Build the complete KoalaByte Blue peripheral firmware bundle.

Usage:
  bash scripts/build_whole_system_firmware.sh
  bash scripts/build_whole_system_firmware.sh --check-only
  bash scripts/build_whole_system_firmware.sh --skip-esp32
  bash scripts/build_whole_system_firmware.sh --skip-t114

The build uses one job by default on low-memory Raspberry Pi hosts, preserves the
last verified firmware bundle until its replacement is complete, and restores
tracked ESP32 generator inputs after every build attempt.
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

mkdir -p "${ROOT}/logs/deployment" "$(dirname "${BUNDLE_DIR}")"

write_status() {
  local status="$1" reason="$2"
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${BUNDLE_DIR}" \
    "${SKIP_ESP32}" "${SKIP_T114}" "${PIO_JOBS}" "${CMAKE_BUILD_PARALLEL_LEVEL}" <<'PY'
import json, sys, time
from pathlib import Path
path, status, reason, bundle, skip_esp32, skip_t114, pio_jobs, cmake_jobs = sys.argv[1:]
Path(path).write_text(json.dumps({
    "status": status,
    "reason": reason,
    "bundle_dir": bundle,
    "esp32_included": skip_esp32 != "1",
    "t114_included": skip_t114 != "1",
    "source_build": True,
    "dependencies_gated_before_build": True,
    "atomic_bundle_publish": True,
    "esp32_source_restore": True,
    "pio_jobs": int(pio_jobs),
    "cmake_parallel_level": int(cmake_jobs),
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

tracked_esp32_sources=(
  firmware/esp32-dualeye/src/integrated_main.cpp
  firmware/esp32-dualeye/src/integrated_main_wake_session.cpp
  firmware/esp32-dualeye/include/config.h
)

restore_esp32_sources() {
  local relative backup
  [[ -d "${SOURCE_BACKUP_DIR}" ]] || { SOURCE_BACKUP_ACTIVE=0; return 0; }
  for relative in "${tracked_esp32_sources[@]}"; do
    backup="${SOURCE_BACKUP_DIR}/${relative}"
    if [[ -f "${backup}" ]]; then
      mkdir -p "$(dirname "${ROOT}/${relative}")"
      cp -f "${backup}" "${ROOT}/${relative}"
    fi
  done
  rm -rf -- "${SOURCE_BACKUP_DIR}"
  SOURCE_BACKUP_ACTIVE=0
}

backup_esp32_sources() {
  local relative
  # Recover exact pre-build sources after a prior interrupted run, then create a
  # fresh transaction backup for this build.
  restore_esp32_sources
  mkdir -p "${SOURCE_BACKUP_DIR}"
  for relative in "${tracked_esp32_sources[@]}"; do
    [[ -f "${ROOT}/${relative}" ]] || continue
    mkdir -p "$(dirname "${SOURCE_BACKUP_DIR}/${relative}")"
    cp -p "${ROOT}/${relative}" "${SOURCE_BACKUP_DIR}/${relative}"
  done
  SOURCE_BACKUP_ACTIVE=1
}

on_exit() {
  local rc=$?
  if [[ "${SOURCE_BACKUP_ACTIVE}" == "1" || -d "${SOURCE_BACKUP_DIR}" ]]; then
    restore_esp32_sources || true
  fi
  [[ -d "${STAGING_DIR}" ]] && rm -rf -- "${STAGING_DIR}"
  exit "${rc}"
}
trap on_exit EXIT

validate_sources() {
  bash -n scripts/build_whole_system_firmware.sh
  bash -n scripts/setup_esp32_tools.sh
  bash -n scripts/setup_nrf_connect_sdk_toolchain.sh
  bash -n scripts/build_t114_combined_safe.sh
  bash -n scripts/preflight_firmware_host.sh
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
    [[ -x "${ESP32_TOOLS_VENV}/bin/edge-tts" || -x "${ROOT}/pi-companion/.venv/bin/edge-tts" ]] || {
      echo "edge-tts is missing after ESP32 dependency setup." >&2; return 1;
    }
    command -v ffmpeg >/dev/null 2>&1 || { echo "ffmpeg is missing." >&2; return 1; }
    "${PIO_BIN}" --version
  fi
  if [[ "${SKIP_T114}" != "1" ]]; then
    INSTALL_NCS_TOOLCHAIN=1 STRICT_NCS_TOOLCHAIN=1 bash scripts/setup_nrf_connect_sdk_toolchain.sh
    source "${ROOT}/logs/nrf_connect_sdk_env.sh"
    command -v west >/dev/null 2>&1
    command -v cmake >/dev/null 2>&1
    command -v ninja >/dev/null 2>&1
    test -d "${NCS_WORKSPACE}/.west"
    test -x "${ZEPHYR_SDK_INSTALL_DIR}/arm-zephyr-eabi/bin/arm-zephyr-eabi-gcc"
  fi
  write_status dependencies_ready "All selected firmware dependencies passed."
}

publish_bundle_atomically() {
  rm -rf -- "${PREVIOUS_DIR}"
  if [[ -d "${BUNDLE_DIR}" ]]; then mv "${BUNDLE_DIR}" "${PREVIOUS_DIR}"; fi
  if mv "${STAGING_DIR}" "${BUNDLE_DIR}"; then
    rm -rf -- "${PREVIOUS_DIR}"
  else
    [[ -d "${PREVIOUS_DIR}" ]] && mv "${PREVIOUS_DIR}" "${BUNDLE_DIR}"
    return 1
  fi
}

validate_sources
if [[ "${CHECK_ONLY}" == "1" ]]; then
  write_status check_only_ready "Whole-system firmware source/build contract validated."
  echo "Whole-system firmware build contract ready."
  exit 0
fi

bash scripts/preflight_firmware_host.sh --before-build
prepare_all_dependencies
rm -rf -- "${STAGING_DIR}"
mkdir -p "${STAGING_DIR}/esp32" "${STAGING_DIR}/t114"

if [[ "${SKIP_ESP32}" != "1" ]]; then
  echo "== Build ESP32-S3 DualEye with ${PIO_JOBS} job(s) =="
  backup_esp32_sources
  PATH="${ESP32_TOOLS_VENV}/bin:${ROOT}/pi-companion/.venv/bin:${HOME}/.local/bin:${PATH}" \
    "${PIO_BIN}" run -j "${PIO_JOBS}" -d firmware/esp32-dualeye

  boot_app0="$(find "${HOME}/.platformio/packages" -path '*/tools/partitions/boot_app0.bin' -print -quit)"
  srmodels="$(find "${HOME}/.platformio/packages" -path '*/esp_sr/srmodels.bin' -print -quit)"
  for file in bootloader.bin partitions.bin firmware.bin; do
    test -f "${ESP32_BUILD}/${file}"
    cp "${ESP32_BUILD}/${file}" "${STAGING_DIR}/esp32/${file}"
  done
  test -n "${boot_app0}" && test -f "${boot_app0}"
  test -n "${srmodels}" && test -f "${srmodels}"
  cp "${boot_app0}" "${STAGING_DIR}/esp32/boot_app0.bin"
  cp "${srmodels}" "${STAGING_DIR}/esp32/srmodels.bin"
  restore_esp32_sources
fi

if [[ "${SKIP_T114}" != "1" ]]; then
  echo "== Build Heltec T114 UF2 with ${CMAKE_BUILD_PARALLEL_LEVEL} job(s) =="
  source "${ROOT}/logs/nrf_connect_sdk_env.sh"
  export CMAKE_BUILD_PARALLEL_LEVEL
  STRICT_T114_COMBINED_BUILD=1 bash scripts/build_t114_combined_safe.sh
  raw="${T114_BUILD}/zephyr/zephyr.uf2"
  output="${STAGING_DIR}/t114/koalabyte-t114-current.uf2"
  test -f "${raw}"
  python3 scripts/patch_uf2_family.py "${raw}" "${output}" 0x239a0071
  python3 scripts/verify_uf2_vector.py "${output}" \
    --vector-address 0x26000 --application-min 0x26000 --application-max 0xec000 \
    --family 0x239a0071 > "${STAGING_DIR}/t114/vector-validation.txt"
  grep -Fq 'Reset handler range valid: true' "${STAGING_DIR}/t114/vector-validation.txt"
fi

source_commit="unknown"
if git rev-parse HEAD >/dev/null 2>&1; then source_commit="$(git rev-parse HEAD)"; fi
python3 - "${STAGING_DIR}" "${source_commit}" "${SKIP_ESP32}" "${SKIP_T114}" <<'PY'
import hashlib, json, sys, time
from pathlib import Path
bundle = Path(sys.argv[1]); source_commit = sys.argv[2]
skip_esp32 = sys.argv[3] == "1"; skip_t114 = sys.argv[4] == "1"
def record(path: Path, address=None):
    data = path.read_bytes()
    row = {"path": str(path.relative_to(bundle)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    if address is not None: row["flash_address"] = address
    return row
esp32 = []
for name, address in (("bootloader.bin", "0x00000000"), ("partitions.bin", "0x00008000"),
                      ("boot_app0.bin", "0x0000e000"), ("firmware.bin", "0x00010000"),
                      ("srmodels.bin", "0x00cb0000")):
    path = bundle / "esp32" / name
    if path.exists(): esp32.append(record(path, address))
t114 = bundle / "t114" / "koalabyte-t114-current.uf2"
manifest = {
    "schema": 1, "bundle": "koalabyte-blue-current", "source_commit": source_commit,
    "built_at": time.time(), "dependencies_gated_before_build": True,
    "esp32": {"target": "Waveshare ESP32-S3 DualEye 1.28 non-touch", "included": not skip_esp32,
              "chip": "esp32s3", "flash_mode": "qio", "flash_frequency": "80m",
              "flash_size": "16MB", "files": esp32},
    "t114": {"target": "Heltec T114 / HT-n5262 nRF52840 UF2", "included": not skip_t114,
             "volume_label": "HT-n5262", "family_id": "0x239a0071",
             "application_offset": "0x00026000", "file": record(t114) if t114.exists() else None},
}
(bundle / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
checksums = []
for path in sorted(bundle.rglob("*")):
    if path.is_file() and path.name != "SHA256SUMS.txt":
        checksums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(bundle)}")
(bundle / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")
PY
(
  cd "${STAGING_DIR}"
  sha256sum -c SHA256SUMS.txt
)
publish_bundle_atomically
write_status built "All firmware built, validated, checksummed, and atomically published."
echo "Firmware bundle ready: ${BUNDLE_DIR}"
