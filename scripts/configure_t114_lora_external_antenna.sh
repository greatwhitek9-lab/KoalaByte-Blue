#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

HELTEC_T114_LORA_ANTENNA="${HELTEC_T114_LORA_ANTENNA:-external_connector}"
HELTEC_T114_LORA_CONNECTOR="${HELTEC_T114_LORA_CONNECTOR:-u.FL/IPEX-to-SMA or board LoRa antenna connector}"
HELTEC_T114_LORA_REGION="${HELTEC_T114_LORA_REGION:-US915}"
HELTEC_T114_LORA_TX_POLICY="${HELTEC_T114_LORA_TX_POLICY:-antenna_required_before_tx}"
STATUS_PATH="${HELTEC_T114_LORA_ANTENNA_STATUS_PATH:-${REPO_ROOT}/logs/t114_lora_external_antenna_status.json}"
CHECK_ONLY=0

usage() {
  cat <<'EOF'
KoalaByte Blue Heltec T114 external LoRa antenna helper

Usage:
  bash scripts/configure_t114_lora_external_antenna.sh
  bash scripts/configure_t114_lora_external_antenna.sh --check-only
  HELTEC_T114_LORA_REGION=US915 bash scripts/configure_t114_lora_external_antenna.sh

Important:
  This is the Heltec T114 LoRa / SX1262 antenna path only.
  Use a LoRa antenna matched to the configured regional band.
  Do not attach a 2.4 GHz WiFi/Bluetooth antenna to the LoRa connector.
  Do not transmit LoRa without a matched antenna attached.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) CHECK_ONLY=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

mkdir -p "$(dirname "${STATUS_PATH}")"

json_escape() {
  python3 - <<'PY' "$1"
import json, sys
print(json.dumps(sys.argv[1]))
PY
}

case "${HELTEC_T114_LORA_ANTENNA}" in
  external_connector|external|EXTERNAL|External)
    status="external_connector"
    reason="Heltec T114 LoRa/SX1262 is configured for an external, region-matched LoRa antenna."
    physical="Heltec T114 LoRa antenna connector -> u.FL/IPEX pigtail -> SMA/RP-SMA bulkhead -> region-matched LoRa antenna"
    ;;
  disabled|DISABLED|Disabled)
    status="disabled"
    reason="Heltec T114 LoRa external antenna readiness disabled."
    physical="not requested"
    ;;
  *)
    echo "Unsupported HELTEC_T114_LORA_ANTENNA=${HELTEC_T114_LORA_ANTENNA}. Use external_connector or disabled." >&2
    exit 2
    ;;
esac

cat > "${STATUS_PATH}" <<JSON
{
  "device": "Heltec Mesh Node T114",
  "radio": "LoRa / SX1262",
  "antenna_mode": $(json_escape "${status}"),
  "connector": $(json_escape "${HELTEC_T114_LORA_CONNECTOR}"),
  "region": $(json_escape "${HELTEC_T114_LORA_REGION}"),
  "tx_policy": $(json_escape "${HELTEC_T114_LORA_TX_POLICY}"),
  "physical_connection": $(json_escape "${physical}"),
  "reason": $(json_escape "${reason}"),
  "warnings": [
    "Use an antenna matched to the configured LoRa region/frequency band.",
    "Do not attach a 2.4 GHz WiFi/Bluetooth antenna to the LoRa connector.",
    "Do not transmit LoRa without the matched antenna attached."
  ],
  "requires_hardware_validation": true,
  "updated_at": $(date +%s)
}
JSON

echo "Heltec T114 LoRa antenna status written: ${STATUS_PATH}"
echo "${reason}"
exit 0
