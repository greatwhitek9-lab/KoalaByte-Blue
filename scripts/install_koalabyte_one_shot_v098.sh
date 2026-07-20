#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BASE_INSTALLER="${REPO_ROOT}/scripts/install_koalabyte_one_shot.sh"
FLASH_POLICY="${FLASH_ESP32:-auto}"
ESP32_PORT="${ESP32_PORT:-}"
CHECK_ONLY=0

for arg in "$@"; do
  case "${arg}" in
    --check-only|--dry-run)
      CHECK_ONLY=1
      ;;
  esac
done

if [[ ! -x "${BASE_INSTALLER}" && ! -f "${BASE_INSTALLER}" ]]; then
  echo "Base one-shot installer not found: ${BASE_INSTALLER}" >&2
  exit 1
fi

if [[ "${CHECK_ONLY}" == "1" ]]; then
  bash -n scripts/flash_esp32_prebuilt.sh
  bash -n scripts/install_koalabyte_one_shot_v098.sh
  python3 -m py_compile scripts/probe_esp32_dualeye_version.py
  if [[ "${FLASH_POLICY}" == "1" || "${FLASH_POLICY}" == "true" || "${FLASH_POLICY}" == "yes" ]]; then
    bash scripts/flash_esp32_prebuilt.sh --check-only
  fi
  FLASH_ESP32=0 bash "${BASE_INSTALLER}" "$@"
  exit $?
fi

if [[ -z "${ESP32_PORT}" && -f scripts/discover_koalabyte_ports.py ]]; then
  python3 scripts/discover_koalabyte_ports.py --profile heltec >/tmp/koalabyte_ports_discovery.json 2>/tmp/koalabyte_ports_discovery.err || true
  if [[ -f logs/preflight/koalabyte_ports.env ]]; then
    # shellcheck disable=SC1091
    source logs/preflight/koalabyte_ports.env
    ESP32_PORT="${ESP32_PORT:-${KOALABYTE_ESP32_FACE_PORT:-${KOALABYTE_ESP32_DUALEYE_BY_ID:-}}}"
  fi
fi

flash_prebuilt() {
  STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS:-1}" bash scripts/setup_esp32_tools.sh
  ESP32_PORT="${ESP32_PORT}" bash scripts/flash_esp32_prebuilt.sh
}

case "${FLASH_POLICY}" in
  0|false|False|no|NO|skip|SKIP)
    echo "Preserving existing ESP32-S3 DualEye firmware by configuration."
    ;;
  1|true|True|yes|YES)
    echo "Explicit ESP32-S3 v0.9.8 prebuilt flash requested."
    flash_prebuilt
    ;;
  auto|AUTO)
    if [[ -z "${ESP32_PORT}" ]]; then
      echo "ESP32-S3 port not discovered; auto policy preserves the connected firmware."
    else
      set +e
      python3 scripts/probe_esp32_dualeye_version.py --port "${ESP32_PORT}"
      probe_rc=$?
      set -e
      case "${probe_rc}" in
        0)
          echo "ESP32-S3 reports current v0.9.8 wake-session behavior; preserving firmware."
          ;;
        10)
          echo "ESP32-S3 was positively identified as older than v0.9.8; flashing the verified prebuilt image."
          flash_prebuilt
          ;;
        *)
          echo "ESP32-S3 version could not be positively identified; auto policy preserves firmware."
          echo "Use FLASH_ESP32=1 for an explicit verified v0.9.8 reflash."
          ;;
      esac
    fi
    ;;
  *)
    echo "Unknown FLASH_ESP32=${FLASH_POLICY}. Use auto, 0, or 1." >&2
    exit 2
    ;;
esac

# The v0.9.8 wrapper owns the ESP32 decision and flash. The established installer
# then performs the Pi, Heltec, service, voice, menu, sync, CAN, and readiness steps
# without rebuilding or reflashing ESP32 firmware from source.
FLASH_ESP32=0 ESP32_PORT="${ESP32_PORT}" bash "${BASE_INSTALLER}" "$@"
