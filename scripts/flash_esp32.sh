#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../firmware/esp32-dualeye"
if ! command -v pio >/dev/null 2>&1; then
  echo "PlatformIO is not installed. Install it with: python3 -m pip install --user platformio" >&2
  exit 1
fi
pio run
pio run -t upload
printf '\nFlash complete. Opening serial monitor at 115200 baud. Press Ctrl+C to exit.\n'
pio device monitor -b 115200
