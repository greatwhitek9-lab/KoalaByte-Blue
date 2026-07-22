#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

BUNDLE_DIR="${KOALABYTE_FIRMWARE_BUNDLE_DIR:-${ROOT}/releases/koalabyte-blue-current}"
MANIFEST_PATH="${BUNDLE_DIR}/manifest.json"
UF2="${T114_UF2_PATH:-${BUNDLE_DIR}/t114/koalabyte-t114-current.uf2}"
UF2_VOLUME_NAME="${T114_UF2_VOLUME_NAME:-HT-n5262}"
UF2_MOUNTPOINT="${T114_UF2_MOUNTPOINT:-/mnt/koalabyte-t114-uf2}"
STATUS_PATH="${T114_FLASH_STATUS_PATH:-${ROOT}/logs/deployment/t114_flash_status.json}"
WAIT_SECONDS="${T114_FLASH_WAIT_SECONDS:-75}"
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
python3 scripts/check_firmware_bundle.py --bundle "${BUNDLE_DIR}" --require t114 >/dev/null
mapfile -t expected_identity < <(python3 - "${MANIFEST_PATH}" <<'PY'
import json, sys
manifest = json.load(open(sys.argv[1], encoding="utf-8"))
identity = manifest["t114"]["runtime_identity"]
for key in ("device", "fw", "protocol", "repo_protocol_version"):
    value = str(identity.get(key) or "").strip()
    if not value:
        raise SystemExit(f"missing T114 runtime identity field: {key}")
    print(value)
PY
)
[[ ${#expected_identity[@]} -eq 4 ]] || { echo "Invalid T114 runtime identity in ${MANIFEST_PATH}" >&2; exit 1; }
EXPECTED_DEVICE="${expected_identity[0]}"
EXPECTED_FW="${expected_identity[1]}"
EXPECTED_PROTOCOL="${expected_identity[2]}"
EXPECTED_REPO_PROTOCOL="${expected_identity[3]}"

write_status() {
  local status="$1" reason="$2" mount="${3:-}" runtime_port="${4:-}" observed_payload="${5:-}"
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${UF2}" "${mount}" \
    "${runtime_port}" "${EXPECTED_DEVICE}" "${EXPECTED_FW}" "${EXPECTED_PROTOCOL}" \
    "${EXPECTED_REPO_PROTOCOL}" "${observed_payload}" <<'PY'
import hashlib, json, sys, time
from pathlib import Path
(path, status, reason, uf2, mount, runtime_port, expected_device, expected_fw,
 expected_protocol, expected_repo_protocol, observed_payload) = sys.argv[1:]
source = Path(uf2)
try:
    observed = json.loads(observed_payload) if observed_payload else None
except Exception:
    observed = {"raw": observed_payload}
payload = {
    "status": status,
    "reason": reason,
    "artifact": uf2,
    "artifact_sha256": hashlib.sha256(source.read_bytes()).hexdigest() if source.exists() else "",
    "uf2_mount": mount,
    "runtime_port": runtime_port,
    "runtime_identity_required": True,
    "expected_runtime_identity": {
        "device": expected_device,
        "fw": expected_fw,
        "protocol": expected_protocol,
        "repo_protocol_version": expected_repo_protocol,
    },
    "observed_runtime_identity": observed,
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
  local candidate="$1" python_runner=(python3)
  [[ -e "${candidate}" ]] || return 1
  if [[ ! -r "${candidate}" || ! -w "${candidate}" ]] && command -v sudo >/dev/null 2>&1; then
    python_runner=(sudo env "PYTHONPATH=${ROOT}/pi-companion" python3)
  fi
  PYTHONPATH=pi-companion "${python_runner[@]}" - "${candidate}" \
    "${EXPECTED_DEVICE}" "${EXPECTED_FW}" "${EXPECTED_PROTOCOL}" "${EXPECTED_REPO_PROTOCOL}" <<'PY'
import json, sys, time
import serial
port, expected_device, expected_fw, expected_protocol, expected_repo_protocol = sys.argv[1:]
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
        if (
            payload.get("type") == "heltec_mouth_status"
            and str(payload.get("device") or "") == expected_device
            and str(payload.get("fw") or "") == expected_fw
            and str(payload.get("protocol") or "") == expected_protocol
            and str(payload.get("repo_protocol_version") or "") == expected_repo_protocol
        ):
            print(json.dumps(payload, sort_keys=True))
            raise SystemExit(0)
finally:
    ser.close()
raise SystemExit(1)
PY
}

validate_contract
if [[ "${CHECK_ONLY}" == "1" ]]; then
  write_status check_only_ready \
    "T114 checksums, UF2 vector/family, bootloader path, and exact runtime firmware/protocol identity contracts validated."
  exit 0
fi

bash scripts/enter_t114_uf2_bootloader.sh
mount="$(mount_volume || true)"
if [[ -z "${mount}" || ! -d "${mount}" ]]; then
  write_status mount_failed "HT-n5262 UF2 volume could not be mounted."
  exit 1
fi

echo "Copying verified T114 UF2 to ${mount}..."
cp "${UF2}" "${mount}/KOALABYTE.UF2" 2>/dev/null \
  || sudo_run cp "${UF2}" "${mount}/KOALABYTE.UF2"
sync
write_status copied "Verified T114 UF2 copied; waiting for exact application identity." "${mount}"

deadline=$(( $(date +%s) + WAIT_SECONDS ))
verified_port=""
verified_payload=""
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
    if payload="$(query_t114_status "${candidate}")"; then
      verified_port="${candidate}"
      verified_payload="${payload}"
      break 2
    fi
  done
  sleep 1
done

if [[ -n "${verified_port}" ]]; then
  write_status flashed \
    "T114 UF2 accepted and exact firmware/protocol identity verified." \
    "${mount}" "${verified_port}" "${verified_payload}"
  echo "T114 firmware flash complete and exact identity verified: ${EXPECTED_FW}"
  exit 0
fi

write_status flashed_unverified \
  "UF2 was copied, but the exact bundled T114 firmware/protocol identity was not verified before timeout." \
  "${mount}"
echo "T114 UF2 copied, but exact runtime identity ${EXPECTED_FW}/${EXPECTED_PROTOCOL} was not verified." >&2
exit 1
