#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
NCS_WORKSPACE="${NCS_WORKSPACE:-${HOME}/ncs}"
NCS_REVISION="${NCS_REVISION:-v2.9.0}"
ZEPHYR_SDK_VERSION="${ZEPHYR_SDK_VERSION:-0.17.0}"
ZEPHYR_SDK_INSTALL_DIR="${ZEPHYR_SDK_INSTALL_DIR:-${HOME}/zephyr-sdk-${ZEPHYR_SDK_VERSION}}"
INSTALL_NCS_TOOLCHAIN="${INSTALL_NCS_TOOLCHAIN:-auto}"
STRICT_NCS_TOOLCHAIN="${STRICT_NCS_TOOLCHAIN:-0}"
CHECK_ONLY=0
SKIP_ZEPHYR_SDK="${SKIP_ZEPHYR_SDK:-0}"
SKIP_NCS_UPDATE="${SKIP_NCS_UPDATE:-0}"
VALIDATE_BUILD="${VALIDATE_BUILD:-0}"

usage() {
  cat <<'EOF'
KoalaByte Blue full Nordic nRF Connect SDK / Zephyr toolchain setup helper

Usage:
  bash scripts/setup_nrf_connect_sdk_toolchain.sh
  STRICT_NCS_TOOLCHAIN=1 bash scripts/setup_nrf_connect_sdk_toolchain.sh
  NCS_WORKSPACE=$HOME/ncs NCS_REVISION=v2.9.0 bash scripts/setup_nrf_connect_sdk_toolchain.sh
  bash scripts/setup_nrf_connect_sdk_toolchain.sh --check-only
  VALIDATE_BUILD=1 bash scripts/setup_nrf_connect_sdk_toolchain.sh

Environment:
  NCS_WORKSPACE            nRF Connect SDK west workspace. Default: $HOME/ncs
  NCS_REVISION             sdk-nrf revision/tag. Default: v2.9.0
  ZEPHYR_SDK_VERSION       Zephyr SDK version. Default: 0.17.0
  ZEPHYR_SDK_INSTALL_DIR   Zephyr SDK install directory. Default: $HOME/zephyr-sdk-$ZEPHYR_SDK_VERSION
  INSTALL_NCS_TOOLCHAIN    auto/1/0. Default: auto. Downloads/updates NCS and Zephyr SDK when enabled.
  STRICT_NCS_TOOLCHAIN     1 fails when the toolchain is incomplete. Default: 0
  SKIP_ZEPHYR_SDK          1 skips Zephyr SDK download/install.
  SKIP_NCS_UPDATE          1 skips west update when workspace already exists.
  VALIDATE_BUILD           1 validates KoalaByte Lab Zephyr build after setup.

Outputs:
  logs/nrf_connect_sdk_env.sh       source-able environment file
  logs/nrf_connect_sdk_status.json  status/report JSON
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only)
      CHECK_ONLY=1
      INSTALL_NCS_TOOLCHAIN=0
      ;;
    --validate-build)
      VALIDATE_BUILD=1
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
  case "${INSTALL_NCS_TOOLCHAIN}" in
    1|true|True|yes|YES|auto|AUTO) return 0 ;;
    *) return 1 ;;
  esac
}

strict_enabled() {
  [[ "${STRICT_NCS_TOOLCHAIN}" == "1" ]]
}

have_tool() {
  command -v "$1" >/dev/null 2>&1
}

host_arch() {
  case "$(uname -m)" in
    x86_64|amd64) echo "x86_64" ;;
    aarch64|arm64) echo "aarch64" ;;
    *) uname -m ;;
  esac
}

