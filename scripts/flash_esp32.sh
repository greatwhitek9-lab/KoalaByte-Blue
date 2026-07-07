#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FW_DIR="${REPO_ROOT}/firmware/esp32-dualeye"
PIO_ENV="${PIO_ENV:-}"
ESP32_PORT="${ESP32_PORT:-}"
NO_MONITOR="${NO_MONITOR:-0}"
NO_CLEAN="${NO_CLEAN:-0}"

cd "${REPO_ROOT}"
STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS:-1}" bash scripts/setup_esp32_tools.sh
bash scripts/configure_esp32s3_dualeye_2g4_antenna.sh

if [[ -z "${ESP32_PORT}" && -f scripts/discover_koalabyte_ports.py ]]; then
  echo "Auto-discovering ESP32-S3 DualEye port..."
  python3 scripts/discover_koalabyte_ports.py --profile heltec >/tmp/koalabyte_ports_discovery.json 2>/tmp/koalabyte_ports_discovery.err || true
  if [[ -f logs/preflight/koalabyte_ports.env ]]; then
    # shellcheck disable=SC1091
    source logs/preflight/koalabyte_ports.env
    ESP32_PORT="${ESP32_PORT:-${KOALABYTE_ESP32_FACE_PORT:-${KOALABYTE_ESP32_DUALEYE_BY_ID:-}}}"
  fi
fi

cd "${FW_DIR}"

PIO_COMMON_ARGS=()
if [[ -n "${PIO_ENV}" ]]; then
  PIO_COMMON_ARGS+=( -e "${PIO_ENV}" )
fi

PIO_UPLOAD_ARGS=("${PIO_COMMON_ARGS[@]}")
if [[ -n "${ESP32_PORT}" ]]; then
  PIO_UPLOAD_ARGS+=( --upload-port "${ESP32_PORT}" )
fi

MONITOR_ARGS=()
if [[ -n "${ESP32_PORT}" ]]; then
  MONITOR_ARGS+=( --port "${ESP32_PORT}" )
fi

cat <<EOF
KoalaByte Blue ESP32-S3 DualEye firmware flash helper
Firmware directory: ${FW_DIR}
Boot animation: enabled in include/config.h when ENABLE_DISPLAY_BOOT_ANIMATION=1
ESP32-S3 2.4 GHz antenna: external connector path recorded in logs/esp32s3_dualeye_2g4_antenna_status.json
Voice front end: ESP-SR AFE/VAD + WakeNet9 + MultiNet7 Q8 English command aliases; Raspberry Pi handles large vocabulary responses
PlatformIO env: ${PIO_ENV:-default}
Upload port: ${ESP32_PORT:-PlatformIO auto-detect}
EOF

if [[ -z "${ESP32_PORT}" ]]; then
  cat <<'EOF'

ESP32_PORT was not auto-discovered. PlatformIO will try auto-detect.
If upload chooses the wrong device, rerun with:
  ESP32_PORT=/dev/serial/by-id/<esp32-device> NO_MONITOR=1 bash scripts/flash_esp32.sh

For first flash on some ESP32-S3 boards, hold BOOT, tap RESET, then release BOOT when upload starts.
EOF
fi

echo
if [[ "${NO_CLEAN}" != "1" ]]; then
  echo "Cleaning previous build output..."
  pio run "${PIO_COMMON_ARGS[@]}" -t clean
else
  echo "Skipping clean because NO_CLEAN=1."
fi

echo "Building firmware..."
pio run "${PIO_COMMON_ARGS[@]}"

echo "Uploading firmware..."
pio run "${PIO_UPLOAD_ARGS[@]}" -t upload

cat <<'EOF'

Flash complete.

Expected on-device boot behavior:
  - KoalaByte Blue splash appears on the ESP32 display.
  - Dual-eye UI comes up with the KoalaByte/killerkoala theme.
  - BOOTING... progress bar advances when boot animation is enabled.
  - Serial boot JSON reports esp32_2g4_antenna as external_connector.
  - Serial voice_stack JSON reports WakeNet9/MultiNet7 front-end intent and the Pi companion brain.

Expected serial boot JSON includes:
  "boot_animation": 1
  "esp32_external_antenna": 1
  "voice_front_end": "ESP-SR AFE/VAD + WakeNet9/MultiNet7 Q8 English"
EOF

if [[ "${NO_MONITOR}" == "1" ]]; then
  echo
  echo "NO_MONITOR=1 set; skipping serial monitor."
  echo "To monitor manually: pio device monitor -b 115200 ${ESP32_PORT:+--port ${ESP32_PORT}}"
  exit 0
fi

echo
echo "Opening serial monitor at 115200 baud. Press Ctrl+C to exit."
pio device monitor -b 115200 "${MONITOR_ARGS[@]}"
