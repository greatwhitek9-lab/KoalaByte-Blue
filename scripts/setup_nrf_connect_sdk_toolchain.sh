#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_USER="${SUDO_USER:-${USER:-$(id -un)}}"
INSTALL_HOME="${HOME}"
if command -v getent >/dev/null 2>&1; then
  resolved_home="$(getent passwd "${INSTALL_USER}" | cut -d: -f6 || true)"
  [[ -n "${resolved_home}" ]] && INSTALL_HOME="${resolved_home}"
fi

NCS_WORKSPACE="${NCS_WORKSPACE:-${INSTALL_HOME}/ncs}"
NCS_REVISION="${NCS_REVISION:-v2.9.0}"
NCS_TOOLS_VENV="${NCS_TOOLS_VENV:-${INSTALL_HOME}/.venvs/ncs-tools}"
ZEPHYR_SDK_VERSION="${ZEPHYR_SDK_VERSION:-0.16.8}"
ZEPHYR_SDK_INSTALL_DIR="${ZEPHYR_SDK_INSTALL_DIR:-${INSTALL_HOME}/zephyr-sdk-${ZEPHYR_SDK_VERSION}}"
ZEPHYR_SDK_DOWNLOAD_DIR="${ZEPHYR_SDK_DOWNLOAD_DIR:-${INSTALL_HOME}/.cache/koalabyte/zephyr-sdk}"
INSTALL_NCS_TOOLCHAIN="${INSTALL_NCS_TOOLCHAIN:-auto}"
STRICT_NCS_TOOLCHAIN="${STRICT_NCS_TOOLCHAIN:-0}"
SKIP_ZEPHYR_SDK="${SKIP_ZEPHYR_SDK:-0}"
SKIP_NCS_UPDATE="${SKIP_NCS_UPDATE:-0}"
VALIDATE_BUILD="${VALIDATE_BUILD:-0}"
PIP_RETRIES="${PIP_RETRIES:-25}"
PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT:-300}"
WEST_UPDATE_ATTEMPTS="${WEST_UPDATE_ATTEMPTS:-3}"
CHECK_ONLY=0

usage() {
  cat <<'EOF'
KoalaByte Blue nRF Connect SDK / Zephyr toolchain setup helper

Usage:
  bash scripts/setup_nrf_connect_sdk_toolchain.sh
  STRICT_NCS_TOOLCHAIN=1 bash scripts/setup_nrf_connect_sdk_toolchain.sh
  bash scripts/setup_nrf_connect_sdk_toolchain.sh --check-only
  VALIDATE_BUILD=1 bash scripts/setup_nrf_connect_sdk_toolchain.sh

The project is pinned to NCS v2.9.0 with Zephyr SDK 0.16.8, matching its
source-build workflow. Linux firmware builds require x86-64 or a 64-bit ARM
userspace reporting aarch64. Downloads use persistent storage and can resume.
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
mkdir -p logs

install_enabled() {
  case "${INSTALL_NCS_TOOLCHAIN}" in
    1|true|True|yes|YES|auto|AUTO) return 0 ;;
    *) return 1 ;;
  esac
}
strict_enabled() { [[ "${STRICT_NCS_TOOLCHAIN}" == "1" ]]; }
have_tool() { command -v "$1" >/dev/null 2>&1; }

fail_or_warn() {
  local message="$1"
  echo "${message}" >&2
  write_status incomplete "${message}"
  strict_enabled && exit 1
  return 1
}

host_arch() {
  case "$(uname -m)" in
    x86_64|amd64) echo x86_64 ;;
    aarch64|arm64) echo aarch64 ;;
    armv6l|armv7l)
      echo "32-bit Raspberry Pi OS is unsupported for Zephyr SDK host tools; install 64-bit Raspberry Pi OS Lite." >&2
      return 1
      ;;
    *) echo "Unsupported Zephyr SDK host architecture: $(uname -m)" >&2; return 1 ;;
  esac
}

