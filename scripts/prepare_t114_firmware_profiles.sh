#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

T114_BOARD="${T114_BOARD:-heltec_t114_v2/nrf52840}"
OUT_DIR="logs/t114_profiles"
mkdir -p "${OUT_DIR}"

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
STATUS_JSON="${OUT_DIR}/prepare_status.json"

cat > "${STATUS_JSON}" <<JSON
{
  "status": "running",
  "started_at": "${STARTED_AT}",
  "branch_profile": "koalabyte_blue_v2_heltec_edition",
  "hardware_target": "Heltec Mesh Node T114 v2 onboard nRF52840",
  "t114_board": "${T114_BOARD}",
  "profiles": ["heltec_lab", "koala_konnect_t114"]
}
JSON

echo "== Preparing Heltec T114 firmware profiles =="
echo "Target: Heltec Mesh Node T114 v2 onboard nRF52840"
echo "Profile 1: Heltec Lab / mouth / BLE / GNSS"
echo "Profile 2: Koala Konnect T114 USB-HCI"

echo
echo "== Build check: Heltec Lab / mouth / BLE / GNSS profile =="
BUILD_ONLY=1 bash scripts/flash_heltec_mouth.sh --build-only

echo
echo "== Build check: Koala Konnect T114 USB-HCI profile =="
T114_BOARD="${T114_BOARD}" bash scripts/build_koala_konnect_t114.sh

FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
cat > "${STATUS_JSON}" <<JSON
{
  "status": "success",
  "started_at": "${STARTED_AT}",
  "finished_at": "${FINISHED_AT}",
  "branch_profile": "koalabyte_blue_v2_heltec_edition",
  "hardware_target": "Heltec Mesh Node T114 v2 onboard nRF52840",
  "t114_board": "${T114_BOARD}",
  "prepared_profiles": {
    "heltec_lab": {
      "title": "Heltec Lab / mouth / BLE / GNSS",
      "helper": "scripts/flash_heltec_mouth.sh",
      "build_path": "firmware/heltec-mouth"
    },
    "koala_konnect_t114": {
      "title": "Koala Konnect T114 USB-HCI",
      "helper": "scripts/flash_koala_konnect_t114.sh",
      "board_target": "${T114_BOARD}"
    }
  },
  "next_step": "At startup, run scripts/select_t114_startup_mode.sh or let scripts/koalabyte_blue_boot.sh prompt for the active T114 profile."
}
JSON

echo "T114 profile preparation complete: ${STATUS_JSON}"
