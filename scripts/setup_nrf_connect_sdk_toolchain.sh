#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
NCS_WORKSPACE="${NCS_WORKSPACE:-${HOME}/ncs}"
NCS_REVISION="${NCS_REVISION:-v2.9.0}"
ZEPHYR_SDK_VERSION="${ZEPHYR_SDK_VERSION:-0.17.0}"
ZEPHYR_SDK_INSTALL_DIR="${ZEPHYR_SDK_INSTALL_DIR:-${HOME}/zephyr-sdk-${ZEPHYR_SDK_VERSION}}"
ZEPHYR_SDK_DOWNLOAD_DIR="${ZEPHYR_SDK_DOWNLOAD_DIR:-${HOME}/.cache/koalabyte/zephyr-sdk}"
ZEPHYR_SDK_MIN_FREE_KB="${ZEPHYR_SDK_MIN_FREE_KB:-8388608}"
INSTALL_NCS_TOOLCHAIN="${INSTALL_NCS_TOOLCHAIN:-auto}"
STRICT_NCS_TOOLCHAIN="${STRICT_NCS_TOOLCHAIN:-0}"
CHECK_ONLY=0
SKIP_ZEPHYR_SDK="${SKIP_ZEPHYR_SDK:-0}"
SKIP_NCS_UPDATE="${SKIP_NCS_UPDATE:-0}"
VALIDATE_BUILD="${VALIDATE_BUILD:-0}"
PIP_RETRIES="${PIP_RETRIES:-25}"
PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT:-300}"

usage() {
  cat <<'EOF'
KoalaByte Blue full Nordic nRF Connect SDK / Zephyr toolchain setup helper

Usage:
  bash scripts/setup_nrf_connect_sdk_toolchain.sh
  STRICT_NCS_TOOLCHAIN=1 bash scripts/setup_nrf_connect_sdk_toolchain.sh
  bash scripts/setup_nrf_connect_sdk_toolchain.sh --check-only
  VALIDATE_BUILD=1 bash scripts/setup_nrf_connect_sdk_toolchain.sh

This helper supports Raspberry Pi OS Bookworm and Trixie, resumes existing west
workspaces and interrupted Zephyr SDK downloads, validates CMake/Ninja before
building, and retries transient pip network failures.

The Zephyr SDK archive is downloaded under:
  ZEPHYR_SDK_DOWNLOAD_DIR=$HOME/.cache/koalabyte/zephyr-sdk

This avoids RAM-backed /tmp filesystems that are too small for the SDK archive.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) CHECK_ONLY=1; INSTALL_NCS_TOOLCHAIN=0 ;;
    --validate-build) VALIDATE_BUILD=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

cd "${REPO_ROOT}"
export PATH="${NCS_WORKSPACE}/.venv/bin:${REPO_ROOT}/pi-companion/.venv/bin:${HOME}/.local/bin:/usr/bin:/bin:${PATH}"
export PIP_RETRIES PIP_DEFAULT_TIMEOUT

install_enabled() {
  case "${INSTALL_NCS_TOOLCHAIN}" in
    1|true|True|yes|YES|auto|AUTO) return 0 ;;
    *) return 1 ;;
  esac
}

strict_enabled() { [[ "${STRICT_NCS_TOOLCHAIN}" == "1" ]]; }
have_tool() { command -v "$1" >/dev/null 2>&1; }

host_arch() {
  case "$(uname -m)" in
    x86_64|amd64) echo x86_64 ;;
    aarch64|arm64) echo aarch64 ;;
    *) uname -m ;;
  esac
}

