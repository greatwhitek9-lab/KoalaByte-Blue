#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="${KOALABYTE_REPO_URL:-https://github.com/greatwhitek9-lab/KoalaByte-Blue.git}"
BRANCH="${KOALABYTE_BRANCH:-Main}"
INSTALL_DIR="${KOALABYTE_INSTALL_DIR:-${HOME}/KoalaByte-Blue}"
MODE="install"

usage() {
  cat <<'EOF'
KoalaByte Blue Raspberry Pi bootstrapper

Usage:
  bash install.sh
  bash install.sh check-only
  bash install.sh repo-only

Environment:
  KOALABYTE_REPO_URL=https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
  KOALABYTE_BRANCH=Main
  KOALABYTE_INSTALL_DIR=$HOME/KoalaByte-Blue
  KOALABYTE_SERVICE_USER=<linux-user>

This bootstrapper clones or updates the repository and invokes the single
canonical entrypoint: one-shot-install.sh. Peripheral firmware is preserved.
EOF
}

case "${1:-install}" in
  install) MODE="install"; shift || true ;;
  check-only|--check-only|--dry-run) MODE="check-only"; shift || true ;;
  repo-only) MODE="repo-only"; shift || true ;;
  -h|--help) usage; exit 0 ;;
  *) echo "Unknown mode: ${1}" >&2; usage >&2; exit 2 ;;
esac

if [[ $# -gt 0 ]]; then
  echo "Unexpected arguments: $*" >&2
  exit 2
fi

if ! command -v git >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    if [[ "${EUID}" -eq 0 ]]; then
      apt-get update
      apt-get install -y git ca-certificates
    else
      sudo apt-get update
      sudo apt-get install -y git ca-certificates
    fi
  else
    echo "git is required." >&2
    exit 1
  fi
fi

if [[ -d "${INSTALL_DIR}/.git" ]]; then
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
  repo-only)
    echo "Repository ready: ${INSTALL_DIR}"
    ;;
  check-only)
    bash one-shot-install.sh --check-only
    ;;
  install)
    bash one-shot-install.sh
    ;;
esac
