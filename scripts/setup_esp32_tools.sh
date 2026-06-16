#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_ESP32_TOOLS="${INSTALL_ESP32_TOOLS:-auto}"
STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS:-0}"
CHECK_ONLY=0

usage() {
  cat <<'EOF'
KoalaByte Blue ESP32/PlatformIO setup helper

Usage:
  bash scripts/setup_esp32_tools.sh
  STRICT_ESP32_TOOLS=1 bash scripts/setup_esp32_tools.sh
  bash scripts/setup_esp32_tools.sh --check-only

Environment:
  PYTHON_BIN            Python executable used for pip installs. Default: python3
  INSTALL_ESP32_TOOLS   auto/1/0. Default: auto. Attempts pip install of PlatformIO when missing.
  STRICT_ESP32_TOOLS    1 fails if PlatformIO is still missing after setup. Default: 0
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only)
      CHECK_ONLY=1
      INSTALL_ESP32_TOOLS=0
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

cd "${REPO_ROOT}"
export PATH="${HOME}/.local/bin:${PATH}"

install_enabled() {
  case "${INSTALL_ESP32_TOOLS}" in
    1|true|True|yes|YES|auto|AUTO) return 0 ;;
    *) return 1 ;;
  esac
}

strict_enabled() {
  [[ "${STRICT_ESP32_TOOLS}" == "1" ]]
}

echo "== KoalaByte Blue ESP32 tool setup =="
echo "Repository root: ${REPO_ROOT}"
echo "INSTALL_ESP32_TOOLS=${INSTALL_ESP32_TOOLS} STRICT_ESP32_TOOLS=${STRICT_ESP32_TOOLS}"

if ! command -v pio >/dev/null 2>&1 && [[ "${CHECK_ONLY}" != "1" ]] && install_enabled; then
  echo "PlatformIO not found. Attempting to install PlatformIO with pip..."
  "${PYTHON_BIN}" -m pip install --user --upgrade platformio || true
  export PATH="${HOME}/.local/bin:${PATH}"
fi

if command -v pio >/dev/null 2>&1; then
  echo "pio: $(command -v pio)"
  pio --version || true
else
  echo "PlatformIO/pio: MISSING" >&2
  echo "Install manually: ${PYTHON_BIN} -m pip install --user platformio" >&2
  if strict_enabled; then
    exit 1
  fi
fi

echo "ESP32 tool setup/check complete."
