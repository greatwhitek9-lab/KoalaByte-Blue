#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${KOALABYTE_REPO_URL:-https://github.com/greatwhitek9-lab/KoalaByte-Blue.git}"
BRANCH="${KOALABYTE_BRANCH:-Main}"
INSTALL_DIR="${KOALABYTE_INSTALL_DIR:-${HOME}/KoalaByte-Blue}"
RUN_MODE="install"

# Compatibility contract: one-shot-install.sh delegates comprehensive Pi
# provisioning to scripts/install_koalabyte_one_shot.sh while owning pinned
# peripheral flashing and final hardware validation.

usage() {
  cat <<'USAGE'
KoalaByte Blue V2 Heltec Edition bootstrapper

Normal Raspberry Pi 3B+ install from a cloned repo:
  bash install.sh

Fresh Pi download flow:
  curl -fsSL -o koalabyte-install.sh https://raw.githubusercontent.com/greatwhitek9-lab/KoalaByte-Blue/Main/install.sh
  bash koalabyte-install.sh

Heltec UF2-first full install:
  1. Plug in the Heltec T114 by USB-C data cable.
  2. Press RST twice quickly until the HT-n5262 UF2 volume appears.
  3. Run:
       bash install.sh --heltec-uf2-first

Modes:
  install      Clone/update repo, then run the complete pinned-firmware one-shot installer. Default.
  check-only   Clone/update repo, prepare the local Python check venv, then run dry-run readiness checks.
  repo-only    Clone/update repo only.

Any extra flags after the mode are passed to the one-shot installer.

ESP32-S3 firmware policy:
  FLASH_ESP32=auto  Positively identify current/older firmware; preserve unknown boards. Default.
  FLASH_ESP32=0     Always preserve the connected ESP32-S3 firmware.
  FLASH_ESP32=1     Explicitly flash the hash-verified v0.9.8 full-flash image.

For FLASH_ESP32=1, provide the extracted firmware package through either:
  KOALABYTE_ESP32_FIRMWARE_PACKAGE=/path/to/koalabyte-esp32-s3-dualeye-v0.9.8-killerkoala-wake-session
  ESP32_PREBUILT_IMAGE=/absolute/path/to/koalabyte-esp32-s3-dualeye-v0.9.8-killerkoala-wake-session-full-flash.bin

Examples:
  bash install.sh install --heltec-uf2-first
  FLASH_ESP32=1 ESP32_PORT=/dev/ttyACM0 KOALABYTE_ESP32_FIRMWARE_PACKAGE=$HOME/Downloads/koalabyte-esp32-s3-dualeye-v0.9.8-killerkoala-wake-session bash install.sh
  bash install.sh check-only

Lab transmit profile:
  The installer does not transmit RF, BLE, or CAN traffic during setup.
  CAN bench transmit remains gated to isolated simulator use through explicit backend flags.

Useful environment:
  KOALABYTE_INSTALL_DIR=$HOME/KoalaByte-Blue
  KOALABYTE_BRANCH=Main
  ESP32_PORT=/dev/ttyACM0
  ESP32_BAUD=460800
  FLASH_ESP32=auto|0|1
  KOALABYTE_ESP32_FIRMWARE_PACKAGE=/path/to/extracted/package
  ESP32_PREBUILT_IMAGE=/absolute/path/to/full-flash.bin
  KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM1
  HELTEC_UF2_FIRST=1
  T114_REQUIRE_UF2=1
  T114_FLASH_METHOD=uf2
  T114_PLUG_FLASH_PROFILE=combined-safe|color-mouth|hci-usb|skip
  INSTALL_INNOMAKER_CAN=optional|0|1
  STRICT_INNOMAKER_CAN=1
  KOALABYTE_LAB_PROFILE=owned-lab
  KOALABYTE_CAN_TRANSMIT_MODE=gated-bench|listen-only|disabled
  KOALABYTE_RF_BLE_TRANSMIT_MODE=disabled-during-install|passive-only
  STRICT_LAB_TRANSMIT_POLICY=1
  CAN_INTERFACE=can0
  CAN_BITRATE=500000
  KOALABYTE_ALLOW_DIRTY=1
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

case "${1:-install}" in
  install|check-only|repo-only)
    RUN_MODE="${1:-install}"
    shift || true
    ;;
  --*)
    RUN_MODE="install"
    ;;
  *)
    echo "Unknown mode: ${1:-}" >&2
    usage >&2
    exit 2
    ;;
esac

apt_install() {
  if ! command -v apt-get >/dev/null 2>&1; then
    return 1
  fi
  if [[ "${EUID}" -eq 0 ]]; then
    apt-get update
    apt-get install -y "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y "$@"
  else
    echo "apt-get exists, but this user is not root and sudo is unavailable." >&2
    return 1
  fi
}

