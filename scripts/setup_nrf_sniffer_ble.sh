#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_NRF_SNIFFER="${INSTALL_NRF_SNIFFER:-auto}"
STRICT_NRF_SNIFFER="${STRICT_NRF_SNIFFER:-0}"
NRF_SNIFFER_ZIP="${NRF_SNIFFER_ZIP:-}"
NRF_SNIFFER_DIR="${NRF_SNIFFER_DIR:-}"
NRF_SNIFFER_URL="${NRF_SNIFFER_URL:-}"
NRF_SNIFFER_CACHE_DIR="${NRF_SNIFFER_CACHE_DIR:-${REPO_ROOT}/vendor/nordic/nrf-sniffer-ble}"
NRF_SNIFFER_EXTCAP_DIR="${NRF_SNIFFER_EXTCAP_DIR:-${HOME}/.local/lib/wireshark/extcap}"
NRF_SNIFFER_INSTALL_DEPS="${NRF_SNIFFER_INSTALL_DEPS:-auto}"
CHECK_ONLY=0

usage() {
  cat <<'EOF'
KoalaByte Blue Nordic nRF Sniffer for Bluetooth LE setup helper

Usage:
  bash scripts/setup_nrf_sniffer_ble.sh
  NRF_SNIFFER_ZIP=/path/to/nrf_sniffer_for_bluetooth_le.zip bash scripts/setup_nrf_sniffer_ble.sh
  NRF_SNIFFER_DIR=/path/to/extracted/nrf_sniffer bash scripts/setup_nrf_sniffer_ble.sh
  NRF_SNIFFER_URL=<authorized_download_url> bash scripts/setup_nrf_sniffer_ble.sh
  STRICT_NRF_SNIFFER=1 NRF_SNIFFER_ZIP=/path/to/zip bash scripts/setup_nrf_sniffer_ble.sh
  bash scripts/setup_nrf_sniffer_ble.sh --check-only

Environment:
  NRF_SNIFFER_ZIP          Path to the Nordic nRF Sniffer for Bluetooth LE ZIP downloaded from Nordic.
  NRF_SNIFFER_DIR          Path to an already extracted Nordic nRF Sniffer package.
  NRF_SNIFFER_URL          Optional authorized URL to a Nordic sniffer ZIP. Not set by default.
  NRF_SNIFFER_EXTCAP_DIR   Wireshark extcap install directory. Default: ~/.local/lib/wireshark/extcap
  INSTALL_NRF_SNIFFER      auto/1/0. Default: auto. If package is available, install extcap pieces.
  STRICT_NRF_SNIFFER       1 fails if the proprietary package is missing or install fails. Default: 0.
  PYTHON_BIN               Python executable used for optional Python dependency installs.

Important:
  Nordic's nRF Sniffer for Bluetooth LE package is proprietary. This repo does not redistribute it.
  Download it from Nordic under its license, then provide NRF_SNIFFER_ZIP or NRF_SNIFFER_DIR.

This helper installs the Wireshark/extcap host side. It does not automatically flash sniffer firmware
onto the Heltec T114 because that would replace the current selected T114 personality.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only)
      CHECK_ONLY=1
      INSTALL_NRF_SNIFFER=0
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
mkdir -p logs vendor/nordic

install_enabled() {
  case "${INSTALL_NRF_SNIFFER}" in
    1|true|True|yes|YES|auto|AUTO) return 0 ;;
    *) return 1 ;;
  esac
}

strict_enabled() {
  [[ "${STRICT_NRF_SNIFFER}" == "1" ]]
}

install_dep_enabled() {
  case "${NRF_SNIFFER_INSTALL_DEPS}" in
    1|true|True|yes|YES|auto|AUTO) return 0 ;;
    *) return 1 ;;
  esac
}

have_tool() {
  command -v "$1" >/dev/null 2>&1
}

json_escape() {
  python3 - <<'PY' "$1"
import json, sys
print(json.dumps(sys.argv[1]))
PY
}

