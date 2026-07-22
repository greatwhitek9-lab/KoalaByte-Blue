#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="before-build"
STATUS_PATH="${KOALABYTE_FIRMWARE_HOST_PREFLIGHT_STATUS:-${ROOT}/logs/preflight/firmware_host_preflight.json}"
MIN_BUILD_FREE_KB="${KOALABYTE_MIN_BUILD_FREE_KB:-16777216}"
MIN_FLASH_FREE_KB="${KOALABYTE_MIN_FLASH_FREE_KB:-1048576}"
MIN_TOTAL_MEMORY_KB="${KOALABYTE_MIN_TOTAL_MEMORY_KB:-900000}"
STRICT_POWER="${KOALABYTE_STRICT_POWER_PREFLIGHT:-1}"

usage() {
  cat <<'EOF'
Validate the host before KoalaByte firmware builds or hardware flashing.

Usage:
  bash scripts/preflight_firmware_host.sh --before-build
  bash scripts/preflight_firmware_host.sh --before-flash

The build check requires a supported 64-bit host, sufficient persistent storage,
working HTTPS access, writable storage, and adequate RAM plus swap. On Raspberry
Pi hardware, both checks reject any under-voltage event recorded since boot.
Reboot after correcting the power supply so the firmware flash starts from a
clean power-health state.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --before-build) MODE="before-build" ;;
    --before-flash) MODE="before-flash" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

mkdir -p "$(dirname "${STATUS_PATH}")"

warnings=()
failures=()
arch="$(uname -m)"
long_bits="$(getconf LONG_BIT 2>/dev/null || echo 0)"
model=""
if [[ -r /proc/device-tree/model ]]; then
  model="$(tr -d '\0' </proc/device-tree/model)"
fi

is_enabled() {
  case "$1" in
    1|true|True|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

if [[ "${MODE}" == "before-build" ]]; then
  case "${arch}" in
    x86_64|amd64|aarch64|arm64) ;;
    armv6l|armv7l)
      failures+=("32-bit ARM host ${arch} is unsupported by the Zephyr SDK Linux archives; install 64-bit Raspberry Pi OS Lite so uname -m reports aarch64")
      ;;
    *) failures+=("unsupported firmware-build host architecture: ${arch}") ;;
  esac
  if [[ "${long_bits}" != "64" ]]; then
    failures+=("firmware builds require a 64-bit userspace; getconf LONG_BIT reported ${long_bits}")
  fi
fi

free_required_kb="${MIN_FLASH_FREE_KB}"
[[ "${MODE}" == "before-build" ]] && free_required_kb="${MIN_BUILD_FREE_KB}"
available_kb="$(df -Pk "${ROOT}" | awk 'NR == 2 {print $4}')"
if [[ ! "${available_kb}" =~ ^[0-9]+$ ]]; then
  failures+=("unable to determine free space for ${ROOT}")
elif (( available_kb < free_required_kb )); then
  failures+=("only $((available_kb / 1024 / 1024)) GiB is free at ${ROOT}; ${MODE} requires at least $((free_required_kb / 1024 / 1024)) GiB")
fi

available_inodes="$(df -Pi "${ROOT}" | awk 'NR == 2 {print $4}')"
if [[ "${available_inodes}" =~ ^[0-9]+$ ]] && (( available_inodes < 50000 )); then
  failures+=("fewer than 50000 inodes remain on the repository filesystem")
fi

write_probe="${ROOT}/.koalabyte-write-test.$$"
if ! (umask 077; printf 'ok\n' >"${write_probe}" && rm -f "${write_probe}"); then
  failures+=("repository filesystem is not writable: ${ROOT}")
fi

mem_kb="$(awk '/^MemTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
swap_kb="$(awk '/^SwapTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
[[ "${mem_kb}" =~ ^[0-9]+$ ]] || mem_kb=0
[[ "${swap_kb}" =~ ^[0-9]+$ ]] || swap_kb=0
total_memory_kb=$((mem_kb + swap_kb))
if [[ "${MODE}" == "before-build" && ${total_memory_kb} -lt ${MIN_TOTAL_MEMORY_KB} ]]; then
  failures+=("RAM plus swap is only $((total_memory_kb / 1024)) MiB; at least $((MIN_TOTAL_MEMORY_KB / 1024)) MiB is required")
