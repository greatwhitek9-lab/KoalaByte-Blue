#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"
PROFILE="${KOALABYTE_PROFILE:-auto}"
SETUP_VCAN="${SETUP_VCAN:-1}"

usage() {
  cat <<'EOF'
KoalaByte hardware communication hardening helper

Usage:
  bash scripts/apply_hardware_hardening.sh
  KOALABYTE_PROFILE=main bash scripts/apply_hardware_hardening.sh
  KOALABYTE_PROFILE=heltec bash scripts/apply_hardware_hardening.sh

Runs:
  1. stable USB udev rule install
  2. USB/CAN port discovery to logs/preflight/koalabyte_ports.env
  3. persistent koalabyte-can0.service install
  4. optional vcan0 local self-test setup
  5. full non-flashing hardware report
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --no-vcan) SETUP_VCAN=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

mkdir -p logs/preflight

echo "== KoalaByte stable USB path rules =="
INSTALL_UDEV_RULES="${INSTALL_UDEV_RULES:-auto}" STRICT_UDEV_RULES="${STRICT_UDEV_RULES:-0}" bash scripts/install_koalabyte_udev_rules.sh

echo
echo "== KoalaByte port discovery =="
python3 scripts/discover_koalabyte_ports.py --profile "${PROFILE}" --output-dir logs/preflight
# shellcheck disable=SC1091
source logs/preflight/koalabyte_ports.env || true

echo
echo "== KoalaByte persistent CAN setup service =="
INSTALL_CAN0_SERVICE="${INSTALL_CAN0_SERVICE:-auto}" STRICT_CAN0_SERVICE="${STRICT_CAN0_SERVICE:-0}" bash scripts/install_can0_service.sh

if [[ "${SETUP_VCAN}" == "1" ]]; then
  echo
  echo "== KoalaByte vcan0 local self-test interface =="
  STRICT_VCAN_SETUP="${STRICT_VCAN_SETUP:-0}" bash scripts/setup_vcan0.sh || true
fi

echo
echo "== KoalaByte full non-flashing hardware preflight =="
if [[ "${SETUP_VCAN}" == "1" ]]; then
  bash scripts/preflight_all_hardware.sh --profile "${PROFILE}" --setup-vcan
else
  bash scripts/preflight_all_hardware.sh --profile "${PROFILE}"
fi