write_status() {
  local status="$1" message="$2"
  cat > "${REPO_ROOT}/logs/nrf_connect_sdk_status.json" <<EOF
{
  "status": "${status}",
  "message": "${message}",
  "ncs_workspace": "${NCS_WORKSPACE}",
  "ncs_revision": "${NCS_REVISION}",
  "ncs_tools_venv": "${NCS_TOOLS_VENV}",
  "zephyr_sdk_version": "${ZEPHYR_SDK_VERSION}",
  "zephyr_sdk_install_dir": "${ZEPHYR_SDK_INSTALL_DIR}",
  "zephyr_sdk_download_dir": "${ZEPHYR_SDK_DOWNLOAD_DIR}",
  "zephyr_base": "${NCS_WORKSPACE}/zephyr",
  "west_available": $([[ -x "${NCS_TOOLS_VENV}/bin/west" || -x "${NCS_WORKSPACE}/.venv/bin/west" ]] && echo true || echo false),
  "ncs_workspace_exists": $([[ -d "${NCS_WORKSPACE}/.west" ]] && echo true || echo false),
  "zephyr_sdk_compiler_exists": $([[ -x "${ZEPHYR_SDK_INSTALL_DIR}/arm-zephyr-eabi/bin/arm-zephyr-eabi-gcc" ]] && echo true || echo false),
  "updated_at": $(date +%s)
}
EOF
}

write_env_file() {
  cat > "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh" <<EOF
# KoalaByte Blue nRF Connect SDK / Zephyr environment
export NCS_WORKSPACE="${NCS_WORKSPACE}"
export ZEPHYR_BASE="${NCS_WORKSPACE}/zephyr"
export ZEPHYR_TOOLCHAIN_VARIANT="zephyr"
export ZEPHYR_SDK_INSTALL_DIR="${ZEPHYR_SDK_INSTALL_DIR}"
export ZEPHYR_SDK_DOWNLOAD_DIR="${ZEPHYR_SDK_DOWNLOAD_DIR}"
export NCS_TOOLS_VENV="${NCS_TOOLS_VENV}"
export PATH="${NCS_WORKSPACE}/.venv/bin:${NCS_TOOLS_VENV}/bin:${REPO_ROOT}/pi-companion/.venv/bin:${INSTALL_HOME}/.local/bin:/usr/bin:/bin:\$PATH"
export PIP_RETRIES="${PIP_RETRIES}"
export PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT}"
export CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-1}"
EOF
}

run_as_install_user() {
  if [[ "$(id -u)" == "0" && "${INSTALL_USER}" != "root" ]]; then
    sudo -u "${INSTALL_USER}" -H env HOME="${INSTALL_HOME}" "$@"
  else
    "$@"
  fi
}

apt_install() {
  local packages=("$@") runner=()
  command -v apt-get >/dev/null 2>&1 || return 1
  if [[ "${EUID}" -eq 0 ]]; then runner=(apt-get); else runner=(sudo apt-get); fi
  DEBIAN_FRONTEND=noninteractive "${runner[@]}" update
  DEBIAN_FRONTEND=noninteractive "${runner[@]}" install -y "${packages[@]}"
}

