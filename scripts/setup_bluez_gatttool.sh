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
KoalaByte Blue gatttool availability helper

Usage:
  bash scripts/setup_bluez_gatttool.sh
  bash scripts/setup_bluez_gatttool.sh --check-only

Env:
  INSTALL_GATTTOOL=auto|1|0
  STRICT_GATTTOOL=1
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

write_status() {
  local status="$1"
  local reason="$2"
  local found_path=""
  if command -v gatttool >/dev/null 2>&1; then
    found_path="$(command -v gatttool)"
  fi
  python3 - <<'PY' "${STATUS_PATH}" "${status}" "${reason}" "${found_path}" "${INSTALL_GATTTOOL}" "${STRICT_GATTTOOL}"
import json, sys, time
path, status, reason, found_path, install_mode, strict = sys.argv[1:]
payload = {
    "status": status,
    "reason": reason,
    "command": "gatttool",
    "path": found_path,
    "install_mode": install_mode,
    "strict": strict == "1",
    "used_by": "Gumnut GATT Gatechecker readiness artifact",
    "owned_device_required": True,
    "read_only_gatechecker": True,
    "updated_at": time.time(),
}
open(path, "w", encoding="utf-8").write(json.dumps(payload, indent=2, sort_keys=True))
PY
}

missing_ok() {
  local reason="$1"
  write_status "GATTTOOL_MISSING" "${reason}"
  if [[ "${STRICT_GATTTOOL}" == "1" ]]; then
    echo "STRICT_GATTTOOL=1 and gatttool is missing: ${reason}" >&2
    exit 1
  fi
  echo "gatttool missing, continuing in non-strict mode: ${reason}" >&2
  exit 0
}

case "${INSTALL_GATTTOOL}" in
  0|false|False|no|NO|skip|SKIP)
    write_status "GATTTOOL_SKIPPED" "disabled by INSTALL_GATTTOOL"
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES)
    ;;
  *)
    echo "Unknown INSTALL_GATTTOOL=${INSTALL_GATTTOOL}" >&2
    exit 2
    ;;
esac

if command -v gatttool >/dev/null 2>&1; then
  write_status "GATTTOOL_READY" "gatttool already present"
  cat "${STATUS_PATH}"
  exit 0
fi

if [[ "${CHECK_ONLY}" == "1" ]]; then
  bash -n "$0"
  missing_ok "check-only mode"
fi

if ! command -v apt-get >/dev/null 2>&1; then
  missing_ok "apt-get unavailable"
fi

if [[ "${EUID}" -eq 0 ]]; then
  apt_runner=(apt-get)
elif command -v sudo >/dev/null 2>&1; then
  apt_runner=(sudo apt-get)
else
  missing_ok "sudo/root unavailable"
fi

packages=()
for candidate in bluez bluez-tools bluez-test-tools bluez-obexd; do
  if apt-cache show "${candidate}" >/dev/null 2>&1; then
    packages+=("${candidate}")
  fi
done

if [[ "${#packages[@]}" -eq 0 ]]; then
  missing_ok "no BlueZ helper package candidates found"
fi

"${apt_runner[@]}" update
"${apt_runner[@]}" install -y "${packages[@]}"

if command -v gatttool >/dev/null 2>&1; then
  write_status "GATTTOOL_READY" "gatttool available after BlueZ package setup"
  cat "${STATUS_PATH}"
  exit 0
fi

missing_ok "BlueZ packages installed but gatttool was not provided by this OS image"