elif [[ "${MODE}" == "before-build" && ${total_memory_kb} -lt 2097152 ]]; then
  warnings+=("low-memory host detected ($((mem_kb / 1024)) MiB RAM, $((swap_kb / 1024)) MiB swap); firmware builds will be forced to one job")
fi

throttled_raw="unavailable"
throttled_value=0
if command -v vcgencmd >/dev/null 2>&1; then
  throttled_raw="$(vcgencmd get_throttled 2>/dev/null || echo throttled=unavailable)"
  throttled_hex="${throttled_raw#throttled=}"
  if [[ "${throttled_hex}" =~ ^0x[0-9a-fA-F]+$ ]]; then
    throttled_value=$((throttled_hex))
    if (( throttled_value & 0x10001 )); then
      message="Raspberry Pi under-voltage is current or has occurred since boot (${throttled_raw}); replace the supply/cable and reboot before continuing"
      if is_enabled "${STRICT_POWER}"; then failures+=("${message}"); else warnings+=("${message}"); fi
    fi
    if (( throttled_value & 0x80008 )); then
      warnings+=("Raspberry Pi temperature limiting is current or has occurred since boot (${throttled_raw}); provide airflow before a long build")
    fi
    if (( throttled_value & 0x60006 )); then
      warnings+=("Raspberry Pi frequency capping or throttling is current or has occurred since boot (${throttled_raw})")
    fi
  else
    warnings+=("could not parse Raspberry Pi power state: ${throttled_raw}")
  fi
fi

current_year="$(date +%Y 2>/dev/null || echo 0)"
if [[ ! "${current_year}" =~ ^[0-9]+$ ]] || (( current_year < 2025 )); then
  failures+=("system clock is invalid; TLS downloads will fail until network time is synchronized")
fi

if [[ "${MODE}" == "before-build" ]]; then
  if ! command -v curl >/dev/null 2>&1; then
    failures+=("curl is required for dependency downloads")
  else
    for endpoint in https://github.com https://pypi.org/simple/; do
      if ! curl -fsSI --connect-timeout 10 --max-time 20 "${endpoint}" >/dev/null 2>&1; then
        failures+=("HTTPS preflight failed: ${endpoint}")
      fi
    done
  fi
fi

status="ready"
reason="host preflight passed"
if (( ${#failures[@]} > 0 )); then
  status="failed"
  reason="host preflight found blocking conditions"
elif (( ${#warnings[@]} > 0 )); then
  status="ready_with_warnings"
  reason="host preflight passed with warnings"
fi

WARNINGS_TEXT="$(printf '%s\n' "${warnings[@]:-}")" \
FAILURES_TEXT="$(printf '%s\n' "${failures[@]:-}")" \
python3 - "${STATUS_PATH}" "${status}" "${reason}" "${MODE}" "${arch}" \
  "${long_bits}" "${model}" "${available_kb:-0}" "${mem_kb}" "${swap_kb}" \
  "${throttled_raw}" <<'PY'
import json
import os
import sys
import time
from pathlib import Path

(path, status, reason, mode, arch, long_bits, model, available_kb,
 mem_kb, swap_kb, throttled) = sys.argv[1:]
payload = {
    "status": status,
    "reason": reason,
    "mode": mode,
    "architecture": arch,
    "userspace_bits": int(long_bits) if long_bits.isdigit() else 0,
    "model": model,
    "free_gib": round(int(available_kb) / 1024 / 1024, 2),
    "memory_mib": round(int(mem_kb) / 1024, 1),
    "swap_mib": round(int(swap_kb) / 1024, 1),
    "raspberry_pi_throttled": throttled,
    "warnings": [x for x in os.environ.get("WARNINGS_TEXT", "").splitlines() if x],
    "failures": [x for x in os.environ.get("FAILURES_TEXT", "").splitlines() if x],
    "updated_at": time.time(),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

echo "== KoalaByte firmware host preflight (${MODE}) =="
echo "Host: ${model:-unknown} ${arch} (${long_bits}-bit)"
echo "Storage: $((available_kb / 1024 / 1024)) GiB free"
echo "Memory: $((mem_kb / 1024)) MiB RAM + $((swap_kb / 1024)) MiB swap"
echo "Power: ${throttled_raw}"
for item in "${warnings[@]:-}"; do [[ -n "${item}" ]] && echo "warning: ${item}" >&2; done
for item in "${failures[@]:-}"; do [[ -n "${item}" ]] && echo "error: ${item}" >&2; done

(( ${#failures[@]} == 0 ))
