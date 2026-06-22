#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"
export PYTHONPATH="${ROOT}/pi-companion${PYTHONPATH:+:${PYTHONPATH}}"

exec python3 scripts/preflight_all_hardware.py "$@"
