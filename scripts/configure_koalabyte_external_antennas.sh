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
KoalaByte Blue external antenna readiness helper

Usage:
  bash scripts/configure_koalabyte_external_antennas.sh
  bash scripts/configure_koalabyte_external_antennas.sh --check-only

Runs readiness helpers for:
  - Heltec T114 LoRa external antenna
  - Heltec T114 2.4 GHz antenna connector path
  - ESP32-S3 DualEye 2.4 GHz external antenna connector path
  - Raspberry Pi 2.4 GHz USB-adapter external antenna path
EOF
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

mkdir -p "$(dirname "${STATUS_PATH}")"

bash scripts/configure_t114_lora_external_antenna.sh --check-only
bash scripts/configure_t114_2g4_antenna.sh --check-only
bash scripts/configure_esp32s3_dualeye_2g4_antenna.sh --check-only
bash scripts/configure_pi_2g4_external_antenna.sh --check-only

cat > "${STATUS_PATH}" <<JSON
{
  "status": "KOALABYTE_EXTERNAL_ANTENNAS_READY_FOR_HARDWARE_VALIDATION",
  "heltec_lora_status": "logs/t114_lora_external_antenna_status.json",
  "heltec_2g4_status": "logs/t114_2g4_antenna_status.json",
  "esp32s3_dualeye_2g4_status": "logs/esp32s3_dualeye_2g4_antenna_status.json",
  "pi_2g4_status": "logs/pi_2g4_external_antenna_status.json",
  "production_rules": [
    "Heltec LoRa uses a region-matched LoRa antenna on the LoRa connector.",
    "Heltec 2.4 GHz uses the board 2.4 GHz antenna connector only.",
    "ESP32-S3 DualEye uses its IPEX1/U.FL/MHF1 2.4 GHz connector path.",
    "Raspberry Pi 3B+ external 2.4 GHz path uses a USB WiFi/BLE adapter with an external antenna connector."
  ],
  "updated_at": $(date +%s)
}
JSON

echo "KoalaByte external antenna readiness written: ${STATUS_PATH}"
exit 0