write_status() {
  local status="$1"
  local reason="$2"
  local source_path="$3"
  local extcap_dir="$4"
  local installed="$5"
  cat > "${REPO_ROOT}/logs/nrf_sniffer_ble_status.json" <<JSON
{
  "status": $(json_escape "${status}"),
  "installed": ${installed},
  "reason": $(json_escape "${reason}"),
  "source_path": $(json_escape "${source_path}"),
  "extcap_dir": $(json_escape "${extcap_dir}"),
  "wireshark_available": $(have_tool wireshark && echo true || echo false),
  "tshark_available": $(have_tool tshark && echo true || echo false),
  "python": $(json_escape "${PYTHON_BIN}"),
  "strict_nrf_sniffer": $(json_escape "${STRICT_NRF_SNIFFER}"),
  "updated_at": $(date +%s)
}
JSON
}

find_extcap_source() {
  local root="$1"
  local found=""
  found="$(find "${root}" -type f \( -name 'nrf_sniffer_ble.py' -o -name 'nrf_sniffer_ble.sh' -o -name '*nrf*sniffer*ble*.py' \) -print -quit 2>/dev/null || true)"
  if [[ -n "${found}" ]]; then
    dirname "${found}"
    return 0
  fi
  found="$(find "${root}" -type d -iname 'extcap' -print -quit 2>/dev/null || true)"
  if [[ -n "${found}" ]]; then
    echo "${found}"
    return 0
  fi
  return 1
}

