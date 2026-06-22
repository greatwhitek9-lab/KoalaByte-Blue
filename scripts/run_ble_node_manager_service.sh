#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/pi-companion/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

export PYTHONPATH="${REPO_ROOT}/pi-companion${PYTHONPATH:+:${PYTHONPATH}}"
export KOALABYTE_HELTEC_USB_PORT="${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-/dev/ttyACM0}}"
export KOALABYTE_ESP32_FACE_PORT="${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-}}"

mkdir -p "${REPO_ROOT}/logs/ble_nodes"

args=(
  "${REPO_ROOT}/scripts/run_ble_node_manager.py"
  --duration 0
  --heltec-port "${KOALABYTE_HELTEC_USB_PORT}"
  --log-dir "${REPO_ROOT}/logs/ble_nodes"
)

if [[ -n "${KOALABYTE_ESP32_FACE_PORT}" ]]; then
  args+=(--esp32-port "${KOALABYTE_ESP32_FACE_PORT}")
fi

exec "${PYTHON_BIN}" "${args[@]}"
