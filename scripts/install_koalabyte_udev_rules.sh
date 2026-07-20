#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RULES_PATH="/etc/udev/rules.d/99-koalabyte.rules"
INSTALL_UDEV_RULES="${INSTALL_UDEV_RULES:-auto}"
STRICT_UDEV_RULES="${STRICT_UDEV_RULES:-0}"
CHECK_ONLY=0

usage() {
  cat <<'EOF'
Install KoalaByte stable USB aliases and optional SocketCAN hot-plug rule.

Aliases:
  /dev/koalabyte-heltec
  /dev/koalabyte-heltec-t114
  /dev/koalabyte-esp32-dualeye
  /dev/koalabyte-esp32-eyes

The current detected identities are Heltec 2fe3:0100 and ESP32-S3 303a:1001.
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

case "${INSTALL_UDEV_RULES}" in
  0|false|False|no|NO|skip|SKIP) echo "Skipping udev rule install by request."; exit 0 ;;
  auto|AUTO|1|true|True|yes|YES) ;;
  *) echo "Unknown INSTALL_UDEV_RULES value: ${INSTALL_UDEV_RULES}" >&2; exit 2 ;;
esac

SOURCE_RULES="${ROOT}/udev/99-koalabyte-blue.rules"
[[ -f "${SOURCE_RULES}" ]] || { echo "Missing source rules: ${SOURCE_RULES}" >&2; exit 1; }

for marker in \
  'ATTRS{idVendor}=="2fe3"' \
  'ATTRS{idProduct}=="0100"' \
  'ATTRS{idVendor}=="303a"' \
  'ATTRS{idProduct}=="1001"' \
  'koalabyte-heltec-t114' \
  'koalabyte-esp32-dualeye'; do
  grep -Fq "${marker}" "${SOURCE_RULES}" || { echo "Source udev rules missing marker: ${marker}" >&2; exit 1; }
done

if [[ "${CHECK_ONLY}" == "1" ]]; then
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

"${sudo_cmd[@]}" install -m 0644 "${SOURCE_RULES}" "${RULES_PATH}"
"${sudo_cmd[@]}" udevadm control --reload-rules
"${sudo_cmd[@]}" udevadm trigger || true
"${sudo_cmd[@]}" udevadm settle || true

echo "Installed KoalaByte udev rules: ${RULES_PATH}"
PYTHONPATH="${ROOT}/pi-companion${PYTHONPATH:+:${PYTHONPATH}}" \
  python3 "${ROOT}/scripts/discover_koalabyte_ports.py" \
  --profile heltec --output-dir "${ROOT}/logs/preflight" || true