write_status() {
  local status="$1" message="$2"
  mkdir -p "${REPO_ROOT}/logs"
  cat > "${REPO_ROOT}/logs/nrf_connect_sdk_status.json" <<EOF
{
  "status": "${status}",
  "message": "${message}",
  "ncs_workspace": "${NCS_WORKSPACE}",
  "ncs_revision": "${NCS_REVISION}",
  "zephyr_sdk_version": "${ZEPHYR_SDK_VERSION}",
  "zephyr_sdk_install_dir": "${ZEPHYR_SDK_INSTALL_DIR}",
  "zephyr_sdk_download_dir": "${ZEPHYR_SDK_DOWNLOAD_DIR}",
  "zephyr_base": "${NCS_WORKSPACE}/zephyr",
  "env_file": "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh",
  "west_available": $(have_tool west && echo true || echo false),
  "cmake_available": $(have_tool cmake && echo true || echo false),
  "ninja_available": $(have_tool ninja && echo true || echo false),
  "ncs_workspace_exists": $([[ -d "${NCS_WORKSPACE}/.west" ]] && echo true || echo false),
  "zephyr_base_exists": $([[ -d "${NCS_WORKSPACE}/zephyr" ]] && echo true || echo false),
  "zephyr_sdk_exists": $([[ -x "${ZEPHYR_SDK_INSTALL_DIR}/setup.sh" ]] && echo true || echo false),
  "pip_retries": ${PIP_RETRIES},
  "pip_timeout_seconds": ${PIP_DEFAULT_TIMEOUT},
  "updated_at": $(date +%s)
}
EOF
}

write_env_file() {
  mkdir -p "${REPO_ROOT}/logs"
  cat > "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh" <<EOF
# KoalaByte Blue nRF Connect SDK / Zephyr environment
export NCS_WORKSPACE="${NCS_WORKSPACE}"
export ZEPHYR_BASE="${NCS_WORKSPACE}/zephyr"
export ZEPHYR_TOOLCHAIN_VARIANT="zephyr"
export ZEPHYR_SDK_INSTALL_DIR="${ZEPHYR_SDK_INSTALL_DIR}"
export ZEPHYR_SDK_DOWNLOAD_DIR="${ZEPHYR_SDK_DOWNLOAD_DIR}"
export PATH="${NCS_WORKSPACE}/.venv/bin:${REPO_ROOT}/pi-companion/.venv/bin:${HOME}/.local/bin:/usr/bin:/bin:\$PATH"
export PIP_RETRIES="${PIP_RETRIES}"
export PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT}"
EOF
}

fail_or_warn() {
  local message="$1"
  echo "${message}" >&2
  write_status incomplete "${message}"
  strict_enabled && exit 1
  return 0
}

pip_install_retry() {
  local attempt rc=1
  for attempt in 1 2 3; do
    echo "pip install attempt ${attempt}/3: $*"
    set +e
    python -m pip install --retries "${PIP_RETRIES}" --timeout "${PIP_DEFAULT_TIMEOUT}" --prefer-binary --no-input "$@"
    rc=$?
    set -e
    [[ ${rc} -eq 0 ]] && return 0
    echo "pip attempt ${attempt} failed with exit ${rc}; retrying after $((attempt * 10)) seconds..." >&2
    sleep $((attempt * 10))
  done
  return "${rc}"
}

