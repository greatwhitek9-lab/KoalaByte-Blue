#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${KOALABYTE_FIRMWARE_MANIFEST:-${REPO_ROOT}/firmware/prebuilt/manifest.json}"
STATUS_PATH="${KOALABYTE_T114_PREBUILT_FLASH_STATUS:-${REPO_ROOT}/logs/one_shot/t114_prebuilt_flash_status.json}"
STATE_PATH="${KOALABYTE_PERIPHERAL_STATE_PATH:-${REPO_ROOT}/logs/one_shot/peripheral_firmware_state.json}"
UF2_VOLUME_NAME="${T114_UF2_VOLUME_NAME:-HT-n5262}"
UF2_MOUNTPOINT="${T114_UF2_MOUNTPOINT:-/mnt/koalabyte-t114-uf2}"
FLASH_MODE="${FLASH_T114_ON_PLUG:-auto}"
FORCE="${FORCE_T114_FLASH:-0}"
STRICT="${STRICT_T114_PLUG_FLASH:-0}"

mkdir -p "$(dirname "${STATUS_PATH}")" "$(dirname "${STATE_PATH}")"

write_status() {
  local status="$1" reason="$2" mount="${3:-}" image="${4:-}" expected="${5:-}"
  python3 - <<'PY' "${STATUS_PATH}" "${status}" "${reason}" "${mount}" "${image}" "${expected}" "${FLASH_MODE}"
import json, sys, time
from pathlib import Path
path, status, reason, mount, image, expected, mode = sys.argv[1:]
payload = {
    "status": status,
    "reason": reason,
    "uf2_mount": mount,
    "image": image,
    "expected_sha256": expected,
    "flash_mode": mode,
    "target": "heltec-t114-ht-n5262",
    "windows_auto_eject_note": "0x80070022/ERROR_WRONG_DISK can appear after a successful UF2 copy because the bootloader volume ejects itself",
    "updated_at": time.time(),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(payload, sort_keys=True))
PY
}

case "${FLASH_MODE}" in
  0|false|False|no|NO|skip|SKIP)
    write_status "T114_FLASH_SKIPPED" "Disabled by FLASH_T114_ON_PLUG configuration."
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES) ;;
  *) echo "Unsupported FLASH_T114_ON_PLUG=${FLASH_MODE}; use auto, 1, or 0." >&2; exit 2 ;;
esac

if [[ ! -f "${MANIFEST}" ]]; then
  write_status "T114_MANIFEST_MISSING" "Prebuilt firmware manifest is missing."
  [[ "${STRICT}" == "1" ]] && exit 1 || exit 0
fi

readarray -t meta < <(python3 - <<'PY' "${MANIFEST}"
import json, sys
entry = json.load(open(sys.argv[1], encoding="utf-8"))["heltec_t114"]
print(entry.get("file", ""))
print(entry.get("sha256", ""))
PY
)
relative="${meta[0]:-}"
expected="${meta[1]:-}"
image="${REPO_ROOT}/${relative}"

if [[ ! -f "${image}" ]]; then
  write_status "T114_PREBUILT_NOT_INCLUDED" "Source checkout does not contain the release UF2; no T114 flash attempted." "" "${image}" "${expected}"
  [[ "${STRICT}" == "1" && ( "${FLASH_MODE}" == "1" || "${FLASH_MODE}" == "true" ) ]] && exit 1 || exit 0
fi
actual="$(sha256sum "${image}" | awk '{print $1}')"
if [[ -z "${expected}" || "${actual}" != "${expected}" ]]; then
  write_status "T114_HASH_MISMATCH" "Refusing to copy a UF2 that does not match the manifest." "" "${image}" "${expected}"
  exit 1
fi

find_mount() {
  if [[ -n "${T114_UF2_MOUNT:-}" && -d "${T114_UF2_MOUNT}" ]]; then
    printf '%s\n' "${T114_UF2_MOUNT}"
    return 0
  fi
  local user_name="${SUDO_USER:-${USER:-}}"
  local candidates=()
  [[ -n "${user_name}" ]] && candidates+=("/media/${user_name}/${UF2_VOLUME_NAME}" "/run/media/${user_name}/${UF2_VOLUME_NAME}")
  candidates+=("/media/${UF2_VOLUME_NAME}" "/mnt/${UF2_VOLUME_NAME}" "/Volumes/${UF2_VOLUME_NAME}" "${UF2_MOUNTPOINT}")
  candidates+=(/media/*/"${UF2_VOLUME_NAME}" /run/media/*/"${UF2_VOLUME_NAME}")
  for candidate in "${candidates[@]}"; do
    [[ -d "${candidate}" ]] && { printf '%s\n' "${candidate}"; return 0; }
  done
  if command -v lsblk >/dev/null 2>&1; then
    local device
    device="$(lsblk -rno LABEL,PATH | awk -v label="${UF2_VOLUME_NAME}" '$1 == label {print $2; exit}')"
    if [[ -n "${device}" && -b "${device}" ]]; then
      if [[ "${EUID}" -eq 0 ]]; then
        mkdir -p "${UF2_MOUNTPOINT}"; mount "${device}" "${UF2_MOUNTPOINT}" || true
      elif command -v sudo >/dev/null 2>&1; then
        sudo mkdir -p "${UF2_MOUNTPOINT}"; sudo mount -o "uid=$(id -u),gid=$(id -g)" "${device}" "${UF2_MOUNTPOINT}" || sudo mount "${device}" "${UF2_MOUNTPOINT}" || true
      fi
      [[ -d "${UF2_MOUNTPOINT}" ]] && { printf '%s\n' "${UF2_MOUNTPOINT}"; return 0; }
    fi
  fi
  return 1
}

mount="$(find_mount || true)"
if [[ -z "${mount}" ]]; then
  write_status "T114_BOOTLOADER_NOT_PRESENT" "Latest UF2 is bundled and verified. T114 was not reflashed because the HT-n5262 bootloader volume is not mounted; normal USB serial is not treated as flash permission." "" "${image}" "${expected}"
  [[ "${STRICT}" == "1" && ( "${FLASH_MODE}" == "1" || "${FLASH_MODE}" == "true" ) ]] && exit 1 || exit 0
fi

previous="$(python3 - <<'PY' "${STATE_PATH}"
import json, sys
try:
    print(json.load(open(sys.argv[1], encoding="utf-8")).get("heltec_t114", {}).get("sha256", ""))
except Exception:
    print("")
PY
)"
if [[ "${FORCE}" != "1" && "${previous}" == "${expected}" ]]; then
  write_status "T114_ALREADY_CURRENT" "Recorded peripheral state already matches bundled UF2; no reflash performed." "${mount}" "${image}" "${expected}"
  exit 0
fi

cp "${image}" "${mount}/"
sync || true
python3 - <<'PY' "${STATE_PATH}" "${expected}" "${image}"
import json, sys, time
from pathlib import Path
path, sha, image = sys.argv[1:]
try:
    payload = json.load(open(path, encoding="utf-8"))
except Exception:
    payload = {}
payload["heltec_t114"] = {"sha256": sha, "image": image, "flashed_at": time.time()}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
PY
write_status "T114_UF2_COPIED" "UF2 copy completed. The bootloader should eject and reboot automatically; a host wrong-disk/eject message after disappearance is not by itself a failure." "${mount}" "${image}" "${expected}"
