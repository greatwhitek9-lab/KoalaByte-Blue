#!/usr/bin/env bash
set -euo pipefail

# KoalaByte Blue ESP32-S3 DualEye Touch USB serial detection helper.
# David's live board appears as an ESPRESSIF USB JTAG serial debug unit and,
# with the Heltec T114 already present on ttyACM0, usually maps to ttyACM1.
# Prefer /dev/serial/by-id and fall back only after excluding the Heltec path.

KOALABYTE_ESP32_DUALEYE_USB_ID="${KOALABYTE_ESP32_DUALEYE_USB_ID:-usb-ESPRESSIF_USB_JTAG_serial_debug_unit_A0:F2:62:E3:DE:54-if00}"
KOALABYTE_ESP32_DUALEYE_BY_ID="${KOALABYTE_ESP32_DUALEYE_BY_ID:-/dev/serial/by-id/${KOALABYTE_ESP32_DUALEYE_USB_ID}}"
KOALABYTE_ESP32_DEVICE_ENV="${KOALABYTE_ESP32_DEVICE_ENV:-/etc/koalabyte-blue/device.env}"

resolve_esp32_dualeye_port() {
  local candidate=""
  local heltec_resolved=""

  if [[ -n "${ESP32_PORT:-}" && -e "${ESP32_PORT}" ]]; then
    printf '%s\n' "${ESP32_PORT}"
    return 0
  fi

  if [[ -n "${KOALABYTE_ESP32_FACE_PORT:-}" && -e "${KOALABYTE_ESP32_FACE_PORT}" ]]; then
    printf '%s\n' "${KOALABYTE_ESP32_FACE_PORT}"
    return 0
  fi

  if [[ -e "${KOALABYTE_ESP32_DUALEYE_BY_ID}" ]]; then
    printf '%s\n' "${KOALABYTE_ESP32_DUALEYE_BY_ID}"
    return 0
  fi

  candidate="$(ls /dev/serial/by-id/* 2>/dev/null | grep -Eim1 'ESPRESSIF|Espressif|USB[_-]?JTAG|serial[_-]?debug|A0:F2:62:E3:DE:54|esp32|esp32-s3' || true)"
  if [[ -n "${candidate}" && -e "${candidate}" ]]; then
    printf '%s\n' "${candidate}"
    return 0
  fi

  if [[ -n "${HELTEC_PORT:-}" && -e "${HELTEC_PORT}" ]]; then
    heltec_resolved="$(readlink -f "${HELTEC_PORT}" 2>/dev/null || true)"
  elif [[ -e /dev/serial/by-id/usb_Heltec_HT_n5262_F0E6F99E30161F35-if00 ]]; then
    heltec_resolved="$(readlink -f /dev/serial/by-id/usb_Heltec_HT_n5262_F0E6F99E30161F35-if00 2>/dev/null || true)"
  fi

  for candidate in /dev/koalabyte-esp32-dualeye /dev/koalabyte-esp32-eyes /dev/ttyACM1 /dev/ttyUSB0 /dev/ttyUSB1 /dev/ttyACM0; do
    if [[ -e "${candidate}" ]]; then
      if [[ -n "${heltec_resolved}" && "$(readlink -f "${candidate}" 2>/dev/null || true)" == "${heltec_resolved}" ]]; then
        continue
      fi
      printf '%s\n' "${candidate}"
      return 0
    fi
  done

  return 1
}

write_esp32_dualeye_env_file() {
  local port="$1"
  local env_path="${2:-${KOALABYTE_ESP32_DEVICE_ENV}}"
  local env_dir
  env_dir="$(dirname "${env_path}")"

  if [[ "${EUID}" -eq 0 ]]; then
    mkdir -p "${env_dir}"
    {
      echo "ESP32_PORT=${port}"
      echo "KOALABYTE_ESP32_FACE_PORT=${port}"
      echo "KOALABYTE_ESP32_MIC_PORT=${port}"
      echo "ESP32_DUALEYE_USB_ID=${KOALABYTE_ESP32_DUALEYE_USB_ID}"
      echo "KOALABYTE_ESP32_DUALEYE_BY_ID=${KOALABYTE_ESP32_DUALEYE_BY_ID}"
    } >> "${env_path}"
  elif command -v sudo >/dev/null 2>&1; then
    sudo mkdir -p "${env_dir}"
    {
      echo "ESP32_PORT=${port}"
      echo "KOALABYTE_ESP32_FACE_PORT=${port}"
      echo "KOALABYTE_ESP32_MIC_PORT=${port}"
      echo "ESP32_DUALEYE_USB_ID=${KOALABYTE_ESP32_DUALEYE_USB_ID}"
      echo "KOALABYTE_ESP32_DUALEYE_BY_ID=${KOALABYTE_ESP32_DUALEYE_BY_ID}"
    } | sudo tee -a "${env_path}" >/dev/null
  else
    return 1
  fi
}

print_esp32_dualeye_exports() {
  local port="$1"
  printf "export ESP32_PORT='%s'\n" "${port}"
  printf "export KOALABYTE_ESP32_FACE_PORT='%s'\n" "${port}"
  printf "export KOALABYTE_ESP32_MIC_PORT='%s'\n" "${port}"
  printf "export ESP32_DUALEYE_USB_ID='%s'\n" "${KOALABYTE_ESP32_DUALEYE_USB_ID}"
  printf "export KOALABYTE_ESP32_DUALEYE_BY_ID='%s'\n" "${KOALABYTE_ESP32_DUALEYE_BY_ID}"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  MODE="detect"
  case "${1:-}" in
    --env) MODE="env" ;;
    --write-device-env) MODE="write" ;;
    --check-only|"") MODE="detect" ;;
    -h|--help)
      cat <<'EOF'
Usage:
  bash scripts/detect_esp32_dualeye.sh
  bash scripts/detect_esp32_dualeye.sh --env
  bash scripts/detect_esp32_dualeye.sh --write-device-env

Detects the KoalaByte Blue ESP32-S3 DualEye Touch serial port. Preferred pattern:
  ESPRESSIF USB JTAG serial debug unit A0:F2:62:E3:DE:54
Common fallback with Heltec also plugged in:
  /dev/ttyACM1
EOF
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac

  if ! ESP32_DUALEYE_PORT="$(resolve_esp32_dualeye_port)"; then
    echo "ESP32-S3 DualEye Touch not detected. Plug it in with a USB data cable and try again." >&2
    exit 1
  fi

  case "${MODE}" in
    env)
      print_esp32_dualeye_exports "${ESP32_DUALEYE_PORT}"
      ;;
    write)
      write_esp32_dualeye_env_file "${ESP32_DUALEYE_PORT}"
      echo "ESP32-S3 DualEye device env updated in ${KOALABYTE_ESP32_DEVICE_ENV}: ${ESP32_DUALEYE_PORT}"
      ;;
    detect)
      echo "ESP32-S3 DualEye detected at: ${ESP32_DUALEYE_PORT}"
      ;;
  esac
fi
