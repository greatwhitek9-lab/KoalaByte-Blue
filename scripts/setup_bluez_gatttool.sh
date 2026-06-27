#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_GATTTOOL="${INSTALL_GATTTOOL:-auto}"
STRICT_GATTTOOL="${STRICT_GATTTOOL:-0}"
STATUS_PATH="${GATTTOOL_STATUS_PATH:-${REPO_ROOT}/logs/koala_bluez/gatttool_setup_status.json}"
CHECK_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only)
      CHECK_ONLY=1
      ;;
    -h|--help)
      cat <<'EOF'
KoalaByte Blue BlueZ helper availability check

Usage:
  bash scripts/setup_bluez_gatttool.sh
  bash scripts/setup_bluez_gatttool.sh --check-only

Env:
  INSTALL_GATTTOOL=auto|1|0
  STRICT_GATTTOOL=1

Checks/records:
  bluetoothctl  required modern BlueZ control/GATT workflow tool
  btmon         required BlueZ HCI monitor/log capture helper
  gatttool      optional deprecated legacy GATT discovery helper
  btproxy       optional protected lab-only BT proxy readiness helper
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
  shift
done

mkdir -p "$(dirname "${STATUS_PATH}")"

tool_path() {
  command -v "$1" 2>/dev/null || true
}

write_status() {
  local status="$1"
  local reason="$2"
  local bluetoothctl_path="$(tool_path bluetoothctl)"
  local btmon_path="$(tool_path btmon)"
  local gatttool_path="$(tool_path gatttool)"
  local btproxy_path="$(tool_path btproxy)"
  python3 - <<'PY' "${STATUS_PATH}" "${status}" "${reason}" "${bluetoothctl_path}" "${btmon_path}" "${gatttool_path}" "${btproxy_path}" "${INSTALL_GATTTOOL}" "${STRICT_GATTTOOL}"
import json, sys, time
path, status, reason, bluetoothctl_path, btmon_path, gatttool_path, btproxy_path, install_mode, strict = sys.argv[1:]
core_ready = bool(bluetoothctl_path) and bool(btmon_path)
payload = {
    "status": status,
    "reason": reason,
    "tools": {
        "bluetoothctl": {"path": bluetoothctl_path, "available": bool(bluetoothctl_path), "required": True},
        "btmon": {"path": btmon_path, "available": bool(btmon_path), "required": True},
        "gatttool": {"path": gatttool_path, "available": bool(gatttool_path), "required": False, "deprecated": True},
        "btproxy": {"path": btproxy_path, "available": bool(btproxy_path), "required": False, "protected_menu_label": "Platypus BT-Proxy"},
    },
    "bluez_core_ready": core_ready,
    "modern_gatt_tool": "bluetoothctl",
    "legacy_gatttool_optional": True,
    "btproxy_optional": True,
    "install_mode": install_mode,
    "strict": strict == "1",
    "used_by": "Gumnut GATT Gatechecker and Platypus BT-Proxy readiness artifacts",
    "owned_device_required": True,
    "read_only_gatechecker": True,
    "updated_at": time.time(),
}
open(path, "w", encoding="utf-8").write(json.dumps(payload, indent=2, sort_keys=True))
PY
}

core_ready() {
  command -v bluetoothctl >/dev/null 2>&1 && command -v btmon >/dev/null 2>&1
}

missing_core() {
  local reason="$1"
  write_status "BLUEZ_CORE_INCOMPLETE" "${reason}"
  if [[ "${STRICT_GATTTOOL}" == "1" ]]; then
    echo "STRICT_GATTTOOL=1 and required BlueZ tools are incomplete: ${reason}" >&2
    exit 1
  fi
  echo "Required BlueZ tool setup incomplete, continuing in non-strict mode: ${reason}" >&2
  exit 0
}

case "${INSTALL_GATTTOOL}" in
  0|false|False|no|NO|skip|SKIP)
    if core_ready; then
      write_status "BLUEZ_CORE_READY" "bluetoothctl and btmon present; deprecated gatttool skipped"
      cat "${STATUS_PATH}"
      exit 0
    fi
    ;;
  auto|AUTO|1|true|True|yes|YES)
    ;;
  *)
    echo "Unknown INSTALL_GATTTOOL=${INSTALL_GATTTOOL}" >&2
    exit 2
    ;;
esac

if core_ready; then
  if command -v gatttool >/dev/null 2>&1; then
    write_status "BLUEZ_CORE_READY_WITH_GATTTOOL" "bluetoothctl and btmon present; deprecated gatttool also present"
  else
    write_status "BLUEZ_CORE_READY_GATTTOOL_SKIPPED" "bluetoothctl and btmon present; deprecated gatttool not present and not required"
  fi
  cat "${STATUS_PATH}"
  exit 0
fi

if [[ "${CHECK_ONLY}" == "1" ]]; then
  bash -n "$0"
  missing_core "check-only mode"
fi

if ! command -v apt-get >/dev/null 2>&1; then
  missing_core "apt-get unavailable"
fi

if [[ "${EUID}" -eq 0 ]]; then
  apt_runner=(apt-get)
elif command -v sudo >/dev/null 2>&1; then
  apt_runner=(sudo apt-get)
else
  missing_core "sudo/root unavailable"
fi

packages=()
for candidate in bluetooth bluez bluez-tools bluez-test-tools bluez-obexd rfkill; do
  if apt-cache show "${candidate}" >/dev/null 2>&1; then
    packages+=("${candidate}")
  fi
done

if [[ "${#packages[@]}" -eq 0 ]]; then
  missing_core "no BlueZ package candidates found"
fi

"${apt_runner[@]}" update
"${apt_runner[@]}" install -y "${packages[@]}"

if core_ready; then
  if command -v gatttool >/dev/null 2>&1; then
    write_status "BLUEZ_CORE_READY_WITH_GATTTOOL" "bluetoothctl and btmon available after BlueZ package setup; deprecated gatttool also present"
  else
    write_status "BLUEZ_CORE_READY_GATTTOOL_SKIPPED" "bluetoothctl and btmon available after BlueZ package setup; deprecated gatttool not provided by this OS image"
  fi
  cat "${STATUS_PATH}"
  exit 0
fi

missing_core "BlueZ packages installed, but bluetoothctl and/or btmon are still unavailable"
