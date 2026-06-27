#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/pi-companion/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi
cd "${REPO_ROOT}"
PYTHONPATH="${REPO_ROOT}/pi-companion:${REPO_ROOT}:${PYTHONPATH:-}" "${PYTHON_BIN}" scripts/koalabyte_doctor.py "$@"
