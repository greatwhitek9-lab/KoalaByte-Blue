#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ESP32S3_DUALEYE_2G4_ANTENNA="${ESP32S3_DUALEYE_2G4_ANTENNA:-external_connector}"
ESP32S3_DUALEYE_ANTENNA_CONNECTOR="${ESP32S3_DUALEYE_ANTENNA_CONNECTOR:-IPEX1/U.FL/MHF1 2.4 GHz connector}"
ESP32S3_DUALEYE_SELECTOR_MODE="${ESP32S3_DUALEYE_SELECTOR_MODE:-vendor_board_config}"
STATUS_PATH="${ESP32S3_DUALEYE_ANTENNA_STATUS_PATH:-${REPO_ROOT}/logs/esp32s3_dualeye_2g4_antenna_status.json}"
CHECK_ONLY=0

usage() {
  cat <<'EOF'
KoalaByte Blue ESP32-S3 DualEye external 2.4 GHz antenna helper

Usage:
  bash scripts/configure_esp32s3_dualeye_2g4_antenna.sh
  ESP32S3_DUALEYE_2G4_ANTENNA=external_connector bash scripts/configure_esp32s3_dualeye_2g4_antenna.sh
  bash scripts/configure_esp32s3_dualeye_2g4_antenna.sh --check-only

Environment:
  ESP32S3_DUALEYE_2G4_ANTENNA       external_connector, onboard, or disabled. Default: external_connector.
  ESP32S3_DUALEYE_ANTENNA_CONNECTOR Connector name used in logs. Default: IPEX1/U.FL/MHF1 2.4 GHz connector.
  ESP32S3_DUALEYE_SELECTOR_MODE     vendor_board_config, external_antenna_variant, or selector_resistor_verified.

Important:
  This is the ESP32-S3 DualEye antenna path only.
  The ESP32-S3 external antenna is a physical board configuration. Firmware records and reports the expected mode,
  but the board must have the external antenna connector populated and, where required by that board revision,
  its antenna selector resistor/jumper must be set according to the vendor documentation.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only)
      CHECK_ONLY=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

cd "${REPO_ROOT}"
mkdir -p "$(dirname "${STATUS_PATH}")"

json_escape() {
  python3 - <<'PY' "$1"
import json, sys
print(json.dumps(sys.argv[1]))
PY
}

case "${ESP32S3_DUALEYE_2G4_ANTENNA}" in
  external_connector|external|EXTERNAL|External)
    status="external_connector"
    reason="ESP32-S3 DualEye is configured for the board's external 2.4 GHz antenna connector. Attach a 2.4 GHz antenna through the IPEX/U.FL pigtail/bulkhead path."
    physical="ESP32-S3 DualEye 2.4 GHz / IPEX1/U.FL/MHF1 antenna connector -> IPEX/U.FL pigtail -> SMA/RP-SMA bulkhead -> 2.4 GHz antenna"
    ;;
  onboard|ONBOARD|Onboard)
    status="onboard"
    reason="ESP32-S3 DualEye external antenna path disabled; using onboard antenna path if the board variant supports it."
    physical="onboard antenna path"
    ;;
  disabled|DISABLED|Disabled)
    status="disabled"
    reason="ESP32-S3 DualEye radio antenna validation disabled."
    physical="not requested"
    ;;
  *)
    echo "Unsupported ESP32S3_DUALEYE_2G4_ANTENNA=${ESP32S3_DUALEYE_2G4_ANTENNA}. Use external_connector, onboard, or disabled." >&2
    exit 2
    ;;
esac

cat > "${STATUS_PATH}" <<JSON
{
  "device": "ESP32-S3 DualEye",
  "radio": "2.4 GHz WiFi/Bluetooth",
  "antenna_mode": $(json_escape "${status}"),
  "connector": $(json_escape "${ESP32S3_DUALEYE_ANTENNA_CONNECTOR}"),
  "selector_mode": $(json_escape "${ESP32S3_DUALEYE_SELECTOR_MODE}"),
  "physical_connection": $(json_escape "${physical}"),
  "reason": $(json_escape "${reason}"),
  "firmware_config": "firmware/esp32-dualeye/include/config.h",
  "production_wiring_doc": "production/WIRING_DIAGRAM_ANTENNAS.md",
  "requires_hardware_validation": true,
  "updated_at": $(date +%s)
}
JSON

echo "ESP32-S3 DualEye 2.4 GHz antenna status written: ${STATUS_PATH}"
echo "${reason}"
if [[ "${CHECK_ONLY}" == "1" ]]; then
  exit 0
fi
