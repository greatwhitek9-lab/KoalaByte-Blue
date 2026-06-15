#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUTOSTART_DIR="${HOME}/.config/autostart"
AUTOSTART_FILE="${AUTOSTART_DIR}/koalabyte-blue-boot-splash.desktop"
TEMPLATE="${REPO_ROOT}/pi-companion/autostart/koalabyte-blue-boot-splash.desktop"

mkdir -p "${AUTOSTART_DIR}"
sed "s#__KOALABYTE_ROOT__#${REPO_ROOT}#g" "${TEMPLATE}" > "${AUTOSTART_FILE}"
chmod 0644 "${AUTOSTART_FILE}"

echo "Installed KoalaByte Blue boot splash desktop autostart: ${AUTOSTART_FILE}"
echo "It will run after the Pi desktop session starts. Test now with:"
echo "PYTHONPATH=${REPO_ROOT}/pi-companion python3 ${REPO_ROOT}/scripts/run_boot_splash.py --windowed --duration 3"
