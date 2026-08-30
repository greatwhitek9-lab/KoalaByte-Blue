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
  0|false|False|no|NO|skip|SKIP) echo "Skipping KoalaByte udev rules by request."; exit 0 ;;
  auto|AUTO|1|true|True|yes|YES) ;;
  *) echo "Unknown INSTALL_UDEV_RULES=${INSTALL_UDEV_RULES}" >&2; exit 2 ;;
esac

SOURCE_RULES="${ROOT}/udev/99-koalabyte-blue.rules"
[[ -f "${SOURCE_RULES}" ]] || { echo "Missing ${SOURCE_RULES}" >&2; exit 1; }

for marker in \
  'ATTRS{idVendor}=="2fe3"' \
  'ATTRS{idProduct}=="0100"' \
  'ATTRS{idVendor}=="303a"' \
  'ATTRS{idProduct}=="1001"' \
  'koalabyte-heltec-t114' \
  'koalabyte-esp32-dualeye'; do
  grep -Fq "${marker}" "${SOURCE_RULES}" || { echo "Missing udev rule marker: ${marker}" >&2; exit 1; }
done

if [[ "${CHECK_ONLY}" == "1" ]]; then
  bash -n "$0"
  echo "KoalaByte udev rules source contract passed."
  exit 0
fi

if [[ "${EUID}" -eq 0 ]]; then sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then sudo_cmd=(sudo)
else echo "sudo or root is required to install udev rules." >&2; exit 1
fi

command -v udevadm >/dev/null 2>&1 || {
  echo "udevadm is required to install KoalaByte stable device aliases." >&2
  exit 1
}

"${sudo_cmd[@]}" install -m 0644 "${SOURCE_RULES}" "${RULES_PATH}"

reserved_aliases=(
  /dev/koalabyte-heltec
  /dev/koalabyte-heltec-t114
  /dev/koalabyte-esp32-dualeye
  /dev/koalabyte-esp32-eyes
  /dev/koalabyte-nrf52840
  /dev/koalabyte-nrf-ble
)
for alias in "${reserved_aliases[@]}"; do
  if [[ -L "${alias}" ]]; then
    target="$(readlink -f "${alias}" 2>/dev/null || true)"
    if [[ -n "${target}" && -c "${target}" ]]; then
      continue
    fi
    echo "Removing stale KoalaByte device symlink: ${alias}" >&2
    "${sudo_cmd[@]}" rm -f -- "${alias}"
  elif [[ -e "${alias}" && ! -c "${alias}" ]]; then
    echo "Removing invalid regular KoalaByte device alias: ${alias}" >&2
    "${sudo_cmd[@]}" rm -f -- "${alias}"
  fi
done

"${sudo_cmd[@]}" udevadm control --reload-rules
"${sudo_cmd[@]}" udevadm trigger || true
"${sudo_cmd[@]}" udevadm settle || true

echo "Installed KoalaByte udev rules: ${RULES_PATH}"
PYTHONPATH="${ROOT}/pi-companion${PYTHONPATH:+:${PYTHONPATH}}" \
  python3 "${ROOT}/scripts/discover_koalabyte_ports.py" \
  --profile heltec --output-dir "${ROOT}/logs/preflight" || true