ensure_build_tools() {
  local missing=()
  have_tool cmake || missing+=(cmake)
  have_tool ninja || missing+=(ninja-build)
  have_tool git || missing+=(git)
  have_tool curl || missing+=(curl)
  if (( ${#missing[@]} > 0 )); then
    echo "Missing required build tool(s): ${missing[*]}" >&2
    if command -v apt-get >/dev/null 2>&1; then
      if [[ "${EUID}" -eq 0 ]]; then
        apt-get update && apt-get install -y "${missing[@]}"
      elif command -v sudo >/dev/null 2>&1; then
        sudo apt-get update && sudo apt-get install -y "${missing[@]}"
      fi
    fi
  fi
  have_tool cmake && have_tool ninja && have_tool git && have_tool curl || {
    fail_or_warn "CMake, Ninja, Git, and curl are required for the NCS toolchain."
    return 1
  }
}

ensure_free_space() {
  local path="$1" minimum_kb="$2" label="$3"
  local available_kb
  mkdir -p "${path}"
  available_kb="$(df -Pk "${path}" | awk 'NR == 2 { print $4 }')"
  if [[ -z "${available_kb}" || ! "${available_kb}" =~ ^[0-9]+$ ]]; then
    fail_or_warn "Could not determine free space for ${label}: ${path}"
    return 1
  fi
  if (( available_kb < minimum_kb )); then
    fail_or_warn "${label} requires at least $((minimum_kb / 1024 / 1024)) GiB free at ${path}; only $((available_kb / 1024 / 1024)) GiB is available."
    return 1
  fi
  echo "${label} free space: $((available_kb / 1024 / 1024)) GiB at ${path}"
}

install_zephyr_sdk() {
  [[ "${SKIP_ZEPHYR_SDK}" == "1" ]] && { echo "Skipping Zephyr SDK install."; return 0; }

  if [[ -x "${ZEPHYR_SDK_INSTALL_DIR}/setup.sh" ]]; then
    echo "Zephyr SDK already exists: ${ZEPHYR_SDK_INSTALL_DIR}"
    return 0
  fi

  if [[ -d "${ZEPHYR_SDK_INSTALL_DIR}" ]]; then
    echo "Removing incomplete Zephyr SDK directory: ${ZEPHYR_SDK_INSTALL_DIR}"
    rm -rf "${ZEPHYR_SDK_INSTALL_DIR}"
  fi

  local arch archive url archive_path partial_path install_parent
  arch="$(host_arch)"
  archive="zephyr-sdk-${ZEPHYR_SDK_VERSION}_linux-${arch}.tar.xz"
  url="https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v${ZEPHYR_SDK_VERSION}/${archive}"
  install_parent="$(dirname "${ZEPHYR_SDK_INSTALL_DIR}")"

  mkdir -p "${ZEPHYR_SDK_DOWNLOAD_DIR}" "${install_parent}"
  ensure_free_space "${install_parent}" "${ZEPHYR_SDK_MIN_FREE_KB}" "Zephyr SDK download and extraction" || return 1

  archive_path="${ZEPHYR_SDK_DOWNLOAD_DIR}/${archive}"
  partial_path="${archive_path}.part"

  if [[ -f "${archive_path}" ]]; then
    echo "Using cached Zephyr SDK archive: ${archive_path}"
  else
    if [[ -f "${partial_path}" ]]; then
      echo "Resuming interrupted Zephyr SDK download: ${partial_path}"
    else
      echo "Downloading Zephyr SDK ${ZEPHYR_SDK_VERSION} for ${arch}"
    fi

    curl -L --fail --retry 10 --retry-all-errors --connect-timeout 30 \
      --continue-at - --output "${partial_path}" "${url}" || {
        fail_or_warn "Zephyr SDK download failed for ${arch}. Partial data was retained for the next retry: ${partial_path}"
        return 1
      }
    mv -f "${partial_path}" "${archive_path}"
  fi

  echo "Validating Zephyr SDK archive..."
  if ! tar -tJf "${archive_path}" >/dev/null; then
    rm -f "${archive_path}" "${partial_path}"
    fail_or_warn "Zephyr SDK archive validation failed; the corrupt cached archive was removed."
    return 1
  fi

  echo "Extracting Zephyr SDK to ${install_parent}"
  tar -xJf "${archive_path}" -C "${install_parent}"
  rm -f "${archive_path}" "${partial_path}"

  [[ -x "${ZEPHYR_SDK_INSTALL_DIR}/setup.sh" ]] || {
    fail_or_warn "Zephyr SDK extraction completed, but setup.sh was not found in ${ZEPHYR_SDK_INSTALL_DIR}."
    return 1
  }
  "${ZEPHYR_SDK_INSTALL_DIR}/setup.sh" -t arm-zephyr-eabi -h -c || true
}

install_ncs_workspace() {
  mkdir -p "$(dirname "${NCS_WORKSPACE}")"
  if [[ ! -d "${NCS_WORKSPACE}/.west" ]]; then
    echo "Creating nRF Connect SDK west workspace: ${NCS_WORKSPACE} (${NCS_REVISION})"
    west init -m https://github.com/nrfconnect/sdk-nrf --mr "${NCS_REVISION}" "${NCS_WORKSPACE}"
  else
    echo "Resuming existing nRF Connect SDK workspace: ${NCS_WORKSPACE}"
  fi
  cd "${NCS_WORKSPACE}"
  if [[ "${SKIP_NCS_UPDATE}" != "1" ]]; then
    west update
  else
    echo "Skipping west update because SKIP_NCS_UPDATE=1."
  fi
  west zephyr-export
}

install_python_requirements() {
  echo "Creating/updating NCS Python venv: ${NCS_WORKSPACE}/.venv"
  if [[ ! -x "${NCS_WORKSPACE}/.venv/bin/python" ]]; then
    "${PYTHON_BIN}" -m venv "${NCS_WORKSPACE}/.venv"
  fi
  source "${NCS_WORKSPACE}/.venv/bin/activate"
  pip_install_retry --upgrade pip wheel setuptools west
  cd "${NCS_WORKSPACE}"
  local req
  for req in zephyr/scripts/requirements.txt nrf/scripts/requirements.txt bootloader/mcuboot/scripts/requirements.txt; do
    if [[ -f "${req}" ]]; then
      echo "Installing Python requirements: ${req}"
      pip_install_retry -r "${req}" || {
        fail_or_warn "Python requirements failed after retries: ${req}"
        return 1
      }
    fi
  done
}

validate_build() {
  [[ "${VALIDATE_BUILD}" == "1" ]] || return 0
  source "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh"
  cd "${NCS_WORKSPACE}"
  west build -b "${T114_BOARD:-heltec_t114_v2/nrf52840}" "${REPO_ROOT}/firmware/t114-combined-safe" -d "${REPO_ROOT}/build/t114-combined-safe"
}

echo "== KoalaByte Blue full nRF Connect SDK / Zephyr toolchain setup =="
echo "Repository root: ${REPO_ROOT}"
echo "NCS_WORKSPACE=${NCS_WORKSPACE}"
echo "NCS_REVISION=${NCS_REVISION}"
echo "ZEPHYR_SDK_VERSION=${ZEPHYR_SDK_VERSION}"
echo "ZEPHYR_SDK_DOWNLOAD_DIR=${ZEPHYR_SDK_DOWNLOAD_DIR}"
echo "PIP_RETRIES=${PIP_RETRIES} PIP_DEFAULT_TIMEOUT=${PIP_DEFAULT_TIMEOUT}"
write_env_file

if [[ "${CHECK_ONLY}" == "1" ]]; then
  missing=()
  have_tool west || missing+=(west)
  have_tool cmake || missing+=(cmake)
  have_tool ninja || missing+=(ninja)
  [[ -d "${NCS_WORKSPACE}/.west" ]] || missing+=("NCS workspace")
  [[ -d "${NCS_WORKSPACE}/zephyr" ]] || missing+=("Zephyr checkout")
  [[ -x "${ZEPHYR_SDK_INSTALL_DIR}/setup.sh" ]] || missing+=("Zephyr SDK")
  if (( ${#missing[@]} > 0 )); then
    fail_or_warn "NCS toolchain check found missing item(s): ${missing[*]}"
  else
    write_status success "nRF Connect SDK toolchain check passed."
  fi
  exit 0
fi

if ! install_enabled; then
  echo "Full NCS toolchain install/update disabled by INSTALL_NCS_TOOLCHAIN=${INSTALL_NCS_TOOLCHAIN}."
  write_status skipped "NCS toolchain install/update skipped."
  exit 0
fi

INSTALL_SYSTEM_PACKAGES="${INSTALL_SYSTEM_PACKAGES:-auto}" STRICT_SYSTEM_PACKAGES="${STRICT_NCS_TOOLCHAIN}" bash "${REPO_ROOT}/scripts/setup_system_packages.sh"
ensure_build_tools
STRICT_NRF_TOOLS="${STRICT_NCS_TOOLCHAIN}" bash "${REPO_ROOT}/scripts/setup_nrf_tools.sh" --west-only
have_tool west || { fail_or_warn "west is still missing after setup."; exit 0; }
install_ncs_workspace
install_python_requirements
install_zephyr_sdk
write_env_file
write_status success "nRF Connect SDK / Zephyr toolchain setup complete."
validate_build

echo "nRF Connect SDK / Zephyr setup complete."
echo "Source this before manual west builds: source ${REPO_ROOT}/logs/nrf_connect_sdk_env.sh"
