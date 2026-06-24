#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

echo "== Default T114 protocol artifact generation =="
PYTHONPATH=pi-companion python3 scripts/write_optional_t114_firmware_artifacts.py
bash scripts/configure_t114_2g4_antenna.sh --check-only

echo "Wrote logs/optional_t114_firmware_artifacts.json and logs/t114_2g4_antenna_status.json"
