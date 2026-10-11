#!/usr/bin/env bash
set -Eeuo pipefail

# Provision Raspberry Pi OS support for the Sony IMX500 AI Camera.
# This installs host-side firmware/model/runtime packages; it does not flash
# ESP32-S3 DualEye or Heltec T114 and does not reboot the system automatically.

if [[ "$(uname -m)" != "aarch64" && "$(uname -m)" != "armv7l" ]]; then
  echo "WARNING: this does not look like a Raspberry Pi OS ARM system (uname -m=$(uname -m))." >&2
  echo "Run this on the target Raspberry Pi, not on a development workstation." >&2
  exit 2
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "ERROR: apt-get is required. Use Raspberry Pi OS on the target Pi." >&2
  exit 2
fi

echo "[IMX500] Refreshing package metadata..."
sudo apt-get update
echo "[IMX500] Installing Raspberry Pi AI Camera runtime and sensor firmware..."
sudo apt-get install -y imx500-all python3-picamera2

echo
echo "[IMX500] Installed package versions:"
dpkg-query -W -f='${Package} ${Version}\n' imx500-all python3-picamera2 2>/dev/null || true

echo
echo "[IMX500] Sensor firmware files:"
for f in /lib/firmware/imx500_loader.fpk /lib/firmware/imx500_firmware.fpk; do
  if [[ -r "$f" ]]; then
    ls -lh "$f"
  else
    echo "MISSING: $f"
  fi
done

echo
if command -v rpicam-hello >/dev/null 2>&1; then
  echo "[IMX500] Camera enumeration (a connected camera is required):"
  rpicam-hello --list-cameras || true
else
  echo "WARNING: rpicam-hello is not on PATH yet; check the Raspberry Pi camera applications package." >&2
fi

echo
echo "IMX500 host packages installed. Reboot the Pi when convenient, then verify:"
echo "  rpicam-hello --list-cameras"
echo "  rpicam-hello -t 5000 --post-process-file /usr/share/rpi-camera-assets/imx500_mobilenet_ssd.json"
echo
echo "The first use may take several minutes while the sensor loads firmware/model data."
echo "This script does not change MCU firmware and does not confirm physical camera operation."
