#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

echo "== Heltec OLED koala display firmware =="
STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS:-1}" bash scripts/setup_esp32_tools.sh

if [[ "${BUILD_ONLY:-0}" == "1" || "${1:-}" == "--build-only" ]]; then
  pio run -d firmware/heltec-mouth
  exit 0
fi

if [[ -n "${HELTEC_PORT:-}" ]]; then
  pio run -d firmware/heltec-mouth -t upload --upload-port "${HELTEC_PORT}"
else
  pio run -d firmware/heltec-mouth -t upload
fi

if [[ "${NO_MONITOR:-1}" != "1" ]]; then
  if [[ -n "${HELTEC_PORT:-}" ]]; then
    pio device monitor -d firmware/heltec-mouth -p "${HELTEC_PORT}" -b "${KOALABYTE_FACE_BAUD:-115200}"
  else
    pio device monitor -d firmware/heltec-mouth -b "${KOALABYTE_FACE_BAUD:-115200}"
  fi
fi
