#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="${KOALABYTE_REPO_URL:-https://github.com/greatwhitek9-lab/KoalaByte-Blue.git}"
BRANCH="${KOALABYTE_BRANCH:-Main}"
INSTALL_DIR="${KOALABYTE_INSTALL_DIR:-${HOME}/KoalaByte-Blue}"
MODE="install"
ALLOW_SUDO_WRAPPED_INSTALL="${KOALABYTE_ALLOW_SUDO_WRAPPED_INSTALL:-0}"

usage() {
  cat <<'EOF'
KoalaByte Blue whole-system bootstrapper

Usage:
  bash install.sh
  bash install.sh check-only
  bash install.sh repo-only

Environment:
  KOALABYTE_REPO_URL=https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
  KOALABYTE_BRANCH=Main
  KOALABYTE_INSTALL_DIR=$HOME/KoalaByte-Blue
  KOALABYTE_SERVICE_USER=<linux-user>

Run this as the normal SSH/login user, not with `sudo bash`. The bootstrapper
recovers an interrupted ESP32 source-generation transaction, updates the selected
branch, and invokes one-shot-install.sh, which requests sudo only where required.
EOF
}

case "${1:-install}" in
  install) MODE="install"; shift || true ;;
  check-only|--check-only|--dry-run) MODE="check-only"; shift || true ;;
  repo-only) MODE="repo-only"; shift || true ;;
  -h|--help) usage; exit 0 ;;
  *) echo "Unknown mode: ${1}" >&2; usage >&2; exit 2 ;;
esac
[[ $# -eq 0 ]] || { echo "Unexpected arguments: $*" >&2; exit 2; }

case "${ALLOW_SUDO_WRAPPED_INSTALL}" in
  1|true|True|yes|YES|on|ON) allow_sudo=1 ;;
  *) allow_sudo=0 ;;
esac
if [[ "${EUID}" -eq 0 && -n "${SUDO_USER:-}" && "${allow_sudo}" != "1" ]]; then
  echo "Do not run the KoalaByte bootstrapper with 'sudo bash'." >&2
  echo "Exit the root shell and run it as ${SUDO_USER}; privileged steps call sudo internally." >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    if [[ "${EUID}" -eq 0 ]]; then runner=(apt-get); else runner=(sudo apt-get); fi
    DEBIAN_FRONTEND=noninteractive "${runner[@]}" update
    DEBIAN_FRONTEND=noninteractive "${runner[@]}" install -y git ca-certificates
  else
    echo "git is required." >&2
    exit 1
  fi
fi

restore_interrupted_esp32_sources() {
  local backup_root="${INSTALL_DIR}/logs/deployment/esp32-source-backup"
  local relative backup
  [[ -d "${backup_root}" ]] || return 0
  echo "Recovering tracked ESP32 sources from an interrupted build transaction..."
  for relative in \
    firmware/esp32-dualeye/src/integrated_main.cpp \
    firmware/esp32-dualeye/src/integrated_main_wake_session.cpp \
    firmware/esp32-dualeye/include/config.h; do
    backup="${backup_root}/${relative}"
    if [[ -f "${backup}" ]]; then
      mkdir -p "$(dirname "${INSTALL_DIR}/${relative}")"
      cp -f "${backup}" "${INSTALL_DIR}/${relative}"
    fi
  done
  rm -rf -- "${backup_root}"
}

if [[ -d "${INSTALL_DIR}/.git" ]]; then
  restore_interrupted_esp32_sources
  if ! git -C "${INSTALL_DIR}" diff --quiet || ! git -C "${INSTALL_DIR}" diff --cached --quiet; then
    echo "Repository has local changes; refusing to overwrite them during update:" >&2
    git -C "${INSTALL_DIR}" status --short >&2
    echo "Commit, stash, or intentionally discard those changes, then rerun." >&2
    exit 1
  fi
  git -C "${INSTALL_DIR}" fetch origin
  git -C "${INSTALL_DIR}" checkout "${BRANCH}"
  git -C "${INSTALL_DIR}" pull --ff-only origin "${BRANCH}"
elif [[ -e "${INSTALL_DIR}" ]]; then
  echo "Install path exists but is not a git repository: ${INSTALL_DIR}" >&2
  exit 1
else
  git clone --branch "${BRANCH}" "${REPO_URL}" "${INSTALL_DIR}"
fi

cd "${INSTALL_DIR}"
case "${MODE}" in
  repo-only) echo "Repository ready: ${INSTALL_DIR}" ;;
  check-only) bash one-shot-install.sh --check-only ;;
  install) bash one-shot-install.sh ;;
esac
