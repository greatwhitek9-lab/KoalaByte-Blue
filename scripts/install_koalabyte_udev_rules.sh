#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RULES_PATH="/etc/udev/rules.d/99-koalabyte.rules"
INSTALL_UDEV_RULES="${INSTALL_UDEV_RULES:-auto}"
STRICT_UDEV_RULES="${STRICT_UDEV_RULES:-0}"
CHECK_ONLY=0

usage() {
  cat <<'EOF'
KoalaByte Blue V2 Heltec Edition stable USB device path installer

Usage:
  bash scripts/install_koalabyte_udev_rules.sh
  bash scripts/install_koalabyte_udev_rules.sh --check-only
  INSTALL_UDEV_RULES=1 bash scripts/install_koalabyte_udev_rules.sh
  INSTALL_UDEV_RULES=0 bash scripts/install_koalabyte_udev_rules.sh

Creates best-effort stable symlinks when udev can identify the devices:
  /dev/koalabyte-heltec           Heltec T114 / nRF52840 primary BLE board
  /dev/koalabyte-esp32-dualeye    ESP32-S3 DualEye face/UI and secondary BLE node
  /dev/koalabyte-esp32-eyes       Backward-compatible ESP32 alias
  /dev/koalabyte-nrf52840         Legacy external nRF52840 compatibility alias
  /dev/koalabyte-nrf-ble          Backward-compatible nRF alias

The runtime fallback is scripts/discover_koalabyte_ports.py --profile heltec.
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

case "${INSTALL_UDEV_RULES}" in
  0|false|False|no|NO|skip|SKIP)
    echo "Skipping udev rule install by request."
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES)
    ;;
  *)
    echo "Unknown INSTALL_UDEV_RULES value: ${INSTALL_UDEV_RULES}" >&2
    exit 2
    ;;
esac

if [[ "${CHECK_ONLY}" == "1" ]]; then
  grep -q "koalabyte-heltec" "${ROOT}/udev/99-koalabyte-blue.rules" 2>/dev/null || true
  grep -q "koalabyte-esp32-dualeye" "${ROOT}/udev/99-koalabyte-blue.rules" 2>/dev/null || true
  echo "KoalaByte udev installer check-only passed."
  exit 0
fi

if ! command -v udevadm >/dev/null 2>&1; then
  echo "udevadm not found; cannot install stable device rules on this OS." >&2
  [[ "${STRICT_UDEV_RULES}" == "1" ]] && exit 1
  exit 0
fi

if [[ "${EUID}" -eq 0 ]]; then
  sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then
  sudo_cmd=(sudo)
else
  echo "Root or sudo is required to install udev rules." >&2
  [[ "${STRICT_UDEV_RULES}" == "1" ]] && exit 1
  exit 0
fi

cat > /tmp/99-koalabyte.rules <<'RULESEOF'
# KoalaByte Blue V2 Heltec Edition stable USB serial aliases.
# The runtime fallback is scripts/discover_koalabyte_ports.py --profile heltec.

# Heltec Mesh Node T114 / Nordic nRF52840 primary BLE board.
SUBSYSTEM=="tty", ATTRS{idVendor}=="1915", SYMLINK+="koalabyte-heltec", SYMLINK+="koalabyte-nrf52840", SYMLINK+="koalabyte-nrf-ble", GROUP="dialout", MODE="0660", TAG+="uaccess"
SUBSYSTEM=="tty", ENV{ID_MODEL}=="*T114*", SYMLINK+="koalabyte-heltec", GROUP="dialout", MODE="0660", TAG+="uaccess"
SUBSYSTEM=="tty", ENV{ID_MODEL}=="*nRF52840*", SYMLINK+="koalabyte-nrf52840", SYMLINK+="koalabyte-nrf-ble", GROUP="dialout", MODE="0660", TAG+="uaccess"
SUBSYSTEM=="tty", ENV{ID_MODEL}=="*PCA10059*", SYMLINK+="koalabyte-nrf52840", SYMLINK+="koalabyte-nrf-ble", GROUP="dialout", MODE="0660", TAG+="uaccess"

# ESP32-S3 DualEye / Espressif native USB and common USB serial bridges.
SUBSYSTEM=="tty", ATTRS{idVendor}=="303a", SYMLINK+="koalabyte-esp32-dualeye", SYMLINK+="koalabyte-esp32-eyes", GROUP="dialout", MODE="0660", TAG+="uaccess"
SUBSYSTEM=="tty", ENV{ID_MODEL}=="*ESP32*", SYMLINK+="koalabyte-esp32-dualeye", SYMLINK+="koalabyte-esp32-eyes", GROUP="dialout", MODE="0660", TAG+="uaccess"
SUBSYSTEM=="tty", ENV{ID_VENDOR}=="*Espressif*", SYMLINK+="koalabyte-esp32-dualeye", SYMLINK+="koalabyte-esp32-eyes", GROUP="dialout", MODE="0660", TAG+="uaccess"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", SYMLINK+="koalabyte-esp32-dualeye", SYMLINK+="koalabyte-esp32-eyes", GROUP="dialout", MODE="0660", TAG+="uaccess"
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", SYMLINK+="koalabyte-esp32-dualeye", SYMLINK+="koalabyte-esp32-eyes", GROUP="dialout", MODE="0660", TAG+="uaccess"
RULESEOF

"${sudo_cmd[@]}" install -m 0644 /tmp/99-koalabyte.rules "${RULES_PATH}"
"${sudo_cmd[@]}" udevadm control --reload-rules || true
"${sudo_cmd[@]}" udevadm trigger || true

echo "Installed KoalaByte udev rules: ${RULES_PATH}"
PYTHONPATH="${ROOT}/pi-companion${PYTHONPATH:+:${PYTHONPATH}}" python3 "${ROOT}/scripts/discover_koalabyte_ports.py" --profile heltec --output-dir "${ROOT}/logs/preflight" || true
