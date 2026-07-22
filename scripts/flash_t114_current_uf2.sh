#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

BUNDLE_DIR="${KOALABYTE_FIRMWARE_BUNDLE_DIR:-${ROOT}/releases/koalabyte-blue-current}"
UF2="${T114_UF2_PATH:-${BUNDLE_DIR}/t114/koalabyte-t114-current.uf2}"
UF2_VOLUME_NAME="${T114_UF2_VOLUME_NAME:-HT-n5262}"
UF2_MOUNTPOINT="${T114_UF2_MOUNTPOINT:-/mnt/koalabyte-t114-uf2}"
STATUS_PATH="${T114_FLASH_STATUS_PATH:-${ROOT}/logs/deployment/t114_flash_status.json}"
WAIT_SECONDS="${T114_FLASH_WAIT_SECONDS:-75}"
T114_SOURCE="${ROOT}/firmware/t114-combined-safe/src/main.c"
EXPECTED_FW="${T114_EXPECTED_FW:-}"
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

mkdir -p "${ROOT}/logs/deployment" "${ROOT}/logs/preflight"

resolve_expected_fw() {
  if [[ -n "${EXPECTED_FW}" ]]; then
    printf '%s\n' "${EXPECTED_FW}"
    return 0
  fi
  [[ -f "${T114_SOURCE}" ]] || return 1
  sed -n 's/^#define KOALA_FW "\([^"]*\)".*/\1/p' "${T114_SOURCE}" | head -n 1
}
EXPECTED_FW="$(resolve_expected_fw || true)"
[[ -n "${EXPECTED_FW}" ]] || {
  echo "Unable to resolve the expected T114 firmware identity from ${T114_SOURCE}." >&2
  exit 1
}

write_status() {
  local status="$1" reason="$2" mount="${3:-}" runtime_port="${4:-}" observed_fw="${5:-}"
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${UF2}" "${mount}" "${runtime_port}" "${EXPECTED_FW}" "${observed_fw}" <<'PY'
import hashlib, json, sys, time
from pathlib import Path
path, status, reason, uf2, mount, runtime_port, expected_fw, observed_fw = sys.argv[1:]
source = Path(uf2)
payload = {
    "status": status,
    "reason": reason,
    "artifact": uf2,
    "artifact_sha256": hashlib.sha256(source.read_bytes()).hexdigest() if source.exists() else "",
    "uf2_mount": mount,
    "runtime_port": runtime_port,
    "runtime_identity_required": True,
    "expected_runtime_device": "heltec-t114",
    "expected_runtime_fw": expected_fw,
    "observed_runtime_fw": observed_fw,
    "updated_at": time.time(),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

sudo_run() {
  if [[ "${EUID}" -eq 0 ]]; then "$@"; else sudo "$@"; fi
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

query_t114_status() {
  local candidate="$1" expected_fw="$2" python_runner=(python3)
  [[ -e "${candidate}" ]] || return 1
  if [[ ! -r "${candidate}" || ! -w "${candidate}" ]] && command -v sudo >/dev/null 2>&1; then
    python_runner=(sudo env "PYTHONPATH=${ROOT}/pi-companion" python3)
  fi
  PYTHONPATH=pi-companion "${python_runner[@]}" - "${candidate}" "${expected_fw}" <<'PY'
import json, sys, time
import serial
port, expected_fw = sys.argv[1:]
ser = serial.Serial()
ser.port = port
ser.baudrate = 115200
ser.timeout = 0.25
ser.write_timeout = 1.0
ser.dsrdtr = False
ser.rtscts = False
ser.dtr = False
ser.rts = False
ser.open()
try:
    time.sleep(0.25)
    deadline = time.time() + 4.0
    next_request = 0.0
    while time.time() < deadline:
        now = time.time()
        if now >= next_request:
            ser.write(b'{"type":"status"}\n')
            ser.flush()
            next_request = now + 0.8
        line = ser.readline().decode("utf-8", errors="replace").strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        observed_fw = str(payload.get("fw") or "").strip()
        if (
            payload.get("type") == "heltec_mouth_status"
            and payload.get("device") == "heltec-t114"
            and observed_fw == expected_fw
        ):
            print(json.dumps(payload, sort_keys=True))
            raise SystemExit(0)
finally:
    ser.close()
raise SystemExit(1)
PY
}

if [[ ! -f "${UF2}" ]]; then
  write_status missing_artifact "T114 UF2 artifact is missing."
  echo "Missing T114 UF2: ${UF2}" >&2
  exit 1
fi
validate_contract
if [[ "${CHECK_ONLY}" == "1" ]]; then
  write_status check_only_ready "T114 UF2, vector, bootloader, and exact runtime identity contracts validated."
  exit 0
fi

bash scripts/enter_t114_uf2_bootloader.sh
mount="$(mount_volume || true)"
if [[ -z "${mount}" || ! -d "${mount}" ]]; then
  write_status mount_failed "HT-n5262 UF2 volume could not be mounted."
  exit 1
fi

echo "Copying current T114 UF2 to ${mount}..."
cp "${UF2}" "${mount}/KOALABYTE.UF2" 2>/dev/null \
  || sudo_run cp "${UF2}" "${mount}/KOALABYTE.UF2"
sync
write_status copied "T114 UF2 copied; waiting for verified application USB." "${mount}"

deadline=$(( $(date +%s) + WAIT_SECONDS ))
verified_port=""
observed_fw=""
while (( $(date +%s) < deadline )); do
  PYTHONPATH=pi-companion python3 scripts/discover_koalabyte_ports.py --profile heltec --output-dir logs/preflight >/dev/null 2>&1 || true
  discovered=""
  if [[ -f logs/preflight/koalabyte_ports.env ]]; then
    # shellcheck disable=SC1091
    source logs/preflight/koalabyte_ports.env
    discovered="${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-${HELTEC_PORT:-}}}"
  fi
  for candidate in /dev/koalabyte-heltec /dev/koalabyte-heltec-t114 "${discovered}"; do
    [[ -n "${candidate}" && -e "${candidate}" ]] || continue
    status_json="$(query_t114_status "${candidate}" "${EXPECTED_FW}" 2>/dev/null || true)"
    if [[ -n "${status_json}" ]]; then
      verified_port="${candidate}"
      observed_fw="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read()).get("fw", ""))' <<<"${status_json}")"
      break 2
    fi
  done
  sleep 1
done

if [[ -n "${verified_port}" ]]; then
  write_status flashed "T114 UF2 accepted and exact heltec_mouth_status firmware identity verified." "${mount}" "${verified_port}" "${observed_fw}"
  echo "T114 firmware flash complete: ${EXPECTED_FW}"
  exit 0
fi

write_status flashed_unverified "UF2 was copied, but the exact T114 application identity was not verified before timeout." "${mount}"
echo "T114 UF2 copied, but runtime identity ${EXPECTED_FW} was not verified." >&2
exit 1
