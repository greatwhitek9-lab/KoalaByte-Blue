#!/usr/bin/env bash
set -euo pipefail

# KoalaByte Blue Heltec T114 / HT-n5262 HCI USB UF2-first one-shot wrapper.
# This intentionally selects the hci-usb / Koala Konnect profile and requires
# the HT-n5262 UF2 bootloader volume. It uses the proven Platypus-derived fix:
#   - board target: heltec_t114_v2/nrf52840/uf2
#   - app offset:   0x1000
#   - app size:     0xdf000
#   - UF2 family:   0x239a0071

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

cat <<'EOF'

============================================================
 KoalaByte Blue Heltec T114 HCI USB UF2-first one-shot
============================================================

Before continuing:
  1. Plug the Heltec T114 into the Raspberry Pi or Linux host.
  2. Double-tap RST on the T114.
  3. Wait for the HT-n5262 UF2 bootloader volume to appear.

This wrapper forces:
  T114_PLUG_FLASH_PROFILE=hci-usb
  T114_REQUIRE_UF2=1
  T114_FLASH_METHOD=uf2

EOF

export FLASH_T114_ON_PLUG="${FLASH_T114_ON_PLUG:-1}"
export STRICT_T114_PLUG_FLASH="${STRICT_T114_PLUG_FLASH:-1}"
export T114_PLUG_FLASH_PROFILE="hci-usb"
export T114_REQUIRE_UF2="1"
export T114_FLASH_METHOD="uf2"
export T114_BOARD="${T114_BOARD:-heltec_t114_v2/nrf52840/uf2}"
export T114_FLASH_LOAD_OFFSET="${T114_FLASH_LOAD_OFFSET:-0x1000}"
export T114_FLASH_LOAD_SIZE="${T114_FLASH_LOAD_SIZE:-0xdf000}"
export T114_UF2_FAMILY="${T114_UF2_FAMILY:-0x239a0071}"
export T114_RELEASE_UF2="${T114_RELEASE_UF2:-releases/koalabyte-blue-t114-hci-usb-HT-n5262-offset1000.uf2}"

bash scripts/install_koalabyte_one_shot.sh "$@"
