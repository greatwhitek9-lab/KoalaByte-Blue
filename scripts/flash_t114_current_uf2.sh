#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

BUNDLE_DIR="${KOALABYTE_FIRMWARE_BUNDLE_DIR:-${ROOT}/releases/koalabyte-blue-current}"
UF2="${T114_UF2_PATH:-${BUNDLE_DIR}/t114/koalabyte-t114-current.uf2}"
UF2_VOLUME_NAME="${T114_UF2_VOLUME_NAME:-HT-n5262}"
UF2_MOUNTPOINT="${T114_UF2_MOUNTPOINT:-/mnt/koalabyte-t114-uf2}"
STATUS_PATH="${T114_FLASH_STATUS_PATH:-${ROOT}/logs/deployment/t114_flash_status.json}"
WAIT_SECONDS="${T114_FLASH_WAIT_SECONDS:-45}"
CHECK_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) CHECK_ONLY=1 ;;
    -h|--help)
      echo "Usage: bash scripts/flash_t114_current_uf2.sh [--check-only]"
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

mkdir -p "${ROOT}/logs/deployment"

write_status() {
  local status="$1" reason="$2" mount="${3:-}"
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${UF2}" "${mount}" <<'PY'
import hashlib, json, sys, time
from pathlib import Path
path, status, reason, uf2, mount = sys.argv[1:]
source = Path(uf2)
payload = {
    "status": status,
    "reason": reason,
    "artifact": uf2,
    "artifact_sha256": hashlib.sha256(source.read_bytes()).hexdigest() if source.exists() else "",
    "uf2_mount": mount,
    "updated_at": time.time(),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

sudo_run() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

find_record() {
  command -v lsblk >/dev/null 2>&1 || return 1
  python3 - "${UF2_VOLUME_NAME}" <<'PY'
import json, subprocess, sys
label = sys.argv[1].lower()
data = json.loads(subprocess.check_output(["lsblk", "-J", "-o", "LABEL,PATH,MOUNTPOINT,FSTYPE,TYPE"], text=True))
def walk(nodes):
    for node in nodes:
        if str(node.get("label") or "").lower() == label:
            print(f"{node.get('mountpoint') or ''}\t{node.get('path') or ''}")
            return True
        if walk(node.get("children") or []):
            return True
    return False
raise SystemExit(0 if walk(data.get("blockdevices") or []) else 1)
PY
}

mount_volume() {
  local record mount device
  record="$(find_record || true)"
  [[ -n "${record}" ]] || return 1
  mount="${record%%$'\t'*}"
  device="${record#*$'\t'}"
  if [[ -n "${mount}" && -d "${mount}" ]]; then
    printf '%s\n' "${mount}"
    return 0
  fi
  [[ -n "${device}" && -e "${device}" ]] || return 1
  sudo_run mkdir -p "${UF2_MOUNTPOINT}"
  sudo_run mount -o "uid=$(id -u),gid=$(id -g)" "${device}" "${UF2_MOUNTPOINT}" \
    || sudo_run mount "${device}" "${UF2_MOUNTPOINT}"
  printf '%s\n' "${UF2_MOUNTPOINT}"
}

validate_contract() {
  bash -n scripts/flash_t114_current_uf2.sh
  bash -n scripts/enter_t114_uf2_bootloader.sh
  python3 scripts/inspect_uf2.py "${UF2}" >/dev/null
  python3 scripts/verify_uf2_vector.py "${UF2}" \
    --vector-address 0x26000 \
    --application-min 0x26000 \
    --application-max 0xec000 \
    --family 0x239a0071 >/dev/null
}

if [[ ! -f "${UF2}" ]]; then
  write_status "missing_artifact" "T114 UF2 artifact is missing."
  echo "Missing T114 UF2: ${UF2}" >&2
  exit 1
fi
validate_contract
if [[ "${CHECK_ONLY}" == "1" ]]; then
  write_status "check_only_ready" "T114 UF2 and flash contract validated."
  exit 0
fi

bash scripts/enter_t114_uf2_bootloader.sh
mount="$(mount_volume || true)"
if [[ -z "${mount}" || ! -d "${mount}" ]]; then
  write_status "mount_failed" "HT-n5262 UF2 volume could not be mounted."
  exit 1
fi

echo "Copying current T114 UF2 to ${mount}..."
cp "${UF2}" "${mount}/KOALABYTE.UF2" 2>/dev/null \
  || sudo_run cp "${UF2}" "${mount}/KOALABYTE.UF2"
sync
write_status "copied" "T114 UF2 copied; waiting for application USB to return." "${mount}"

# The bootloader normally unmounts after accepting the UF2. Wait for the runtime
# CDC alias or a ttyACM endpoint to return before allowing Pi services to start.
deadline=$(( $(date +%s) + WAIT_SECONDS ))
while (( $(date +%s) < deadline )); do
  if [[ -e /dev/koalabyte-heltec || -e /dev/koalabyte-heltec-t114 ]]; then
    write_status "flashed" "T114 UF2 accepted and runtime USB alias returned." "${mount}"
    echo "T114 firmware flash complete."
    exit 0
  fi
  sleep 1
done

write_status "flashed_unverified" "UF2 was copied, but the stable runtime alias did not return before timeout." "${mount}"
echo "T114 UF2 copied, but runtime re-enumeration was not verified." >&2
exit 1
