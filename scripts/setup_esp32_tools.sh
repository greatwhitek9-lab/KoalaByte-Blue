#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_ESP32_TOOLS="${INSTALL_ESP32_TOOLS:-auto}"
STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS:-0}"
CHECK_ONLY=0
EDGE_TTS_VERSION="${EDGE_TTS_VERSION:-7.2.8}"

INSTALL_USER="${SUDO_USER:-${USER:-$(id -un)}}"
INSTALL_HOME="${HOME}"
if command -v getent >/dev/null 2>&1; then
  RESOLVED_HOME="$(getent passwd "${INSTALL_USER}" | cut -d: -f6 || true)"
  if [[ -n "${RESOLVED_HOME}" ]]; then
    INSTALL_HOME="${RESOLVED_HOME}"
  fi
fi

ESP32_TOOLS_VENV="${ESP32_TOOLS_VENV:-${INSTALL_HOME}/.venvs/platformio}"
ESP32_USER_BIN="${INSTALL_HOME}/.local/bin"

usage() {
  cat <<'EOF'
KoalaByte Blue ESP32/PlatformIO setup helper

Usage:
  bash scripts/setup_esp32_tools.sh
  STRICT_ESP32_TOOLS=1 bash scripts/setup_esp32_tools.sh
  bash scripts/setup_esp32_tools.sh --check-only

Environment:
  PYTHON_BIN            Python executable used to create the isolated venv. Default: python3
  ESP32_TOOLS_VENV      PlatformIO virtual environment. Default: ~/.venvs/platformio
  INSTALL_ESP32_TOOLS   auto/1/0. Default: auto. Installs PlatformIO and voice tools when missing.
  STRICT_ESP32_TOOLS    1 fails if required ESP32 build tools are missing. Default: 0
  EDGE_TTS_VERSION      Pinned edge-tts version used for Australian voice clips. Default: 7.2.8
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
export PATH="${ESP32_USER_BIN}:${ESP32_TOOLS_VENV}/bin:${PATH}"

install_enabled() {
  case "${INSTALL_ESP32_TOOLS}" in
    1|true|True|yes|YES|auto|AUTO) return 0 ;;
    *) return 1 ;;
  esac
}

strict_enabled() {
  [[ "${STRICT_ESP32_TOOLS}" == "1" ]]
}

run_as_install_user() {
  if [[ "$(id -u)" == "0" && "${INSTALL_USER}" != "root" ]]; then
    sudo -u "${INSTALL_USER}" -H env HOME="${INSTALL_HOME}" "$@"
  else
    "$@"
  fi
}

ensure_venv() {
  if [[ -x "${ESP32_TOOLS_VENV}/bin/python" ]]; then
    return 0
  fi
  echo "Creating isolated ESP32 tools venv: ${ESP32_TOOLS_VENV}"
  if ! run_as_install_user "${PYTHON_BIN}" -m venv "${ESP32_TOOLS_VENV}"; then
    echo "Unable to create the ESP32 tools virtual environment." >&2
    echo "Install venv support first: sudo apt install -y python3-venv python3-full" >&2
    return 1
  fi
}

install_python_tools() {
  ensure_venv || return 1
  run_as_install_user "${ESP32_TOOLS_VENV}/bin/python" -m pip install --upgrade pip
  run_as_install_user "${ESP32_TOOLS_VENV}/bin/python" -m pip install --upgrade platformio "edge-tts==${EDGE_TTS_VERSION}"
  run_as_install_user mkdir -p "${ESP32_USER_BIN}"
  run_as_install_user ln -sfn "${ESP32_TOOLS_VENV}/bin/pio" "${ESP32_USER_BIN}/pio"
  run_as_install_user ln -sfn "${ESP32_TOOLS_VENV}/bin/platformio" "${ESP32_USER_BIN}/platformio"
  run_as_install_user ln -sfn "${ESP32_TOOLS_VENV}/bin/edge-tts" "${ESP32_USER_BIN}/edge-tts"
  export PATH="${ESP32_USER_BIN}:${ESP32_TOOLS_VENV}/bin:${PATH}"
}

ensure_ffmpeg() {
  command -v ffmpeg >/dev/null 2>&1 && return 0
  [[ "${CHECK_ONLY}" == "1" ]] && return 1
  install_enabled || return 1
  echo "ffmpeg not found. Installing system package..."
  if ! command -v apt-get >/dev/null 2>&1; then
    return 1
  fi
  if [[ "$(id -u)" == "0" ]]; then
    apt-get update
    apt-get install -y ffmpeg
  elif command -v sudo >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y ffmpeg
  else
    return 1
  fi
}

echo "== KoalaByte Blue ESP32 tool setup =="
echo "Repository root: ${REPO_ROOT}"
echo "Install user: ${INSTALL_USER}"
echo "PlatformIO venv: ${ESP32_TOOLS_VENV}"
echo "INSTALL_ESP32_TOOLS=${INSTALL_ESP32_TOOLS} STRICT_ESP32_TOOLS=${STRICT_ESP32_TOOLS}"

if [[ "${CHECK_ONLY}" != "1" ]] && install_enabled; then
  if [[ ! -x "${ESP32_TOOLS_VENV}/bin/pio" || ! -x "${ESP32_TOOLS_VENV}/bin/edge-tts" ]]; then
    install_python_tools || true
  fi
fi

missing=0
if [[ -x "${ESP32_TOOLS_VENV}/bin/pio" ]]; then
  echo "pio: ${ESP32_TOOLS_VENV}/bin/pio"
  "${ESP32_TOOLS_VENV}/bin/pio" --version || true
else
  echo "PlatformIO/pio: MISSING" >&2
  missing=1
fi

if [[ -x "${ESP32_TOOLS_VENV}/bin/edge-tts" ]]; then
  echo "edge-tts: ${ESP32_TOOLS_VENV}/bin/edge-tts"
else
  echo "edge-tts: MISSING" >&2
  missing=1
fi

if ensure_ffmpeg && command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg: $(command -v ffmpeg)"
else
  echo "ffmpeg: MISSING" >&2
  missing=1
fi

if [[ "${missing}" == "1" ]] && strict_enabled; then
  exit 1
fi

echo "ESP32 tool setup/check complete."