ensure_build_tools() {
  local missing_packages=()
  have_tool cmake || missing_packages+=(cmake)
  have_tool ninja || missing_packages+=(ninja-build)
  have_tool git || missing_packages+=(git)
  have_tool curl || missing_packages+=(curl)
  have_tool xz || missing_packages+=(xz-utils)
  have_tool gperf || missing_packages+=(gperf)
  if (( ${#missing_packages[@]} > 0 )); then
    apt_install python3-venv ca-certificates device-tree-compiler ccache "${missing_packages[@]}" || true
  fi
  for command in cmake ninja git curl xz; do
    have_tool "${command}" || { fail_or_warn "Required NCS host command is missing: ${command}"; return 1; }
  done
}

pip_install_retry() {
  local python="$1"; shift
  local attempt rc=1
  for attempt in 1 2 3; do
    set +e
    run_as_install_user "${python}" -m pip install --retries "${PIP_RETRIES}" \
      --timeout "${PIP_DEFAULT_TIMEOUT}" --prefer-binary --no-input "$@"
    rc=$?
    set -e
    [[ ${rc} -eq 0 ]] && return 0
    echo "pip attempt ${attempt}/3 failed with exit ${rc}; retrying..." >&2
    sleep $((attempt * 10))
  done
  return "${rc}"
}

ensure_west_venv() {
  if [[ ! -x "${NCS_TOOLS_VENV}/bin/python" ]]; then
    echo "Creating isolated west environment: ${NCS_TOOLS_VENV}"
    run_as_install_user "${PYTHON_BIN}" -m venv "${NCS_TOOLS_VENV}"
  fi
  pip_install_retry "${NCS_TOOLS_VENV}/bin/python" --upgrade pip wheel setuptools west
  export PATH="${NCS_TOOLS_VENV}/bin:${PATH}"
  "${NCS_TOOLS_VENV}/bin/west" --version
}

install_zephyr_sdk() {
  [[ "${SKIP_ZEPHYR_SDK}" == "1" ]] && { echo "Skipping Zephyr SDK install."; return 0; }
  local compiler="${ZEPHYR_SDK_INSTALL_DIR}/arm-zephyr-eabi/bin/arm-zephyr-eabi-gcc"
  if [[ -x "${compiler}" ]]; then
    echo "Zephyr SDK already verified: ${ZEPHYR_SDK_INSTALL_DIR}"
    return 0
  fi
  [[ -d "${ZEPHYR_SDK_INSTALL_DIR}" ]] && rm -rf -- "${ZEPHYR_SDK_INSTALL_DIR}"

  local arch archive url archive_path partial_path install_parent
  arch="$(host_arch)" || { fail_or_warn "No Zephyr SDK archive exists for this host architecture."; return 1; }
  archive="zephyr-sdk-${ZEPHYR_SDK_VERSION}_linux-${arch}.tar.xz"
  url="https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v${ZEPHYR_SDK_VERSION}/${archive}"
  install_parent="$(dirname "${ZEPHYR_SDK_INSTALL_DIR}")"
  archive_path="${ZEPHYR_SDK_DOWNLOAD_DIR}/${archive}"
  partial_path="${archive_path}.part"
  mkdir -p "${ZEPHYR_SDK_DOWNLOAD_DIR}" "${install_parent}"

  if [[ ! -f "${archive_path}" ]]; then
    [[ -f "${partial_path}" ]] && echo "Resuming Zephyr SDK download: ${partial_path}" || \
      echo "Downloading Zephyr SDK ${ZEPHYR_SDK_VERSION} for ${arch}"
    curl -L --fail --retry 10 --retry-all-errors --connect-timeout 30 \
      --continue-at - --output "${partial_path}" "${url}" || {
        fail_or_warn "Zephyr SDK download failed; partial data was retained at ${partial_path}"
        return 1
      }
    mv -f "${partial_path}" "${archive_path}"
  fi

  echo "Validating Zephyr SDK archive..."
  if ! tar -tJf "${archive_path}" >/dev/null; then
    rm -f "${archive_path}" "${partial_path}"
    fail_or_warn "Zephyr SDK archive was corrupt and has been removed."
    return 1
  fi
  tar -xJf "${archive_path}" -C "${install_parent}"
  [[ -x "${ZEPHYR_SDK_INSTALL_DIR}/setup.sh" ]] || {
    fail_or_warn "Zephyr SDK setup.sh is missing after extraction."; return 1;
  }
  "${ZEPHYR_SDK_INSTALL_DIR}/setup.sh" -t arm-zephyr-eabi -h -c
  [[ -x "${compiler}" ]] || {
    fail_or_warn "Zephyr SDK compiler validation failed: ${compiler}"; return 1;
  }
  rm -f "${archive_path}" "${partial_path}"
}

west_update_retry() {
  local attempt rc=1
  for ((attempt=1; attempt<=WEST_UPDATE_ATTEMPTS; attempt++)); do
    set +e
    west update
    rc=$?
    set -e
    [[ ${rc} -eq 0 ]] && return 0
    echo "west update attempt ${attempt}/${WEST_UPDATE_ATTEMPTS} failed; retrying..." >&2
    sleep $((attempt * 15))
  done
  return "${rc}"
}

install_ncs_workspace() {
  mkdir -p "$(dirname "${NCS_WORKSPACE}")"
  if [[ ! -d "${NCS_WORKSPACE}/.west" ]]; then
    if [[ -d "${NCS_WORKSPACE}" ]] && find "${NCS_WORKSPACE}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
      fail_or_warn "Incomplete non-empty NCS workspace found without .west: ${NCS_WORKSPACE}. Move or remove that directory, then retry."
      return 1
    fi
    west init -m https://github.com/nrfconnect/sdk-nrf --mr "${NCS_REVISION}" "${NCS_WORKSPACE}"
  else
    echo "Resuming existing NCS workspace: ${NCS_WORKSPACE}"
  fi
  cd "${NCS_WORKSPACE}"
  if [[ "${SKIP_NCS_UPDATE}" != "1" ]]; then
    west_update_retry || { fail_or_warn "west update failed after ${WEST_UPDATE_ATTEMPTS} attempts."; return 1; }
  fi
  west zephyr-export
}

install_python_requirements() {
  if [[ ! -x "${NCS_WORKSPACE}/.venv/bin/python" ]]; then
    run_as_install_user "${PYTHON_BIN}" -m venv "${NCS_WORKSPACE}/.venv"
  fi
  local python="${NCS_WORKSPACE}/.venv/bin/python" req
  pip_install_retry "${python}" --upgrade pip wheel setuptools west
  for req in zephyr/scripts/requirements.txt nrf/scripts/requirements.txt bootloader/mcuboot/scripts/requirements.txt; do
    if [[ -f "${NCS_WORKSPACE}/${req}" ]]; then
      pip_install_retry "${python}" -r "${NCS_WORKSPACE}/${req}" || {
        fail_or_warn "NCS Python requirements failed: ${req}"; return 1;
      }
    fi
  done
  export PATH="${NCS_WORKSPACE}/.venv/bin:${PATH}"
}

validate_build() {
  [[ "${VALIDATE_BUILD}" == "1" ]] || return 0
  source "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh"
  cd "${REPO_ROOT}"
  west build --no-sysbuild -p always -b "${T114_BOARD:-heltec_t114_v2/nrf52840/uf2}" \
    firmware/t114-combined-safe -d build/t114-combined-safe -- -DBOARD_ROOT="${REPO_ROOT}"
}

echo "== KoalaByte Blue nRF Connect SDK / Zephyr setup =="
echo "NCS=${NCS_REVISION} Zephyr SDK=${ZEPHYR_SDK_VERSION}"
echo "Workspace=${NCS_WORKSPACE}"
echo "Host=$(uname -m) userspace=$(getconf LONG_BIT 2>/dev/null || echo unknown)-bit"
write_env_file

if [[ "${CHECK_ONLY}" == "1" ]]; then
  missing=()
  [[ -x "${NCS_TOOLS_VENV}/bin/west" || -x "${NCS_WORKSPACE}/.venv/bin/west" ]] || missing+=(west)
  [[ -d "${NCS_WORKSPACE}/.west" ]] || missing+=("NCS workspace")
  [[ -d "${NCS_WORKSPACE}/zephyr" ]] || missing+=("Zephyr checkout")
  [[ -x "${ZEPHYR_SDK_INSTALL_DIR}/arm-zephyr-eabi/bin/arm-zephyr-eabi-gcc" ]] || missing+=("Zephyr compiler")
  (( ${#missing[@]} == 0 )) || { fail_or_warn "NCS toolchain check missing: ${missing[*]}"; exit 1; }
  write_status success "nRF Connect SDK toolchain check passed."
  exit 0
fi

install_enabled || { write_status skipped "NCS toolchain installation disabled."; exit 0; }
bash "${REPO_ROOT}/scripts/preflight_firmware_host.sh" --before-build
ensure_build_tools
ensure_west_venv
install_zephyr_sdk
install_ncs_workspace
install_python_requirements
write_env_file
write_status success "nRF Connect SDK / Zephyr toolchain setup complete."
validate_build
echo "nRF Connect SDK / Zephyr setup complete."
