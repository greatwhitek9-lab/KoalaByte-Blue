#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHONPATH="${REPO_ROOT}/pi-companion" python3 "${REPO_ROOT}/scripts/run_koala_bluez.py" all-safe "$@"
