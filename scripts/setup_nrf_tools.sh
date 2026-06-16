#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_NRF_TOOLS="${INSTALL_NRF_TOOLS:-auto}"
STRICT_NRF_TOOLS="${STRICT_NRF_TOOLS:-0}"
NEED_WEST=1
NEED_NRFUTIL=1
CHECK_ONLY=0

usage() {
  cat <<'EOF'
KoalaByte Blue nRF tool setup helper

Usage:
  bash scripts/setup_nrf_tools.sh
  STRICT_NRF_TOOLS=1 bash scripts/setup_nrf_tools.sh
  bash scripts/setup_nrf_tools.sh --west-only
  bash scripts/setup_nrf_tools.sh --nrfutil-only
  bash scripts/setup_nrf_tools.sh --check-only

Environment:
  PYTHON_BIN           Python executable used for pip installs. Default: python3
  INSTALL_NRF_TOOLS    auto/1/0. Default: auto. When enabled, attempts pip install for missing tools.
  STRICT_NRF_TOOLS     1 fails if required tools are still missing after setup. Default: 0
  NRFUTIL_INSTALL_CMD  Optional custom command to install nrfutil if pip install is not desired.

Tools checked:
  west                 Zephyr/nRF Connect SDK build tool
  nrfutil              Nordic DFU package/USB serial flashing tool
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --west-only)
      NEED_WEST=1
      NEED_NRFUTIL=0
      ;;
    --nrfutil-only)
      NEED_WEST=0
      NEED_NRFUTIL=1
      ;;
    --check-only)
      CHECK_ONLY=1
      INSTALL_NRF_TOOLS=0
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
  case "${INSTALL_NRF_TOOLS}" in
    1|true|True|yes|YES|auto|AUTO) return 0 ;;
    *) return 1 ;;
  esac
}

strict_enabled() {
  [[ "${STRICT_NRF_TOOLS}" == "1" ]]
}

have_tool() {
  command -v "$1" >/dev/null 2>&1
}

pip_install() {
  local package="$1"
  "${PYTHON_BIN}" -m pip install --user --upgrade "$package"
}

attempt_install_west() {
  echo "west not found. Attempting to install west with pip..."
  pip_install west || true
  export PATH="${HOME}/.local/bin:${PATH}"
}

attempt_install_nrfutil() {
  if [[ -n "${NRFUTIL_INSTALL_CMD:-}" ]]; then
    echo "nrfutil not found. Running NRFUTIL_INSTALL_CMD..."
    bash -lc "${NRFUTIL_INSTALL_CMD}" || true
  else
    echo "nrfutil not found. Attempting to install nrfutil with pip..."
    pip_install nrfutil || true
  fi
  export PATH="${HOME}/.local/bin:${PATH}"
}

failures=()

echo "== KoalaByte Blue nRF tool setup =="
echo "Repository root: ${REPO_ROOT}"
echo "INSTALL_NRF_TOOLS=${INSTALL_NRF_TOOLS} STRICT_NRF_TOOLS=${STRICT_NRF_TOOLS}"

if [[ "${NEED_WEST}" == "1" ]]; then
  if ! have_tool west && [[ "${CHECK_ONLY}" != "1" ]] && install_enabled; then
    attempt_install_west
  fi
  if have_tool west; then
    echo "west: $(command -v west)"
    west --version || true
  else
    failures+=("west")
    echo "west: MISSING" >&2
  fi
fi

if [[ "${NEED_NRFUTIL}" == "1" ]]; then
  if ! have_tool nrfutil && [[ "${CHECK_ONLY}" != "1" ]] && install_enabled; then
    attempt_install_nrfutil
  fi
  if have_tool nrfutil; then
    echo "nrfutil: $(command -v nrfutil)"
    nrfutil version || nrfutil --version || true
  else
    failures+=("nrfutil")
    echo "nrfutil: MISSING" >&2
  fi
fi

if (( ${#failures[@]} > 0 )); then
  echo "Missing required nRF tool(s): ${failures[*]}" >&2
  echo "Install nRF Connect SDK/west and Nordic nrfutil, then rerun the flash/cache command." >&2
  echo "Override nrfutil installation with NRFUTIL_INSTALL_CMD='your install command' if needed." >&2
  if strict_enabled; then
    exit 1
  fi
fi

echo "nRF tool setup/check complete."
