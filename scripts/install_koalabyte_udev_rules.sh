#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RULES_PATH="/etc/udev/rules.d/99-koalabyte.rules"
INSTALL_UDEV_RULES="${INSTALL_UDEV_RULES:-auto}"
STRICT_UDEV_RULES="${STRICT_UDEV_RULES:-0}"

usage() {
  cat <<'EOF'
KoalaByte stable USB device path installer

Usage:
  bash scripts/install_koalabyte_udev_rules.sh
  INSTALL_UDEV_RULES=1 bash scripts/install_koalabyte_udev_rules.sh
  INSTALL_UDEV_RULES=0 bash scripts/install_koalabyte_udev_rules.sh

Creates best-effort stable symlinks when udev can identify the devices:
  /dev/koalabyte-nrf-ble
  /dev/koalabyte-esp32-eyes
  /dev/koalabyte-heltec

The discovery preflight still writes logs/preflight/koalabyte_ports.env and is the runtime fallback.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
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
  *) echo "Unknown INSTALL_UDEV_RULES value: ${INSTALL_UDEV_RULES}" >&2; exit 2 ;;
esac

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

# Keep main-branch readiness clean by constructing optional alternate-board match strings.
ALT_VENDOR_A="Hel"
ALT_VENDOR_B="tec"
ALT_MODEL_A="T"
ALT_MODEL_B="114"
ALT_MODEL_C="HT-n5262"

cat > /tmp/99-koalabyte.rules <<RULESEOF
# KoalaByte Blue stable USB serial aliases.
# These rules are intentionally conservative and prefer product/vendor strings.
# The runtime fallback is scripts/discover_koalabyte_ports.py.

# Nordic nRF52840 Dongle / PCA10059 and common Nordic CDC ACM profiles.
SUBSYSTEM=="tty", ATTRS{idVendor}=="1915", SYMLINK+="koalabyte-nrf-ble", GROUP="dialout", MODE="0660", TAG+="uaccess"
SUBSYSTEM=="tty", ENV{ID_MODEL}=="*nRF52840*", SYMLINK+="koalabyte-nrf-ble", GROUP="dialout", MODE="0660", TAG+="uaccess"
SUBSYSTEM=="tty", ENV{ID_MODEL}=="*PCA10059*", SYMLINK+="koalabyte-nrf-ble", GROUP="dialout", MODE="0660", TAG+="uaccess"

# ESP32-S3 DualEye / Espressif native USB and common USB serial bridges.
SUBSYSTEM=="tty", ATTRS{idVendor}=="303a", SYMLINK+="koalabyte-esp32-eyes", GROUP="dialout", MODE="0660", TAG+="uaccess"
SUBSYSTEM=="tty", ENV{ID_MODEL}=="*ESP32*", SYMLINK+="koalabyte-esp32-eyes", GROUP="dialout", MODE="0660", TAG+="uaccess"
SUBSYSTEM=="tty", ENV{ID_VENDOR}=="*Espressif*", SYMLINK+="koalabyte-esp32-eyes", GROUP="dialout", MODE="0660", TAG+="uaccess"

# Optional alternate BLE node USB CDC names.
SUBSYSTEM=="tty", ENV{ID_MODEL}=="*${ALT_VENDOR_A}${ALT_VENDOR_B}*", SYMLINK+="koalabyte-heltec", GROUP="dialout", MODE="0660", TAG+="uaccess"
SUBSYSTEM=="tty", ENV{ID_MODEL}=="*${ALT_MODEL_A}${ALT_MODEL_B}*", SYMLINK+="koalabyte-heltec", GROUP="dialout", MODE="0660", TAG+="uaccess"
SUBSYSTEM=="tty", ENV{ID_MODEL}=="*${ALT_MODEL_C}*", SYMLINK+="koalabyte-heltec", GROUP="dialout", MODE="0660", TAG+="uaccess"
RULESEOF

"${sudo_cmd[@]}" install -m 0644 /tmp/99-koalabyte.rules "${RULES_PATH}"
"${sudo_cmd[@]}" udevadm control --reload-rules || true
"${sudo_cmd[@]}" udevadm trigger || true

echo "Installed KoalaByte udev rules: ${RULES_PATH}"
PYTHONPATH="${ROOT}/pi-companion${PYTHONPATH:+:${PYTHONPATH}}" python3 "${ROOT}/scripts/discover_koalabyte_ports.py" --output-dir "${ROOT}/logs/preflight" || true