prepare_source_dir() {
  if [[ -n "${NRF_SNIFFER_DIR}" ]]; then
    [[ -d "${NRF_SNIFFER_DIR}" ]] && echo "${NRF_SNIFFER_DIR}" && return 0
    echo "NRF_SNIFFER_DIR does not exist: ${NRF_SNIFFER_DIR}" >&2
    return 1
  fi
  if [[ -z "${NRF_SNIFFER_ZIP}" && -n "${NRF_SNIFFER_URL}" && "${CHECK_ONLY}" != "1" && install_enabled ]]; then
    mkdir -p "${NRF_SNIFFER_CACHE_DIR}"
    NRF_SNIFFER_ZIP="${NRF_SNIFFER_CACHE_DIR}/nrf_sniffer_for_bluetooth_le.zip"
    echo "Downloading Nordic nRF Sniffer package from NRF_SNIFFER_URL..." >&2
    if have_tool curl; then
      curl -L --fail --output "${NRF_SNIFFER_ZIP}" "${NRF_SNIFFER_URL}"
    elif have_tool wget; then
      wget -O "${NRF_SNIFFER_ZIP}" "${NRF_SNIFFER_URL}"
    else
      echo "curl/wget not found for NRF_SNIFFER_URL download." >&2
      return 1
    fi
  fi
  if [[ -n "${NRF_SNIFFER_ZIP}" ]]; then
    [[ -f "${NRF_SNIFFER_ZIP}" ]] || { echo "NRF_SNIFFER_ZIP does not exist: ${NRF_SNIFFER_ZIP}" >&2; return 1; }
    mkdir -p "${NRF_SNIFFER_CACHE_DIR}/extracted"
    rm -rf "${NRF_SNIFFER_CACHE_DIR}/extracted"/*
    if have_tool unzip; then
      unzip -q "${NRF_SNIFFER_ZIP}" -d "${NRF_SNIFFER_CACHE_DIR}/extracted"
    else
      "${PYTHON_BIN}" - <<PY
import zipfile
from pathlib import Path
zipfile.ZipFile(${NRF_SNIFFER_ZIP@Q}).extractall(Path(${NRF_SNIFFER_CACHE_DIR@Q}) / 'extracted')
PY
    fi
    echo "${NRF_SNIFFER_CACHE_DIR}/extracted"
    return 0
  fi
  return 1
}

install_python_deps() {
  if install_dep_enabled; then
    "${PYTHON_BIN}" -m pip install --user --upgrade pyserial packaging || true
  fi
}

install_extcap() {
  local source_root="$1"
  local extcap_source
  extcap_source="$(find_extcap_source "${source_root}")" || return 1
  mkdir -p "${NRF_SNIFFER_EXTCAP_DIR}"
  echo "Installing nRF Sniffer extcap files from ${extcap_source} to ${NRF_SNIFFER_EXTCAP_DIR}" >&2
  cp -R "${extcap_source}/"* "${NRF_SNIFFER_EXTCAP_DIR}/"
  find "${NRF_SNIFFER_EXTCAP_DIR}" -maxdepth 2 -type f \( -name '*.py' -o -name '*.sh' \) -exec chmod +x {} \; 2>/dev/null || true
  mkdir -p "${REPO_ROOT}/vendor/nordic/nrf-sniffer-ble/firmware"
  find "${source_root}" -type f \( -name '*.hex' -o -name '*.uf2' -o -name '*.zip' \) -path '*firmware*' -exec cp {} "${REPO_ROOT}/vendor/nordic/nrf-sniffer-ble/firmware/" \; 2>/dev/null || true
  echo "${extcap_source}"
}

echo "== Nordic nRF Sniffer for Bluetooth LE setup =="
echo "This installs the Wireshark/extcap host side from a locally provided Nordic package."
echo "Repository root: ${REPO_ROOT}"
echo "Extcap dir: ${NRF_SNIFFER_EXTCAP_DIR}"

if [[ "${CHECK_ONLY}" == "1" ]]; then
  if [[ -d "${NRF_SNIFFER_EXTCAP_DIR}" ]] && find "${NRF_SNIFFER_EXTCAP_DIR}" -type f -iname '*sniffer*' -print -quit | grep -q .; then
    write_status "present" "nRF Sniffer-like extcap file found" "${NRF_SNIFFER_EXTCAP_DIR}" "${NRF_SNIFFER_EXTCAP_DIR}" true
    exit 0
  fi
  write_status "missing" "check-only: no nRF Sniffer extcap file found" "" "${NRF_SNIFFER_EXTCAP_DIR}" false
  exit 0
fi

if ! install_enabled; then
  write_status "skipped" "INSTALL_NRF_SNIFFER=${INSTALL_NRF_SNIFFER}" "" "${NRF_SNIFFER_EXTCAP_DIR}" false
  echo "nRF Sniffer install skipped by INSTALL_NRF_SNIFFER=${INSTALL_NRF_SNIFFER}."
  exit 0
fi

if ! have_tool tshark && ! have_tool wireshark; then
  echo "Wireshark/tshark not found yet. setup_system_packages.sh should install tshark/wireshark-common before this helper." >&2
fi

if ! source_root="$(prepare_source_dir)"; then
  reason="Nordic proprietary package not provided. Set NRF_SNIFFER_ZIP, NRF_SNIFFER_DIR, or NRF_SNIFFER_URL."
  write_status "needs_package" "${reason}" "" "${NRF_SNIFFER_EXTCAP_DIR}" false
  echo "${reason}" >&2
  strict_enabled && exit 1
  exit 0
fi

install_python_deps
if ! extcap_source="$(install_extcap "${source_root}")"; then
  reason="Could not find Nordic nRF Sniffer extcap files in provided package."
  write_status "error" "${reason}" "${source_root}" "${NRF_SNIFFER_EXTCAP_DIR}" false
  echo "${reason}" >&2
  strict_enabled && exit 1
  exit 0
fi

write_status "installed" "nRF Sniffer BLE extcap installed from provided Nordic package" "${extcap_source}" "${NRF_SNIFFER_EXTCAP_DIR}" true

echo "nRF Sniffer BLE host-side setup complete."
echo "Open Wireshark and check the extcap interface list, or run: tshark -D"
echo "Note: flashing sniffer firmware is a separate, intentional action because it replaces the current selected nRF52840 profile."
