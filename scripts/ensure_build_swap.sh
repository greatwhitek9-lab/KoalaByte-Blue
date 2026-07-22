#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_TOTAL_KB="${KOALABYTE_BUILD_MEMORY_TARGET_KB:-2097152}"
SWAPFILE="${KOALABYTE_BUILD_SWAPFILE:-/var/lib/koalabyte/build.swap}"
MAX_SWAP_MIB="${KOALABYTE_MAX_BUILD_SWAP_MIB:-2048}"
STATUS_PATH="${KOALABYTE_BUILD_SWAP_STATUS:-${ROOT}/logs/preflight/build_swap.json}"
SERVICE_NAME="koalabyte-swap.service"

mkdir -p "$(dirname "${STATUS_PATH}")"
mem_kb="$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)"
swap_kb="$(awk '/^SwapTotal:/ {print $2}' /proc/meminfo)"
[[ "${mem_kb}" =~ ^[0-9]+$ ]] || mem_kb=0
[[ "${swap_kb}" =~ ^[0-9]+$ ]] || swap_kb=0

swap_tool="$(command -v swapon || true)"
swapoff_tool="$(command -v swapoff || true)"
mkswap_tool="$(command -v mkswap || true)"
grep_tool="$(command -v grep || true)"
[[ -n "${swap_tool}" && -n "${swapoff_tool}" && -n "${mkswap_tool}" && -n "${grep_tool}" ]] || {
  echo "swapon, swapoff, mkswap, and grep are required to manage KoalaByte swap." >&2
  exit 1
}

active_koalabyte_swap_kb=0
while read -r active_name active_bytes; do
  [[ "${active_name}" == "${SWAPFILE}" ]] || continue
  [[ "${active_bytes}" =~ ^[0-9]+$ ]] || active_bytes=0
  active_koalabyte_swap_kb=$((active_bytes / 1024))
done < <("${swap_tool}" --show=NAME,SIZE --bytes --noheadings 2>/dev/null || true)

other_swap_kb=$((swap_kb - active_koalabyte_swap_kb))
(( other_swap_kb >= 0 )) || other_swap_kb=0
# Size the managed file against RAM plus all *other* swap. Excluding an already
# active KoalaByte file is essential: otherwise an undersized old file is counted
# once while calculating the replacement and the helper recreates it too small.
needed_kb=$((TARGET_TOTAL_KB - mem_kb - other_swap_kb))

