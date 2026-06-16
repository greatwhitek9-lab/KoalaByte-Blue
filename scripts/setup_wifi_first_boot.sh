#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONNECT_WIFI_FIRST_BOOT="${CONNECT_WIFI_FIRST_BOOT:-auto}"
STRICT_WIFI_FIRST_BOOT="${STRICT_WIFI_FIRST_BOOT:-0}"
WIFI_SSID="${WIFI_SSID:-}"
WIFI_PASSWORD="${WIFI_PASSWORD:-}"
WIFI_COUNTRY="${WIFI_COUNTRY:-US}"
WIFI_INTERFACE="${WIFI_INTERFACE:-wlan0}"
WIFI_INTERACTIVE="${WIFI_INTERACTIVE:-0}"
WIFI_CONNECT_TIMEOUT="${WIFI_CONNECT_TIMEOUT:-30}"
CHECK_ONLY=0
STATUS_PATH="${WIFI_STATUS_PATH:-${REPO_ROOT}/logs/wifi_first_boot_status.json}"

usage() {
  cat <<'EOF'
KoalaByte Blue first-boot WiFi setup helper

Usage:
  WIFI_SSID="YourNetwork" WIFI_PASSWORD="YourPassword" bash scripts/setup_wifi_first_boot.sh
  WIFI_INTERACTIVE=1 bash scripts/setup_wifi_first_boot.sh
  STRICT_WIFI_FIRST_BOOT=1 WIFI_SSID="YourNetwork" WIFI_PASSWORD="YourPassword" bash scripts/setup_wifi_first_boot.sh
  bash scripts/setup_wifi_first_boot.sh --check-only

Environment:
  CONNECT_WIFI_FIRST_BOOT  auto/1/0. Default: auto. Skips if internet already works.
  STRICT_WIFI_FIRST_BOOT   1 fails install/flash if WiFi/internet is unavailable. Default: 0
  WIFI_SSID                WiFi network name. Not written to command history if provided by a secure wrapper.
  WIFI_PASSWORD            WiFi password. Never printed by this script.
  WIFI_COUNTRY             Regulatory country code. Default: US
  WIFI_INTERFACE           WiFi interface. Default: wlan0
  WIFI_INTERACTIVE         1 prompts for SSID/password when not provided.
  WIFI_CONNECT_TIMEOUT     Seconds to wait after applying WiFi settings. Default: 30

Notes:
  - Prefers NetworkManager/nmcli when available.
  - Falls back to wpa_supplicant when nmcli is unavailable.
  - Writes status to logs/wifi_first_boot_status.json without storing the WiFi password.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only)
      CHECK_ONLY=1
      CONNECT_WIFI_FIRST_BOOT=0
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

cd "${REPO_ROOT}"
mkdir -p "$(dirname "${STATUS_PATH}")"

json_status() {
  local status="$1"
  local message="$2"
  local internet="$3"
  local method="$4"
  python3 - "$STATUS_PATH" "$status" "$message" "$internet" "$method" "$WIFI_INTERFACE" "$WIFI_COUNTRY" "$WIFI_SSID" <<'PY'
import json, sys, time
path, status, message, internet, method, iface, country, ssid = sys.argv[1:9]
payload = {
    "status": status,
    "message": message,
    "internet_available": internet == "true",
    "method": method,
    "interface": iface,
    "wifi_country": country,
    "ssid_set": bool(ssid),
    "ssid": ssid if ssid else None,
    "password_stored_in_log": False,
    "updated_at": time.time(),
}
with open(path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, sort_keys=True)
PY
}

have_tool() {
  command -v "$1" >/dev/null 2>&1
}

sudo_cmd=()
if [[ "${EUID}" -eq 0 ]]; then
  sudo_cmd=()
elif have_tool sudo; then
  sudo_cmd=(sudo)
else
  sudo_cmd=()
fi

internet_ok() {
  if have_tool curl; then
    curl -fsSL --connect-timeout 8 https://github.com >/dev/null 2>&1 && return 0
    curl -fsSL --connect-timeout 8 https://developer.nordicsemi.com >/dev/null 2>&1 && return 0
  fi
  if have_tool ping; then
    ping -c 1 -W 4 1.1.1.1 >/dev/null 2>&1 && return 0
    ping -c 1 -W 4 8.8.8.8 >/dev/null 2>&1 && return 0
  fi
  return 1
}

strict_fail() {
  local message="$1"
  echo "$message" >&2
  json_status "incomplete" "$message" "false" "none"
  if [[ "${STRICT_WIFI_FIRST_BOOT}" == "1" ]]; then
    exit 1
  fi
}

apply_country() {
  if have_tool rfkill; then
    "${sudo_cmd[@]}" rfkill unblock wifi || true
  fi
  if have_tool raspi-config; then
    "${sudo_cmd[@]}" raspi-config nonint do_wifi_country "${WIFI_COUNTRY}" || true
  fi
  if have_tool iw; then
    "${sudo_cmd[@]}" iw reg set "${WIFI_COUNTRY}" || true
  fi
}