write_status() {
  local status="$1"
  local message="$2"
  mkdir -p "${REPO_ROOT}/logs"
  cat > "${REPO_ROOT}/logs/nrf_connect_sdk_status.json" <<EOF
{
  "status": "${status}",
  "message": "${message}",
  "ncs_workspace": "${NCS_WORKSPACE}",
  "ncs_revision": "${NCS_REVISION}",
  "zephyr_sdk_version": "${ZEPHYR_SDK_VERSION}",
  "zephyr_sdk_install_dir": "${ZEPHYR_SDK_INSTALL_DIR}",
  "zephyr_base": "${NCS_WORKSPACE}/zephyr",
  "env_file": "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh",
  "west_available": $(have_tool west && echo true || echo false),
  "nrfutil_available": $(have_tool nrfutil && echo true || echo false),
  "ncs_workspace_exists": $([[ -d "${NCS_WORKSPACE}/.west" ]] && echo true || echo false),
  "zephyr_base_exists": $([[ -d "${NCS_WORKSPACE}/zephyr" ]] && echo true || echo false),
  "zephyr_sdk_exists": $([[ -d "${ZEPHYR_SDK_INSTALL_DIR}" ]] && echo true || echo false),
  "updated_at": $(date +%s)
}
EOF
}

write_env_file() {
  mkdir -p "${REPO_ROOT}/logs"
  cat > "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh" <<EOF
# KoalaByte Blue nRF Connect SDK / Zephyr environment
# Source this before manual west builds:
#   source ${REPO_ROOT}/logs/nrf_connect_sdk_env.sh
export NCS_WORKSPACE="${NCS_WORKSPACE}"
export ZEPHYR_BASE="${NCS_WORKSPACE}/zephyr"
export ZEPHYR_TOOLCHAIN_VARIANT="zephyr"
export ZEPHYR_SDK_INSTALL_DIR="${ZEPHYR_SDK_INSTALL_DIR}"
export PATH="${NCS_WORKSPACE}/.venv/bin:${HOME}/.local/bin:\$PATH"
EOF
}

fail_or_warn() {
  local message="$1"
  echo "${message}" >&2
  write_status "incomplete" "${message}"
  if strict_enabled; then
    exit 1
  fi
}

install_zephyr_sdk() {
  if [[ "${SKIP_ZEPHYR_SDK}" == "1" ]]; then
    echo "Skipping Zephyr SDK install because SKIP_ZEPHYR_SDK=1."
    return 0
  fi
  if [[ -d "${ZEPHYR_SDK_INSTALL_DIR}" ]]; then
    echo "Zephyr SDK already exists: ${ZEPHYR_SDK_INSTALL_DIR}"
    return 0
  fi
  local arch
  arch="$(host_arch)"
  local archive="zephyr-sdk-${ZEPHYR_SDK_VERSION}_linux-${arch}.tar.xz"
  local url="https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v${ZEPHYR_SDK_VERSION}/${archive}"
  local tmpdir
  tmpdir="$(mktemp -d)"
  echo "Downloading Zephyr SDK ${ZEPHYR_SDK_VERSION} for ${arch}: ${url}"
  if ! curl -L --fail -o "${tmpdir}/${archive}" "${url}"; then
    rm -rf "${tmpdir}"
    fail_or_warn "Zephyr SDK download failed for architecture ${arch}. Set SKIP_ZEPHYR_SDK=1 if you provide your own toolchain."
    return 0
  fi
  mkdir -p "$(dirname "${ZEPHYR_SDK_INSTALL_DIR}")"
  tar -xJf "${tmpdir}/${archive}" -C "$(dirname "${ZEPHYR_SDK_INSTALL_DIR}")"
  rm -rf "${tmpdir}"
  if [[ -x "${ZEPHYR_SDK_INSTALL_DIR}/setup.sh" ]]; then
    echo "Running Zephyr SDK setup for ARM target and host tools."
    "${ZEPHYR_SDK_INSTALL_DIR}/setup.sh" -t arm-zephyr-eabi -h -c || true
  fi
}

install_ncs_workspace() {
  mkdir -p "$(dirname "${NCS_WORKSPACE}")"
  if [[ ! -d "${NCS_WORKSPACE}/.west" ]]; then
    echo "Creating nRF Connect SDK west workspace: ${NCS_WORKSPACE} (${NCS_REVISION})"
    west init -m https://github.com/nrfconnect/sdk-nrf --mr "${NCS_REVISION}" "${NCS_WORKSPACE}"
  else
    echo "nRF Connect SDK west workspace already exists: ${NCS_WORKSPACE}"
    if [[ "${SKIP_NCS_UPDATE}" != "1" ]]; then
      echo "Updating workspace manifest to requested revision: ${NCS_REVISION}"
      cd "${NCS_WORKSPACE}/nrf"
      git fetch --tags origin || true
      git checkout "${NCS_REVISION}" || true
      cd "${NCS_WORKSPACE}"
    fi
  fi
  cd "${NCS_WORKSPACE}"
  if [[ "${SKIP_NCS_UPDATE}" != "1" ]]; then
    west update
  fi
  west zephyr-export
}

