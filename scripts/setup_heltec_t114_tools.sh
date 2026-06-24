#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON_BIN:-${ROOT}/pi-companion/.venv/bin/python}"
INSTALL_HELTEC_T114_TOOLS="${INSTALL_HELTEC_T114_TOOLS:-auto}"
STRICT_HELTEC_T114_TOOLS="${STRICT_HELTEC_T114_TOOLS:-0}"
INSTALL_HELTEC_NRF_TOOLS="${INSTALL_HELTEC_NRF_TOOLS:-auto}"
CHECK_ONLY=0

usage() {
  cat <<'EOF'
KoalaByte Blue V2 Heltec Edition T114 dependency setup helper

Usage:
  bash scripts/setup_heltec_t114_tools.sh
  STRICT_HELTEC_T114_TOOLS=1 bash scripts/setup_heltec_t114_tools.sh
  INSTALL_HELTEC_NRF_TOOLS=1 bash scripts/setup_heltec_t114_tools.sh
  bash scripts/setup_heltec_t114_tools.sh --check-only

Environment:
  PYTHON_BIN                  Python interpreter to use. Defaults to pi-companion/.venv/bin/python, then python3.
  INSTALL_HELTEC_T114_TOOLS   auto/1/0. Default: auto. Installs/checks runtime helpers when possible.
  STRICT_HELTEC_T114_TOOLS    1 fails when required Heltec runtime dependencies are missing.
  INSTALL_HELTEC_NRF_TOOLS    auto/1/0. Default: auto. Checks west/nrfutil support for future T114 firmware work; set 1 to actively prepare tools.

Covers:
  - pyserial and bleak Python runtime dependencies
  - USB/udev/BlueZ command availability checks
  - KoalaByte stable udev aliases, especially /dev/koalabyte-heltec
  - Heltec-priority port discovery and preflight env output
  - optional west/nrfutil/NCS checks for future Heltec T114 nRF52840 firmware targets
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only)
      CHECK_ONLY=1
      INSTALL_HELTEC_T114_TOOLS=0
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

cd "${ROOT}"
mkdir -p "${ROOT}/logs/preflight"

if [[ ! -x "${PY}" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PY="$(command -v python3)"
  else
    echo "No Python 3 interpreter found for Heltec T114 setup." >&2
    [[ "${STRICT_HELTEC_T114_TOOLS}" == "1" ]] && exit 1
    exit 0
  fi
fi

echo "== Heltec Mesh Node T114 dependency setup/check =="
echo "Python: ${PY}"
echo "INSTALL_HELTEC_T114_TOOLS=${INSTALL_HELTEC_T114_TOOLS} STRICT_HELTEC_T114_TOOLS=${STRICT_HELTEC_T114_TOOLS} INSTALL_HELTEC_NRF_TOOLS=${INSTALL_HELTEC_NRF_TOOLS}"

missing=()
for cmd in lsusb udevadm bluetoothctl rfkill; do
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    missing+=("${cmd}")
  fi
done

if [[ "${#missing[@]}" -gt 0 ]]; then
  echo "Missing optional/required Heltec runtime commands: ${missing[*]}" >&2
  echo "Run scripts/setup_system_packages.sh on Raspberry Pi OS to install USB, udev, and BlueZ packages." >&2
fi

if [[ "${CHECK_ONLY}" != "1" && "${INSTALL_HELTEC_T114_TOOLS}" != "0" ]]; then
  echo "Installing/checking Python runtime packages for Heltec serial/BLE node support..."
  "${PY}" -m pip install --upgrade pyserial bleak >/dev/null || {
    echo "Could not install/upgrade pyserial and bleak with ${PY}." >&2
    [[ "${STRICT_HELTEC_T114_TOOLS}" == "1" ]] && exit 1
  }
fi

"${PY}" - <<'PY' || {
import importlib.util
missing = [name for name in ("serial", "bleak") if importlib.util.find_spec(name) is None]
if missing:
    raise SystemExit("missing Python modules: " + ", ".join(missing))
print("Python modules OK: pyserial, bleak")
PY
  [[ "${STRICT_HELTEC_T114_TOOLS}" == "1" ]] && exit 1
}

if [[ "${CHECK_ONLY}" != "1" && "${INSTALL_HELTEC_T114_TOOLS}" != "0" ]]; then
  echo "Installing/checking KoalaByte udev rules for Heltec T114 stable paths..."
  INSTALL_UDEV_RULES="${INSTALL_UDEV_RULES:-auto}" STRICT_UDEV_RULES="${STRICT_UDEV_RULES:-0}" bash "${ROOT}/scripts/install_koalabyte_udev_rules.sh" || {
    echo "Heltec udev alias setup did not complete." >&2
    [[ "${STRICT_HELTEC_T114_TOOLS}" == "1" ]] && exit 1
  }
fi

echo "Running Heltec-priority port discovery..."
"${PY}" "${ROOT}/scripts/discover_koalabyte_ports.py" --profile heltec --output-dir "${ROOT}/logs/preflight" || {
  echo "Heltec port discovery failed." >&2
  [[ "${STRICT_HELTEC_T114_TOOLS}" == "1" ]] && exit 1
}

if [[ -f "${ROOT}/logs/preflight/koalabyte_ports.env" ]]; then
  echo "Heltec port env written: ${ROOT}/logs/preflight/koalabyte_ports.env"
fi

case "${INSTALL_HELTEC_NRF_TOOLS}" in
  0|false|False|no|NO|skip|SKIP)
    echo "Skipping optional west/nrfutil/NCS checks for Heltec T114 firmware work."
    ;;
  auto|AUTO)
    echo "Checking optional west/nrfutil availability for future Heltec T114 nRF52840 firmware work..."
    if command -v west >/dev/null 2>&1; then
      echo "  west: $(command -v west)"
    else
      echo "  west not found. Set INSTALL_HELTEC_NRF_TOOLS=1 to prepare nRF/Zephyr tooling." >&2
    fi
    if command -v nrfutil >/dev/null 2>&1; then
      echo "  nrfutil: $(command -v nrfutil)"
    else
      echo "  nrfutil not found. Set INSTALL_HELTEC_NRF_TOOLS=1 to prepare nRF/Zephyr tooling." >&2
    fi
    ;;
  1|true|True|yes|YES)
    echo "Preparing west/nrfutil and nRF Connect SDK tooling for future Heltec T114 firmware work..."
    STRICT_NRF_TOOLS="${STRICT_HELTEC_T114_TOOLS}" INSTALL_NRF_TOOLS="${INSTALL_NRF_TOOLS:-auto}" PYTHON_BIN="${PY}" bash "${ROOT}/scripts/setup_nrf_tools.sh"
    INSTALL_NCS_TOOLCHAIN="${INSTALL_NCS_TOOLCHAIN:-auto}" STRICT_NCS_TOOLCHAIN="${STRICT_HELTEC_T114_TOOLS}" PYTHON_BIN="${PY}" bash "${ROOT}/scripts/setup_nrf_connect_sdk_toolchain.sh"
    ;;
  *)
    echo "Unknown INSTALL_HELTEC_NRF_TOOLS value: ${INSTALL_HELTEC_NRF_TOOLS}" >&2
    exit 2
    ;;
esac

if [[ "${#missing[@]}" -gt 0 && "${STRICT_HELTEC_T114_TOOLS}" == "1" ]]; then
  exit 1
fi

echo "Heltec T114 dependency setup/check complete."
