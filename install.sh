#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${KOALABYTE_REPO_URL:-https://github.com/greatwhitek9-lab/KoalaByte-Blue.git}"
BRANCH="${KOALABYTE_BRANCH:-Main}"
INSTALL_DIR="${KOALABYTE_INSTALL_DIR:-${HOME}/KoalaByte-Blue}"
RUN_MODE="install"

usage() {
  cat <<'EOF'
KoalaByte Blue V2 Heltec Edition bootstrapper

Normal Raspberry Pi 3B+ install from a cloned repo:
  bash install.sh

Fresh Pi download flow:
  curl -fsSL -o koalabyte-install.sh https://raw.githubusercontent.com/greatwhitek9-lab/KoalaByte-Blue/Main/install.sh
  bash koalabyte-install.sh

Modes:
  install       Clone/update repo, then run scripts/install_koalabyte_one_shot.sh. Default.
  check-only   Clone/update repo, prepare the local Python check venv, then run the one-shot dry-run readiness gate.
  repo-only    Clone/update repo only.

Useful environment:
  KOALABYTE_INSTALL_DIR=$HOME/KoalaByte-Blue
  KOALABYTE_BRANCH=Main
  ESP32_PORT=/dev/ttyUSB0
  KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0
  T114_PLUG_FLASH_PROFILE=combined-safe|color-mouth|hci-usb|skip
  INSTALL_INNOMAKER_CAN=optional|0|1
  STRICT_INNOMAKER_CAN=1
  KOALABYTE_ALLOW_DIRTY=1
EOF
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
  *)
    echo "Unknown mode: ${1:-}" >&2
    usage >&2
    exit 2
    ;;
esac

ensure_git() {
  if command -v git >/dev/null 2>&1; then
    return 0
  fi
  echo "git is not installed. Attempting to install it with apt..."
  if command -v apt-get >/dev/null 2>&1; then
    if [[ "${EUID}" -eq 0 ]]; then
      apt-get update
      apt-get install -y git ca-certificates curl
    elif command -v sudo >/dev/null 2>&1; then
      sudo apt-get update
      sudo apt-get install -y git ca-certificates curl
    else
      echo "apt-get exists, but this user is not root and sudo is unavailable." >&2
      exit 1
    fi
  else
    echo "git is required. Install git, then re-run this bootstrapper." >&2
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
    echo "Running KoalaByte one-shot dry-run readiness gate..."
    bash scripts/install_koalabyte_one_shot.sh --check-only "$@"
    ;;
  install)
    echo "Running KoalaByte one-shot installer..."
    T114_PLUG_FLASH_PROFILE="${T114_PLUG_FLASH_PROFILE:-combined-safe}" bash scripts/install_koalabyte_one_shot.sh "$@"
    ;;
esac
