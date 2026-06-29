#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ESP32S3_DUALEYE_2G4_ANTENNA="${ESP32S3_DUALEYE_2G4_ANTENNA:-onboard}"
ESP32S3_DUALEYE_ANTENNA_CONNECTOR="${ESP32S3_DUALEYE_ANTENNA_CONNECTOR:-onboard ceramic 2.4 GHz antenna}"
ESP32S3_DUALEYE_SELECTOR_MODE="${ESP32S3_DUALEYE_SELECTOR_MODE:-factory_default}"
STATUS_PATH="${ESP32S3_DUALEYE_ANTENNA_STATUS_PATH:-${REPO_ROOT}/logs/esp32s3_dualeye_2g4_antenna_status.json}"
CHECK_ONLY=0

usage() {
  cat <<'EOF'
KoalaByte Blue ESP32-S3 DualEye 2.4 GHz antenna helper

Usage:
  bash scripts/configure_esp32s3_dualeye_2g4_antenna.sh
  ESP32S3_DUALEYE_2G4_ANTENNA=onboard bash scripts/configure_esp32s3_dualeye_2g4_antenna.sh
  ESP32S3_DUALEYE_2G4_ANTENNA=external_connector bash scripts/configure_esp32s3_dualeye_2g4_antenna.sh
  bash scripts/configure_esp32s3_dualeye_2g4_antenna.sh --check-only

Environment:
  ESP32S3_DUALEYE_2G4_ANTENNA       onboard, external_connector, or disabled. Default: onboard.
  ESP32S3_DUALEYE_ANTENNA_CONNECTOR Connector/path name used in logs. Default: onboard ceramic 2.4 GHz antenna.
  ESP32S3_DUALEYE_SELECTOR_MODE     factory_default, vendor_board_config, external_antenna_variant, or selector_verified.

Default:
  Leave the Waveshare onboard ceramic antenna path active. The optional IPEX1 path is for advanced hardware configurations only.
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
  onboard|ONBOARD|Onboard|factory|FACTORY|Factory)
    status="onboard"
    reason="ESP32-S3 DualEye uses the factory onboard ceramic 2.4 GHz antenna path. No case-mounted ESP32 antenna is required."
    physical="factory onboard ceramic antenna path"
    required=false
    ;;
  external_connector|external|EXTERNAL|External)
    status="external_connector_optional"
    reason="ESP32-S3 DualEye external antenna path requested. Confirm the exact board hardware is configured for the IPEX1 path before using it."
    physical="ESP32-S3 DualEye 2.4 GHz IPEX1/U.FL/MHF1 connector path, if the board is configured for it"
    required=false
    ;;
  disabled|DISABLED|Disabled)
    status="disabled"
    reason="ESP32-S3 DualEye radio antenna validation disabled."
    physical="not requested"
    required=false
    ;;
  *)
    echo "Unsupported ESP32S3_DUALEYE_2G4_ANTENNA=${ESP32S3_DUALEYE_2G4_ANTENNA}. Use onboard, external_connector, or disabled." >&2
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
  "external_case_antenna_required": ${required},
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
