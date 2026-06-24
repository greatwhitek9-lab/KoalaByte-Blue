#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

echo "== Default T114 protocol artifact generation =="
PYTHONPATH=pi-companion python3 scripts/write_optional_t114_firmware_artifacts.py

echo "== KoalaByte antenna readiness =="
bash scripts/configure_koalabyte_external_antennas.sh --check-only

echo "Wrote logs/optional_t114_firmware_artifacts.json and KoalaByte antenna readiness status files."
