#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="${REPO_ROOT}/logrotate/koalabyte-blue"
TARGET="/etc/logrotate.d/koalabyte-blue"
CHECK_ONLY=0
INSTALL_LOGROTATE="${INSTALL_LOGROTATE:-auto}"
STRICT_LOGROTATE="${STRICT_LOGROTATE:-0}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only)
      CHECK_ONLY=1
      ;;
    -h|--help)
      cat <<'EOF'
Install the KoalaByte Blue logrotate configuration.

Usage:
  bash scripts/install_koalabyte_logrotate.sh
  bash scripts/install_koalabyte_logrotate.sh --check-only

Installs:
  /etc/logrotate.d/koalabyte-blue
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
  shift
done

case "${INSTALL_LOGROTATE}" in
  0|false|False|no|NO|skip|SKIP)
    echo "Skipping KoalaByte logrotate install by request."
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES)
    ;;
  *)
    echo "Unknown INSTALL_LOGROTATE=${INSTALL_LOGROTATE}" >&2
    exit 2
    ;;
esac

if [[ ! -f "${SOURCE}" ]]; then
  echo "Missing logrotate config template: ${SOURCE}" >&2
  exit 1
fi

grep -q "koalabyte-blue" "${SOURCE}"
grep -q "copytruncate" "${SOURCE}"

if [[ "${CHECK_ONLY}" == "1" ]]; then
  echo "KoalaByte logrotate config check-only passed."
  exit 0
fi

if [[ "${EUID}" -eq 0 ]]; then
  install -m 0644 "${SOURCE}" "${TARGET}"
elif command -v sudo >/dev/null 2>&1; then
  sudo install -m 0644 "${SOURCE}" "${TARGET}"
else
  echo "Root or sudo is required to install ${TARGET}." >&2
  [[ "${STRICT_LOGROTATE}" == "1" ]] && exit 1
  exit 0
fi

echo "Installed KoalaByte logrotate config: ${TARGET}"