write_status() {
  local status="$1" reason="$2" created_mib="${3:-0}"
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${mem_kb}" "${swap_kb}" \
    "${active_koalabyte_swap_kb}" "${other_swap_kb}" "${created_mib}" \
    "${SWAPFILE}" "${SERVICE_NAME}" <<'PY'
import json, sys, time
from pathlib import Path
(path, status, reason, mem_kb, swap_kb, active_managed_kb, other_swap_kb,
 created_mib, swapfile, service) = sys.argv[1:]
Path(path).write_text(json.dumps({
    "status": status,
    "reason": reason,
    "memory_mib": round(int(mem_kb) / 1024, 1),
    "existing_swap_mib": round(int(swap_kb) / 1024, 1),
    "active_managed_swap_mib": round(int(active_managed_kb) / 1024, 1),
    "other_swap_mib": round(int(other_swap_kb) / 1024, 1),
    "created_swap_mib": int(created_mib),
    "swapfile": swapfile,
    "persistent_service": service,
    "updated_at": time.time(),
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

if [[ "${EUID}" -eq 0 ]]; then sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then sudo_cmd=(sudo)
else sudo_cmd=()
fi

install_swap_service() {
  (( ${#sudo_cmd[@]} > 0 || EUID == 0 )) || return 1
  local unit="/etc/systemd/system/${SERVICE_NAME}" temp
  temp="$(mktemp)"
  cat >"${temp}" <<EOF
[Unit]
Description=KoalaByte low-memory swap for firmware builds and local AI
After=local-fs.target
Before=ollama.service
ConditionPathExists=${SWAPFILE}

[Service]
Type=oneshot
ExecStart=/bin/sh -c '${swap_tool} --show=NAME --noheadings | ${grep_tool} -Fxq "${SWAPFILE}" || ${swap_tool} "${SWAPFILE}"'
ExecStop=/bin/sh -c '${swap_tool} --show=NAME --noheadings | ${grep_tool} -Fxq "${SWAPFILE}" && ${swapoff_tool} "${SWAPFILE}" || true'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
  "${sudo_cmd[@]}" install -m 0644 "${temp}" "${unit}"
  rm -f "${temp}"
  if command -v systemctl >/dev/null 2>&1; then
    "${sudo_cmd[@]}" systemctl daemon-reload
    "${sudo_cmd[@]}" systemctl enable "${SERVICE_NAME}" >/dev/null
  fi
}

if (( needed_kb <= 0 )); then
  [[ -f "${SWAPFILE}" ]] && install_swap_service || true
  write_status ready "RAM plus non-KoalaByte swap already meets the build target."
  echo "Build memory ready: $(((mem_kb + swap_kb) / 1024)) MiB RAM+swap"
  exit 0
fi

if command -v vcgencmd >/dev/null 2>&1; then
  raw="$(vcgencmd get_throttled 2>/dev/null || true)"
  hex="${raw#throttled=}"
  if [[ "${hex}" =~ ^0x[0-9a-fA-F]+$ ]] && (( hex & 0x10001 )); then
    write_status blocked "Under-voltage is current or has occurred since boot; refusing SD-card-intensive swap provisioning."
    echo "Under-voltage history detected (${raw}). Replace the supply/cable and reboot first." >&2
    exit 1
  fi
fi

required_mib=$(((needed_kb + 1023) / 1024))
required_mib=$((((required_mib + 255) / 256) * 256))
(( required_mib > MAX_SWAP_MIB )) && required_mib="${MAX_SWAP_MIB}"
if (( mem_kb + other_swap_kb + required_mib * 1024 < TARGET_TOTAL_KB )); then
  write_status blocked "Configured maximum managed swap cannot meet the build memory target."
  exit 1
fi
if (( ${#sudo_cmd[@]} == 0 && EUID != 0 )); then
  write_status blocked "root or sudo is required to provision build swap."
  echo "root or sudo is required to provision build swap." >&2
  exit 1
fi

# Keep an already-active managed file only when it is large enough for the current
# target. Otherwise deactivate it and recreate it at the newly calculated size.
if (( active_koalabyte_swap_kb >= required_mib * 1024 )); then
  install_swap_service
  write_status ready "Existing KoalaByte swap is large enough, active, and persistent." "$((active_koalabyte_swap_kb / 1024))"
  echo "Build memory ready: $(((mem_kb + swap_kb) / 1024)) MiB RAM+swap"
  exit 0
fi

"${sudo_cmd[@]}" install -d -m 0755 "$(dirname "${SWAPFILE}")"
if (( active_koalabyte_swap_kb > 0 )); then
  "${sudo_cmd[@]}" "${swapoff_tool}" "${SWAPFILE}"
fi
if [[ -f "${SWAPFILE}" ]]; then
  "${sudo_cmd[@]}" rm -f "${SWAPFILE}"
fi

echo "Creating ${required_mib} MiB KoalaByte swap at ${SWAPFILE}..."
if command -v fallocate >/dev/null 2>&1; then
  "${sudo_cmd[@]}" fallocate -l "${required_mib}M" "${SWAPFILE}" || \
    "${sudo_cmd[@]}" dd if=/dev/zero of="${SWAPFILE}" bs=1M count="${required_mib}" status=progress
else
  "${sudo_cmd[@]}" dd if=/dev/zero of="${SWAPFILE}" bs=1M count="${required_mib}" status=progress
fi
"${sudo_cmd[@]}" chmod 0600 "${SWAPFILE}"
"${sudo_cmd[@]}" "${mkswap_tool}" "${SWAPFILE}" >/dev/null
"${sudo_cmd[@]}" "${swap_tool}" "${SWAPFILE}"
install_swap_service

new_swap_kb="$(awk '/^SwapTotal:/ {print $2}' /proc/meminfo)"
if [[ ! "${new_swap_kb}" =~ ^[0-9]+$ ]] || (( mem_kb + new_swap_kb < TARGET_TOTAL_KB )); then
  write_status failed "Swap was created but the memory target was not reached." "${required_mib}"
  exit 1
fi
swap_kb="${new_swap_kb}"
active_koalabyte_swap_kb=$((required_mib * 1024))
write_status ready "Low-memory swap is active and enabled for future boots." "${required_mib}"
echo "Build memory ready: $(((mem_kb + swap_kb) / 1024)) MiB RAM+swap"