install_python_requirements() {
  echo "Creating/updating nRF Connect SDK Python venv: ${NCS_WORKSPACE}/.venv"
  "${PYTHON_BIN}" -m venv "${NCS_WORKSPACE}/.venv"
  # shellcheck disable=SC1091
  source "${NCS_WORKSPACE}/.venv/bin/activate"
  python -m pip install --upgrade pip wheel setuptools west
  cd "${NCS_WORKSPACE}"
  for req in \
    "zephyr/scripts/requirements.txt" \
    "nrf/scripts/requirements.txt" \
    "bootloader/mcuboot/scripts/requirements.txt"; do
    if [[ -f "${req}" ]]; then
      echo "Installing Python requirements: ${req}"
      python -m pip install -r "${req}"
    fi
  done
}

validate_build() {
  if [[ "${VALIDATE_BUILD}" != "1" ]]; then
    return 0
  fi
  echo "Validating KoalaByte Lab Zephyr build with configured toolchain."
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh"
  cd "${NCS_WORKSPACE}"
  west build -b nrf52840dongle_nrf52840 "${REPO_ROOT}/firmware/nrf52840-dongle-ear-tag-tx-lab" -d "${REPO_ROOT}/build/nrf52840-dongle-lab"
}

echo "== KoalaByte Blue full nRF Connect SDK / Zephyr toolchain setup =="
echo "Repository root: ${REPO_ROOT}"
echo "NCS_WORKSPACE=${NCS_WORKSPACE}"
echo "NCS_REVISION=${NCS_REVISION}"
echo "ZEPHYR_SDK_VERSION=${ZEPHYR_SDK_VERSION}"
echo "ZEPHYR_SDK_INSTALL_DIR=${ZEPHYR_SDK_INSTALL_DIR}"

write_env_file

if [[ "${CHECK_ONLY}" == "1" ]]; then
  missing=()
  have_tool west || missing+=("west")
  have_tool nrfutil || missing+=("nrfutil")
  [[ -d "${NCS_WORKSPACE}/.west" ]] || missing+=("NCS workspace")
  [[ -d "${NCS_WORKSPACE}/zephyr" ]] || missing+=("Zephyr checkout")
  [[ -d "${ZEPHYR_SDK_INSTALL_DIR}" ]] || missing+=("Zephyr SDK")
  if (( ${#missing[@]} > 0 )); then
    fail_or_warn "nRF Connect SDK toolchain check found missing item(s): ${missing[*]}"
  else
    write_status "success" "nRF Connect SDK toolchain check passed."
  fi
  exit 0
fi

if ! install_enabled; then
  echo "Full NCS toolchain install/update disabled by INSTALL_NCS_TOOLCHAIN=${INSTALL_NCS_TOOLCHAIN}."
  write_status "skipped" "NCS toolchain install/update skipped."
  exit 0
fi

bash "${REPO_ROOT}/scripts/setup_system_packages.sh"
STRICT_NRF_TOOLS="${STRICT_NCS_TOOLCHAIN}" bash "${REPO_ROOT}/scripts/setup_nrf_tools.sh"

if ! have_tool west; then
  fail_or_warn "west is still missing after setup_nrf_tools.sh."
  exit 0
fi

install_ncs_workspace
install_python_requirements
install_zephyr_sdk
write_env_file
validate_build
write_status "success" "nRF Connect SDK / Zephyr toolchain setup complete."

echo "nRF Connect SDK / Zephyr toolchain setup complete."
echo "Source environment for manual builds:"
echo "  source ${REPO_ROOT}/logs/nrf_connect_sdk_env.sh"