ensure_git() {
  if command -v git >/dev/null 2>&1; then
    return 0
  fi
  echo "git is not installed. Attempting to install it with apt..."
  if ! apt_install git ca-certificates curl; then
    echo "git is required. Install git, ca-certificates, and curl, then re-run this bootstrapper." >&2
    exit 1
  fi
}

ensure_python_venv() {
  local python_bin="${PYTHON_BIN:-python3}"
  if ! command -v "${python_bin}" >/dev/null 2>&1; then
    echo "Python 3 is required but was not found. Attempting to install python3, python3-venv, and python3-pip with apt..."
    if ! apt_install python3 python3-venv python3-pip; then
      echo "Python 3 is required. Install python3, python3-venv, and python3-pip, then re-run this bootstrapper." >&2
      exit 1
    fi
  fi
  if "${python_bin}" -m venv --help >/dev/null 2>&1; then
    return 0
  fi
  echo "Python venv support is missing. Attempting to install python3-venv and python3-pip with apt..."
  if ! apt_install python3-venv python3-pip; then
    echo "python3-venv is required for KoalaByte check/install environments." >&2
    exit 1
  fi
  if ! "${python_bin}" -m venv --help >/dev/null 2>&1; then
    echo "Python venv support is still unavailable after package installation." >&2
    exit 1
  fi
}

update_existing_checkout() {
  cd "${INSTALL_DIR}"
  if [[ "${KOALABYTE_ALLOW_DIRTY:-0}" != "1" ]]; then
    if ! git diff --quiet || ! git diff --cached --quiet; then
      echo "Existing checkout has local changes: ${INSTALL_DIR}" >&2
      echo "Commit or stash them first, or set KOALABYTE_ALLOW_DIRTY=1." >&2
      exit 1
    fi
  fi
  git remote set-url origin "${REPO_URL}" || true
  git fetch --prune origin "${BRANCH}"
  git checkout "${BRANCH}"
  git pull --ff-only origin "${BRANCH}"
}

clone_repo() {
  mkdir -p "$(dirname "${INSTALL_DIR}")"
  git clone --depth 1 --branch "${BRANCH}" "${REPO_URL}" "${INSTALL_DIR}"
}

prepare_check_environment() {
  cd "${INSTALL_DIR}"
  local venv_dir="${INSTALL_DIR}/pi-companion/.venv"
  local python_bin="${PYTHON_BIN:-python3}"
  if [[ ! -x "${python_bin}" ]] && ! command -v "${python_bin}" >/dev/null 2>&1; then
    echo "Python 3 is required for check-only mode." >&2
    exit 1
  fi
  if [[ ! -f "${venv_dir}/bin/python" ]]; then
    echo "Preparing local Python check environment: ${venv_dir}"
    "${python_bin}" -m venv --system-site-packages "${venv_dir}"
  fi
  "${venv_dir}/bin/python" -m pip install --upgrade pip wheel setuptools
  "${venv_dir}/bin/python" -m pip install -r "${INSTALL_DIR}/pi-companion/requirements.txt"
  export PYTHON_BIN="${venv_dir}/bin/python"
}

ensure_git
ensure_python_venv

if [[ -d "${INSTALL_DIR}/.git" ]]; then
  echo "Updating existing KoalaByte Blue checkout: ${INSTALL_DIR}"
  update_existing_checkout
elif [[ -e "${INSTALL_DIR}" ]]; then
  echo "Install path exists but is not a git checkout: ${INSTALL_DIR}" >&2
  echo "Choose a different KOALABYTE_INSTALL_DIR or move the existing path." >&2
  exit 1
else
  echo "Cloning KoalaByte Blue ${BRANCH} into ${INSTALL_DIR}"
  clone_repo
  cd "${INSTALL_DIR}"
fi

case "${RUN_MODE}" in
  repo-only)
    echo "Repository ready at ${INSTALL_DIR}"
    ;;
  check-only)
    echo "Preparing KoalaByte one-shot dry-run readiness gate..."
    prepare_check_environment
    echo "Running KoalaByte complete one-shot dry-run readiness gate..."
    bash one-shot-install.sh --check-only
    ;;
  install)
    echo "Running KoalaByte complete pinned-firmware one-shot installer..."
    for arg in "$@"; do
      case "${arg}" in
        --heltec-uf2-first|--t114-uf2-first)
          export FLASH_T114_ON_PLUG=1
          export FORCE_T114_FLASH=1
          export STRICT_T114_PLUG_FLASH=1
          ;;
        *)
          echo "Unknown install argument: ${arg}" >&2
          exit 2
          ;;
      esac
    done
    T114_PLUG_FLASH_PROFILE="${T114_PLUG_FLASH_PROFILE:-combined-safe}" \
      FLASH_ESP32="${FLASH_ESP32:-auto}" \
      bash one-shot-install.sh
    ;;
esac
