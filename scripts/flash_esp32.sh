#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FW_DIR="${REPO_ROOT}/firmware/esp32-dualeye"

cd "${FW_DIR}"

if ! command -v pio >/dev/null 2>&1; then
  echo "PlatformIO is not installed." >&2
  echo "Install it with: python3 -m pip install --user platformio" >&2
  exit 1
fi

echo "KoalaByte Blue ESP32-S3 DualEye firmware flash helper"
echo "Firmware directory: ${FW_DIR}"
echo "Boot animation: enabled in include/config.h when ENABLE_DISPLAY_BOOT_ANIMATION=1"
echo

echo "Cleaning previous build output..."
pio run -t clean

echo "Building firmware..."
pio run

echo "Uploading firmware..."
pio run -t upload

cat <<'EOF'

Flash complete.

Expected on-device boot behavior:
  - KoalaByte Blue splash appears on the ESP32 display.
  - Left eye pulses purple.
  - Right eye pulses true blue.
  - BOOTING... progress bar advances.

Expected serial boot JSON includes:
  "boot_animation": 1

Opening serial monitor at 115200 baud. Press Ctrl+C to exit.
EOF

pio device monitor -b 115200
