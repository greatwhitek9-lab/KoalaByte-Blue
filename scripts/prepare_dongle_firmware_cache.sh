#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "${REPO_ROOT}"
export PYTHONPATH="${REPO_ROOT}/pi-companion${PYTHONPATH:+:${PYTHONPATH}}"

echo "Preparing KoalaByte Blue nRF52840 Dongle firmware cache on this Raspberry Pi..."
echo "This builds and packages both DFU ZIPs:"
echo "  - KoalaByte Blue Lab Mode"
echo "  - Koala Konnect Mode"
echo

echo "Checking/preparing west and nrfutil first..."
STRICT_NRF_TOOLS="${STRICT_NRF_TOOLS:-1}" PYTHON_BIN="${PYTHON_BIN}" bash "${REPO_ROOT}/scripts/setup_nrf_tools.sh"
echo

echo "Checking/preparing local NCS / Zephyr workspace..."
PYTHON_BIN="${PYTHON_BIN}" bash "${REPO_ROOT}/scripts/setup_local_ncs.sh"
echo

"${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_koala_mode_switcher.py" prepare-cache

echo
echo "Firmware cache status:"
"${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_koala_mode_switcher.py" cache-status
