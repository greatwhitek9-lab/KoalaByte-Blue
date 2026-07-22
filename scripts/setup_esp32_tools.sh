#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_ESP32_TOOLS="${INSTALL_ESP32_TOOLS:-auto}"
STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS:-0}"
CHECK_ONLY=0

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
  INSTALL_ESP32_TOOLS   auto/1/0. Default: auto. Installs PlatformIO in the isolated venv when missing.
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

install_platformio_venv() {
  echo "PlatformIO not found. Installing into isolated venv: ${ESP32_TOOLS_VENV}"

  if ! run_as_install_user "${PYTHON_BIN}" -m venv "${ESP32_TOOLS_VENV}"; then
    echo "Unable to create the PlatformIO virtual environment." >&2
    echo "Install venv support first: sudo apt install -y python3-venv python3-full" >&2
    return 1
  fi

  run_as_install_user "${ESP32_TOOLS_VENV}/bin/python" -m pip install --upgrade pip
  run_as_install_user "${ESP32_TOOLS_VENV}/bin/python" -m pip install --upgrade platformio
  run_as_install_user mkdir -p "${ESP32_USER_BIN}"
  run_as_install_user ln -sfn "${ESP32_TOOLS_VENV}/bin/pio" "${ESP32_USER_BIN}/pio"
  run_as_install_user ln -sfn "${ESP32_TOOLS_VENV}/bin/platformio" "${ESP32_USER_BIN}/platformio"
  export PATH="${ESP32_USER_BIN}:${ESP32_TOOLS_VENV}/bin:${PATH}"
}

echo "== KoalaByte Blue ESP32 tool setup =="
echo "Repository root: ${REPO_ROOT}"
echo "Install user: ${INSTALL_USER}"
echo "PlatformIO venv: ${ESP32_TOOLS_VENV}"
echo "INSTALL_ESP32_TOOLS=${INSTALL_ESP32_TOOLS} STRICT_ESP32_TOOLS=${STRICT_ESP32_TOOLS}"

if ! command -v pio >/dev/null 2>&1 && [[ "${CHECK_ONLY}" != "1" ]] && install_enabled; then
  install_platformio_venv || true
fi

if command -v pio >/dev/null 2>&1; then
  echo "pio: $(command -v pio)"
  pio --version || true
else
  echo "PlatformIO/pio: MISSING" >&2
  echo "Install manually in an isolated environment:" >&2
  echo "  ${PYTHON_BIN} -m venv ${ESP32_TOOLS_VENV}" >&2
  echo "  ${ESP32_TOOLS_VENV}/bin/python -m pip install --upgrade platformio" >&2
  if strict_enabled; then
    exit 1
  fi
fi

echo "ESP32 tool setup/check complete."
