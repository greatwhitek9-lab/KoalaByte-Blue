#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_NRF_TOOLS="${INSTALL_NRF_TOOLS:-auto}"
STRICT_NRF_TOOLS="${STRICT_NRF_TOOLS:-0}"
SETUP_NCS_TOOLCHAIN="${SETUP_NCS_TOOLCHAIN:-0}"
NEED_WEST=1
NEED_NRFUTIL=0
CHECK_ONLY=0

usage() {
  cat <<'EOF'
KoalaByte Blue nRF tool setup helper

Usage:
  bash scripts/setup_nrf_tools.sh
  STRICT_NRF_TOOLS=1 bash scripts/setup_nrf_tools.sh
  bash scripts/setup_nrf_tools.sh --west-only
  bash scripts/setup_nrf_tools.sh --nrfutil-only
  bash scripts/setup_nrf_tools.sh --with-nrfutil
  bash scripts/setup_nrf_tools.sh --full-toolchain
  bash scripts/setup_nrf_tools.sh --check-only

Environment:
  PYTHON_BIN           Python executable used for pip installs. Default: python3
  INSTALL_NRF_TOOLS    auto/1/0. Default: auto. When enabled, attempts pip install for missing tools.
  STRICT_NRF_TOOLS     1 fails if required tools are still missing after setup. Default: 0
  SETUP_NCS_TOOLCHAIN  1 also runs scripts/setup_nrf_connect_sdk_toolchain.sh.
  NRFUTIL_INSTALL_CMD  Optional custom command to install nrfutil if pip install is not desired.

Tools checked:
  west                 Zephyr/nRF Connect SDK build tool. Required for combined-safe T114 firmware builds.
  nrfutil              Optional legacy DFU helper for dongle/HCI workflows. Not required for the default combined-safe T114 profile.
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
    --with-nrfutil)
      NEED_WEST=1
      NEED_NRFUTIL=1
      ;;
    --full-toolchain)
      SETUP_NCS_TOOLCHAIN=1
      NEED_WEST=1
      NEED_NRFUTIL=0
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

python_in_venv() {
  "${PYTHON_BIN}" - <<'PY'
import sys
raise SystemExit(0 if sys.prefix != sys.base_prefix else 1)
PY
}

pip_install() {
  local package="$1"
  if python_in_venv; then
    "${PYTHON_BIN}" -m pip install --upgrade "$package"
  else
    "${PYTHON_BIN}" -m pip install --user --upgrade "$package"
  fi
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
    echo "nrfutil not found. Attempting to install nrfutil with pip."
    echo "Note: nrfutil is optional for the default combined-safe T114 profile and may have older Python dependency pins."
    pip_install nrfutil || true
  fi
  export PATH="${HOME}/.local/bin:${PATH}"
}

failures=()

echo "== KoalaByte Blue nRF tool setup =="
echo "Repository root: ${REPO_ROOT}"
echo "INSTALL_NRF_TOOLS=${INSTALL_NRF_TOOLS} STRICT_NRF_TOOLS=${STRICT_NRF_TOOLS} SETUP_NCS_TOOLCHAIN=${SETUP_NCS_TOOLCHAIN} NEED_WEST=${NEED_WEST} NEED_NRFUTIL=${NEED_NRFUTIL}"

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
  echo "Missing requested nRF tool(s): ${failures[*]}" >&2
  echo "For the default combined-safe T114 firmware, west + NCS/Zephyr are required; nrfutil is optional unless explicitly requested." >&2
  if strict_enabled; then
    exit 1
  fi
fi

if [[ "${SETUP_NCS_TOOLCHAIN}" == "1" && "${CHECK_ONLY}" != "1" ]]; then
  echo
  echo "== Full nRF Connect SDK / Zephyr toolchain setup =="
  STRICT_NCS_TOOLCHAIN="${STRICT_NRF_TOOLS}" PYTHON_BIN="${PYTHON_BIN}" bash "${REPO_ROOT}/scripts/setup_nrf_connect_sdk_toolchain.sh"
fi

echo "nRF tool setup/check complete."
