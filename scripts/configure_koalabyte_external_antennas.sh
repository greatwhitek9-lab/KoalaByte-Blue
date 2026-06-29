#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

STATUS_PATH="${KOALABYTE_EXTERNAL_ANTENNA_STATUS_PATH:-${REPO_ROOT}/logs/koalabyte_external_antenna_status.json}"
CHECK_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) CHECK_ONLY=1 ;;
    -h|--help)
      cat <<'EOF'
KoalaByte Blue antenna readiness helper

Usage:
  bash scripts/configure_koalabyte_external_antennas.sh
  bash scripts/configure_koalabyte_external_antennas.sh --check-only

Default routing:
  - Heltec T114 LoRa uses a region-matched LoRa antenna on the LoRa connector.
  - ESP32-S3 DualEye uses its factory onboard ceramic 2.4 GHz antenna.
  - T114 2.4 GHz uses factory/onboard or board-default routing unless explicitly requested.
  - Raspberry Pi uses built-in Wi-Fi; USB Wi-Fi with external antenna is optional only.
EOF
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

mkdir -p "$(dirname "${STATUS_PATH}")"

bash scripts/configure_t114_lora_external_antenna.sh --check-only
T114_2G4_ANTENNA="${T114_2G4_ANTENNA:-onboard}" bash scripts/configure_t114_2g4_antenna.sh --check-only
ESP32S3_DUALEYE_2G4_ANTENNA="${ESP32S3_DUALEYE_2G4_ANTENNA:-onboard}" bash scripts/configure_esp32s3_dualeye_2g4_antenna.sh --check-only
PI_2G4_EXTERNAL_ANTENNA="${PI_2G4_EXTERNAL_ANTENNA:-optional_disabled}" bash scripts/configure_pi_2g4_external_antenna.sh --check-only

cat > "${STATUS_PATH}" <<JSON
{
  "status": "KOALABYTE_ANTENNAS_READY_FOR_DEFAULT_BUILD",
  "heltec_lora_status": "logs/t114_lora_external_antenna_status.json",
  "heltec_2g4_status": "logs/t114_2g4_antenna_status.json",
  "esp32s3_dualeye_2g4_status": "logs/esp32s3_dualeye_2g4_antenna_status.json",
  "pi_2g4_status": "logs/pi_2g4_external_antenna_status.json",
  "production_rules": [
    "Keep factory onboard/default 2.4 GHz antenna paths unless you have a board-specific reason to change them.",
    "Heltec LoRa still uses a region-matched LoRa antenna on the LoRa connector.",
    "Do not add case-mounted ESP32 or T114 2.4 GHz antenna pigtails for the default build.",
    "Raspberry Pi 3B+ USB WiFi/BLE adapter with external antenna is optional only and must not fail firmware when absent."
  ],
  "extra_2g4_case_antennas_required": false,
  "pi_usb_adapter_required": false,
  "updated_at": $(date +%s)
}
JSON

echo "KoalaByte antenna readiness written: ${STATUS_PATH}"
exit 0
