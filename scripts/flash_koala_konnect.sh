#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"
bash scripts/flash_nrf52840_dongle_koala_konnect_dfu.sh "$@"
