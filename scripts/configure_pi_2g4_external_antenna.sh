#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

PI_2G4_EXTERNAL_ANTENNA="${PI_2G4_EXTERNAL_ANTENNA:-optional_disabled}"
PI_2G4_USB_ADAPTER_HINT="${PI_2G4_USB_ADAPTER_HINT:-optional 2.4 GHz USB WiFi/BLE adapter with external antenna connector}"
PI_2G4_INTERFACE="${PI_2G4_INTERFACE:-auto}"
STATUS_PATH="${PI_2G4_EXTERNAL_ANTENNA_STATUS_PATH:-${REPO_ROOT}/logs/pi_2g4_external_antenna_status.json}"
CHECK_ONLY=0

usage() {
  cat <<'EOF'
KoalaByte Blue Raspberry Pi 2.4 GHz optional antenna helper

Usage:
  bash scripts/configure_pi_2g4_external_antenna.sh
  bash scripts/configure_pi_2g4_external_antenna.sh --check-only
  PI_2G4_EXTERNAL_ANTENNA=optional_disabled bash scripts/configure_pi_2g4_external_antenna.sh
  PI_2G4_EXTERNAL_ANTENNA=usb_adapter_optional bash scripts/configure_pi_2g4_external_antenna.sh

Important:
  The extra case-mounted 2.4 GHz antenna is assigned to the Heltec T114 2.4 GHz antenna connector, not the Raspberry Pi.
  A Raspberry Pi USB WiFi/BLE adapter with an antenna connector is optional only.
  Missing Pi USB WiFi/BLE hardware must not fail firmware build, installer, CI, or antenna readiness checks.
  Do not solder an antenna directly to the Raspberry Pi PCB as the production/default path.
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

interface_note="not required"
if command -v iw >/dev/null 2>&1; then
  if [[ "${PI_2G4_INTERFACE}" == "auto" ]]; then
    interface_note="$(iw dev 2>/dev/null | awk '/Interface/ {print $2}' | paste -sd ',' - || true)"
    [[ -n "${interface_note}" ]] || interface_note="no optional Pi USB wireless interface detected; this is allowed"
  else
    interface_note="requested optional interface ${PI_2G4_INTERFACE}"
  fi
fi

case "${PI_2G4_EXTERNAL_ANTENNA}" in
  optional_disabled|not_required|none|disabled|DISABLED|Disabled)
    status="optional_not_required"
    reason="Pi external 2.4 GHz antenna is not required. The extra 2.4 GHz antenna is routed to the Heltec T114 board."
    physical="not connected to Pi by default; extra 2.4 GHz antenna uses the Heltec T114 2.4 GHz connector"
    requires_adapter=false
    ;;
  usb_adapter_optional|usb_adapter|external_usb|EXTERNAL_USB|external|EXTERNAL)
    status="optional_usb_adapter"
    reason="Optional Pi USB WiFi/BLE adapter path enabled. Missing adapter does not fail firmware or readiness."
    physical="optional Pi USB-A port -> USB 2.4 GHz WiFi/BLE adapter with antenna connector -> 2.4 GHz antenna"
    requires_adapter=false
    ;;
  onboard|onboard_mod|pcb_mod)
    status="unsupported_onboard_mod"
    reason="Pi onboard antenna modification is not the supported production path. The extra 2.4 GHz antenna belongs on the Heltec T114 connector."
    physical="unsupported for production/default build"
    requires_adapter=false
    ;;
  *)
    echo "Unsupported PI_2G4_EXTERNAL_ANTENNA=${PI_2G4_EXTERNAL_ANTENNA}. Use optional_disabled, usb_adapter_optional, onboard, or disabled." >&2
    exit 2
    ;;
esac

cat > "${STATUS_PATH}" <<JSON
{
  "device": "Raspberry Pi 3B+",
  "radio": "2.4 GHz WiFi/Bluetooth",
  "antenna_mode": $(json_escape "${status}"),
  "adapter_hint": $(json_escape "${PI_2G4_USB_ADAPTER_HINT}"),
  "adapter_required": ${requires_adapter},
  "interface_hint": $(json_escape "${PI_2G4_INTERFACE}"),
  "interface_check": $(json_escape "${interface_note}"),
  "physical_connection": $(json_escape "${physical}"),
  "reason": $(json_escape "${reason}"),
  "production_policy": "The additional 2.4 GHz antenna is routed to the Heltec T114 board. Pi USB WiFi/BLE adapter is optional only and must not fail firmware or readiness when absent.",
  "requires_hardware_validation": false,
  "updated_at": $(date +%s)
}
JSON

echo "Raspberry Pi 2.4 GHz optional antenna status written: ${STATUS_PATH}"
echo "${reason}"
exit 0