connect_nmcli() {
  if ! have_tool nmcli; then
    return 1
  fi
  echo "Using NetworkManager/nmcli for WiFi setup on ${WIFI_INTERFACE}."
  "${sudo_cmd[@]}" nmcli radio wifi on || true
  "${sudo_cmd[@]}" nmcli device wifi rescan ifname "${WIFI_INTERFACE}" || true
  if [[ -n "${WIFI_PASSWORD}" ]]; then
    "${sudo_cmd[@]}" nmcli device wifi connect "${WIFI_SSID}" password "${WIFI_PASSWORD}" ifname "${WIFI_INTERFACE}"
  else
    "${sudo_cmd[@]}" nmcli device wifi connect "${WIFI_SSID}" ifname "${WIFI_INTERFACE}"
  fi
}

connect_wpa_supplicant() {
  if ! have_tool wpa_passphrase; then
    return 1
  fi
  if [[ -z "${WIFI_PASSWORD}" ]]; then
    echo "wpa_supplicant fallback requires WIFI_PASSWORD for secured networks." >&2
    return 1
  fi
  if [[ "${#sudo_cmd[@]}" -eq 0 && "${EUID}" -ne 0 ]]; then
    echo "wpa_supplicant fallback needs root or sudo to write /etc/wpa_supplicant/wpa_supplicant.conf." >&2
    return 1
  fi
  echo "Using wpa_supplicant fallback for WiFi setup on ${WIFI_INTERFACE}."
  local tmp
  tmp="$(mktemp)"
  {
    echo "country=${WIFI_COUNTRY}"
    echo "ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev"
    echo "update_config=1"
    wpa_passphrase "${WIFI_SSID}" "${WIFI_PASSWORD}"
  } > "${tmp}"
  "${sudo_cmd[@]}" install -m 600 -o root -g root "${tmp}" /etc/wpa_supplicant/wpa_supplicant.conf
  rm -f "${tmp}"
  "${sudo_cmd[@]}" systemctl enable wpa_supplicant >/dev/null 2>&1 || true
  "${sudo_cmd[@]}" systemctl restart wpa_supplicant >/dev/null 2>&1 || true
  "${sudo_cmd[@]}" wpa_cli -i "${WIFI_INTERFACE}" reconfigure >/dev/null 2>&1 || true
  "${sudo_cmd[@]}" dhclient "${WIFI_INTERFACE}" >/dev/null 2>&1 || true
}

wait_for_internet() {
  local waited=0
  while (( waited < WIFI_CONNECT_TIMEOUT )); do
    if internet_ok; then
      return 0
    fi
    sleep 2
    waited=$((waited + 2))
  done
  return 1
}

echo "== KoalaByte Blue first-boot WiFi setup =="
echo "CONNECT_WIFI_FIRST_BOOT=${CONNECT_WIFI_FIRST_BOOT} STRICT_WIFI_FIRST_BOOT=${STRICT_WIFI_FIRST_BOOT} WIFI_INTERFACE=${WIFI_INTERFACE} WIFI_COUNTRY=${WIFI_COUNTRY}"

if [[ "${CHECK_ONLY}" == "1" ]]; then
  if internet_ok; then
    json_status "success" "Internet connectivity check passed." "true" "check-only"
    echo "Internet connectivity check passed."
    exit 0
  fi
  strict_fail "Internet connectivity check failed."
  exit 0
fi

case "${CONNECT_WIFI_FIRST_BOOT}" in
  0|false|False|no|NO|skip|SKIP)
    echo "Skipping first-boot WiFi setup by request."
    internet_ok && json_status "skipped" "WiFi setup skipped; internet is already available." "true" "skipped" || json_status "skipped" "WiFi setup skipped; internet was not verified." "false" "skipped"
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES)
    ;;
  *)
    echo "Unknown CONNECT_WIFI_FIRST_BOOT value: ${CONNECT_WIFI_FIRST_BOOT}. Use auto, 1, or 0." >&2
    exit 2
    ;;
esac

if internet_ok; then
  json_status "success" "Internet already available before WiFi setup." "true" "already-online"
  echo "Internet already available; continuing."
  exit 0
fi

if [[ -z "${WIFI_SSID}" && "${WIFI_INTERACTIVE}" == "1" && -t 0 ]]; then
  read -r -p "WiFi SSID: " WIFI_SSID
fi
if [[ -z "${WIFI_PASSWORD}" && "${WIFI_INTERACTIVE}" == "1" && -t 0 ]]; then
  read -r -s -p "WiFi password: " WIFI_PASSWORD
  echo
fi

if [[ -z "${WIFI_SSID}" ]]; then
  strict_fail "No internet is available and WIFI_SSID was not provided. Set WIFI_SSID/WIFI_PASSWORD or use WIFI_INTERACTIVE=1."
  exit 0
fi

apply_country
method="none"
if connect_nmcli; then
  method="nmcli"
elif connect_wpa_supplicant; then
  method="wpa_supplicant"
else
  strict_fail "Could not configure WiFi because neither nmcli nor wpa_supplicant setup succeeded."
  exit 0
fi

if wait_for_internet; then
  json_status "success" "WiFi connected and internet is available." "true" "${method}"
  echo "WiFi connected and internet is available."
  exit 0
fi

strict_fail "WiFi settings were applied with ${method}, but internet connectivity was not verified."
