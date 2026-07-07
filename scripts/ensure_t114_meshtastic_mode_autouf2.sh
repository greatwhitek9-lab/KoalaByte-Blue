#!/usr/bin/env bash
set -euo pipefail

# Wrapper used by menu actions before Meshtastic commands.
# It tries software UF2 entry first, then runs the normal Meshtastic mode helper.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

if [[ "${T114_SOFTWARE_BOOTLOADER:-1}" == "1" ]]; then
  if [[ -f scripts/enter_t114_uf2_bootloader.sh ]]; then
    bash scripts/enter_t114_uf2_bootloader.sh >/tmp/koalabyte_t114_autouf2.out 2>/tmp/koalabyte_t114_autouf2.err || true
  fi
fi

bash scripts/ensure_t114_meshtastic_mode.sh "$@"
