#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

PI_2G4_EXTERNAL_ANTENNA="${PI_2G4_EXTERNAL_ANTENNA:-usb_adapter}"
PI_2G4_USB_ADAPTER_HINT="${PI_2G4_USB_ADAPTER_HINT:-2.4 GHz USB WiFi/BLE adapter with external antenna connector}"
PI_2G4_INTERFACE="${PI_2G4_INTERFACE:-auto}"
STATUS_PATH="${PI_2G4_EXTERNAL_ANTENNA_STATUS_PATH:-${REPO_ROOT}/logs/pi_2g4_external_antenna_status.json}"
CHECK_ONLY=0

usage() {
  cat <<'EOF'
KoalaByte Blue Raspberry Pi 2.4 GHz external antenna helper

Usage:
  bash scripts/configure_pi_2g4_external_antenna.sh
  bash scripts/configure_pi_2g4_external_antenna.sh --check-only
  PI_2G4_EXTERNAL_ANTENNA=usb_adapter bash scripts/configure_pi_2g4_external_antenna.sh

Important:
  Raspberry Pi 3B+ onboard WiFi/Bluetooth is not treated as an external-antenna radio in this project.
  The supported external 2.4 GHz path is a USB WiFi/Bluetooth adapter with a proper external antenna connector.
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

interface_note="not checked"
if command -v iw >/dev/null 2>&1; then
  if [[ "${PI_2G4_INTERFACE}" == "auto" ]]; then
    interface_note="$(iw dev 2>/dev/null | awk '/Interface/ {print $2}' | paste -sd ',' - || true)"
    [[ -n "${interface_note}" ]] || interface_note="no wireless interfaces reported by iw"
  else
    interface_note="requested interface ${PI_2G4_INTERFACE}"
  fi
fi

case "${PI_2G4_EXTERNAL_ANTENNA}" in
  usb_adapter|external_usb|EXTERNAL_USB|external|EXTERNAL)
    status="usb_adapter_required"
    reason="Raspberry Pi external 2.4 GHz antenna path is configured through an external USB WiFi/BLE adapter with an antenna connector."
    physical="Pi USB-A port -> USB 2.4 GHz WiFi/BLE adapter with SMA/RP-SMA/IPEX antenna connector -> 2.4 GHz antenna"
    ;;
  onboard|onboard_mod|pcb_mod)
    status="unsupported_onboard_mod"
    reason="Pi onboard antenna modification is not the supported production path; use a USB adapter with an antenna connector."
    physical="unsupported for production/default build"
    ;;
  disabled|DISABLED|Disabled)
    status="disabled"
    reason="Pi 2.4 GHz external antenna readiness disabled."
    physical="not requested"
    ;;
  *)
    echo "Unsupported PI_2G4_EXTERNAL_ANTENNA=${PI_2G4_EXTERNAL_ANTENNA}. Use usb_adapter, onboard, or disabled." >&2
    exit 2
    ;;
esac

cat > "${STATUS_PATH}" <<JSON
{
  "device": "Raspberry Pi 3B+",
  "radio": "2.4 GHz WiFi/Bluetooth",
  "antenna_mode": $(json_escape "${status}"),
  "adapter_hint": $(json_escape "${PI_2G4_USB_ADAPTER_HINT}"),
  "interface_hint": $(json_escape "${PI_2G4_INTERFACE}"),
  "interface_check": $(json_escape "${interface_note}"),
  "physical_connection": $(json_escape "${physical}"),
  "reason": $(json_escape "${reason}"),
  "production_policy": "Use an external USB WiFi/BLE adapter with an antenna connector. Do not solder to the Pi 3B+ onboard antenna path as the default build.",
  "requires_hardware_validation": true,
  "updated_at": $(date +%s)
}
JSON

echo "Raspberry Pi 2.4 GHz external antenna status written: ${STATUS_PATH}"
echo "${reason}"
exit 0
