#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${KOALABYTE_ENV_FILE:-/etc/koalabyte-blue/killerkoala.env}"
STATUS_PATH="${KOALABYTE_WIFI_PROVISION_STATUS:-${ROOT}/logs/preflight/esp32_wifi_provision.json}"
SSID="${KOALABYTE_WIFI_SSID:-}"
PASSWORD="${KOALABYTE_WIFI_PASSWORD:-}"
PI_HOST="${KOALABYTE_PI_HOST:-}"
PI_PORT="${KOALABYTE_ESP32_UDP_PORT:-42110}"
CHECK_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) CHECK_ONLY=1 ;;
    -h|--help)
      cat <<'EOF'
Securely provision the ESP32 Wi-Fi bridge from the Pi's active NetworkManager
Wi-Fi connection. Passwords are written only to the root-owned 0600 environment
file and are never printed or included in status JSON.
EOF
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

mkdir -p "$(dirname "${STATUS_PATH}")"
[[ "${PI_PORT}" =~ ^[0-9]+$ ]] && (( PI_PORT > 0 && PI_PORT <= 65535 )) || {
  echo "Invalid KOALABYTE_ESP32_UDP_PORT=${PI_PORT}" >&2
  exit 2
}

if [[ "${EUID}" -eq 0 ]]; then
  sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then
  sudo_cmd=(sudo)
else
  sudo_cmd=()
fi

write_status() {
  local status="$1" reason="$2" connection="$3" device="$4"
  SSID_VALUE="${SSID}" PASSWORD_PRESENT="$([[ -n "${PASSWORD}" ]] && echo 1 || echo 0)" \
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${connection}" \
    "${device}" "${PI_HOST}" "${PI_PORT}" "${ENV_FILE}" <<'PY'
import json, os, sys, time
from pathlib import Path
path, status, reason, connection, device, host, port, env_file = sys.argv[1:]
ssid = os.environ.get("SSID_VALUE", "")
payload = {
    "status": status,
    "reason": reason,
    "connection": connection,
    "device": device,
    "ssid": ssid,
    "password_present": os.environ.get("PASSWORD_PRESENT") == "1",
    "password_logged": False,
    "pi_host": host,
    "pi_port": int(port),
    "environment_file": env_file,
    "updated_at": time.time(),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in payload.items() if k != "ssid"}, sort_keys=True))
PY
}

connection=""
device=""
security=""
if [[ -z "${SSID}" && -z "${PASSWORD}" ]] && command -v nmcli >/dev/null 2>&1; then
  while IFS=: read -r name type dev; do
    [[ "${type}" == "802-11-wireless" && -n "${dev}" ]] || continue
    connection="${name}"
    device="${dev}"
    break
  done < <(nmcli -t -f NAME,TYPE,DEVICE connection show --active 2>/dev/null || true)

  if [[ -n "${connection}" ]]; then
    SSID="$(nmcli -g 802-11-wireless.ssid connection show "${connection}" 2>/dev/null | head -n 1 || true)"
    security="$(nmcli -g 802-11-wireless-security.key-mgmt connection show "${connection}" 2>/dev/null | head -n 1 || true)"
    if (( ${#sudo_cmd[@]} > 0 )); then
      PASSWORD="$(sudo nmcli --show-secrets -g 802-11-wireless-security.psk connection show "${connection}" 2>/dev/null | head -n 1 || true)"
    else
      PASSWORD="$(nmcli --show-secrets -g 802-11-wireless-security.psk connection show "${connection}" 2>/dev/null | head -n 1 || true)"
    fi
  fi
fi

if [[ -z "${PI_HOST}" && -n "${device}" ]] && command -v ip >/dev/null 2>&1; then
  PI_HOST="$(ip -4 -o addr show dev "${device}" scope global 2>/dev/null | awk 'NR==1 {split($4, a, "/"); print a[1]}' || true)"
fi
if [[ -z "${PI_HOST}" ]] && command -v ip >/dev/null 2>&1; then
  PI_HOST="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1; i<=NF; i++) if ($i=="src") {print $(i+1); exit}}' || true)"
fi

if [[ -z "${SSID}" ]]; then
  write_status "ESP32_WIFI_PROVISION_SKIPPED" \
    "No active NetworkManager Wi-Fi connection or explicit SSID was available." \
    "${connection}" "${device}"
  exit 0
fi
if [[ -z "${PI_HOST}" ]]; then
  write_status "ESP32_WIFI_PROVISION_SKIPPED" \
    "The Pi LAN address could not be determined; existing environment settings were preserved." \
    "${connection}" "${device}"
  exit 0
fi
if [[ -n "${security}" && "${security}" != "--" && -z "${PASSWORD}" ]]; then
  write_status "ESP32_WIFI_PROVISION_SKIPPED" \
    "The active Wi-Fi connection is secured but NetworkManager did not expose its PSK." \
    "${connection}" "${device}"
  exit 0
fi

if [[ "${CHECK_ONLY}" == "1" ]]; then
  write_status "ESP32_WIFI_PROVISION_READY" \
    "Credentials and Pi address are available; check-only mode made no changes." \
    "${connection}" "${device}"
  exit 0
fi
if (( ${#sudo_cmd[@]} == 0 && EUID != 0 )); then
  echo "Root or sudo is required to update ${ENV_FILE}." >&2
  exit 1
fi

temp_existing="$(mktemp)"
temp_new="$(mktemp)"
trap 'rm -f "${temp_existing}" "${temp_new}"' EXIT
if "${sudo_cmd[@]}" test -f "${ENV_FILE}"; then
  "${sudo_cmd[@]}" cat "${ENV_FILE}" >"${temp_existing}"
fi

python3 - "${temp_existing}" "${temp_new}" "${SSID}" "${PASSWORD}" \
  "${PI_HOST}" "${PI_PORT}" <<'PY'
import sys
from pathlib import Path
source, output, ssid, password, host, port = sys.argv[1:]
keys = {
    "KOALABYTE_WIFI_SSID": ssid,
    "KOALABYTE_WIFI_PASSWORD": password,
    "KOALABYTE_PI_HOST": host,
    "KOALABYTE_ESP32_UDP_PORT": port,
}
old = Path(source).read_text(encoding="utf-8", errors="ignore").splitlines()
kept = [line for line in old if line.split("=", 1)[0].strip() not in keys]
def quote(value: str) -> str:
    clean = value.replace("\r", "").replace("\n", "")
    return '"' + clean.replace("\\", "\\\\").replace('"', '\\"') + '"'
kept.extend(f"{key}={quote(value)}" for key, value in keys.items())
Path(output).write_text("\n".join(kept) + "\n", encoding="utf-8")
PY

"${sudo_cmd[@]}" install -d -m 0750 "$(dirname "${ENV_FILE}")"
"${sudo_cmd[@]}" install -m 0600 "${temp_new}" "${ENV_FILE}"
write_status "ESP32_WIFI_PROVISIONED" \
  "Active Wi-Fi credentials and Pi UDP address were stored for USB provisioning by the voice bridge." \
  "${connection}" "${device}"
