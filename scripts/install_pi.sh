#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_ROOT}/pi-companion/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PREPARE_DONGLE_CACHE="${PREPARE_DONGLE_CACHE:-auto}"
STRICT_DONGLE_CACHE="${STRICT_DONGLE_CACHE:-0}"
INSTALL_NRF_TOOLS="${INSTALL_NRF_TOOLS:-auto}"
INSTALL_SYSTEM_PACKAGES="${INSTALL_SYSTEM_PACKAGES:-auto}"
STRICT_SYSTEM_PACKAGES="${STRICT_SYSTEM_PACKAGES:-0}"
INSTALL_ESP32_TOOLS="${INSTALL_ESP32_TOOLS:-auto}"
STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS:-0}"

cd "${REPO_ROOT}"

echo "KoalaByte Blue Pi companion installer"
echo "Repository root: ${REPO_ROOT}"
echo "System dependency helper covers BlueZ, SDL2, can-utils, iproute2, USB, build, and GPIO packages when apt is available."
echo

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python 3 is required but was not found." >&2
  exit 1
fi

echo "Checking/installing Raspberry Pi system packages..."
INSTALL_SYSTEM_PACKAGES="${INSTALL_SYSTEM_PACKAGES}" STRICT_SYSTEM_PACKAGES="${STRICT_SYSTEM_PACKAGES}" bash "${REPO_ROOT}/scripts/setup_system_packages.sh" || {
  if [[ "${STRICT_SYSTEM_PACKAGES}" == "1" ]]; then
    echo "STRICT_SYSTEM_PACKAGES=1 is set, failing install because system package setup did not complete." >&2
    exit 1
  fi
  echo "Continuing install because STRICT_SYSTEM_PACKAGES is not enabled." >&2
}

echo "Creating/updating virtual environment: ${VENV_DIR}"
"${PYTHON_BIN}" -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip wheel setuptools
python -m pip install -r "${REPO_ROOT}/pi-companion/requirements.txt"

echo
echo "Checking/preparing ESP32 PlatformIO tools..."
STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS}" INSTALL_ESP32_TOOLS="${INSTALL_ESP32_TOOLS}" PYTHON_BIN="${VENV_DIR}/bin/python" bash "${REPO_ROOT}/scripts/setup_esp32_tools.sh" || {
  if [[ "${STRICT_ESP32_TOOLS}" == "1" ]]; then
    echo "STRICT_ESP32_TOOLS=1 is set, failing install because PlatformIO setup did not complete." >&2
    exit 1
  fi
  echo "Continuing install because STRICT_ESP32_TOOLS is not enabled." >&2
}

echo
echo "Running Python compile check..."
python -m compileall "${REPO_ROOT}/pi-companion" "${REPO_ROOT}/scripts"

echo
echo "Running repo readiness check..."
python "${REPO_ROOT}/scripts/check_repo_readiness.py"

echo
echo "Checking/preparing west and nrfutil for nRF52840 flashing..."
STRICT_NRF_TOOLS="${STRICT_DONGLE_CACHE}" INSTALL_NRF_TOOLS="${INSTALL_NRF_TOOLS}" PYTHON_BIN="${VENV_DIR}/bin/python" bash "${REPO_ROOT}/scripts/setup_nrf_tools.sh" || {
  if [[ "${STRICT_DONGLE_CACHE}" == "1" ]]; then
    echo "STRICT_DONGLE_CACHE=1 is set, failing install because west/nrfutil setup did not complete." >&2
    exit 1
  fi
  echo "Continuing install because STRICT_DONGLE_CACHE is not enabled." >&2
}

echo
echo "Preparing offline nRF52840 Dongle firmware cache policy: PREPARE_DONGLE_CACHE=${PREPARE_DONGLE_CACHE}, STRICT_DONGLE_CACHE=${STRICT_DONGLE_CACHE}"
case "${PREPARE_DONGLE_CACHE}" in
  0|false|False|no|NO|skip|SKIP)
    echo "Skipping dongle firmware cache preparation by request."
    PYTHONPATH="${REPO_ROOT}/pi-companion" python "${REPO_ROOT}/scripts/run_koala_mode_switcher.py" cache-status || true
    ;;
  auto|AUTO|1|true|True|yes|YES)
    if command -v west >/dev/null 2>&1 && command -v nrfutil >/dev/null 2>&1; then
      echo "west and nrfutil detected. Building and caching both dongle DFU ZIPs now."
      PYTHON_BIN="${VENV_DIR}/bin/python" PYTHONPATH="${REPO_ROOT}/pi-companion" bash "${REPO_ROOT}/scripts/prepare_dongle_firmware_cache.sh"
    else
      echo "west and/or nrfutil not found, so both DFU ZIPs cannot be prepared automatically on this install run." >&2
      echo "Run the setup helper and cache helper after installing tools:" >&2
      echo "  bash ${REPO_ROOT}/scripts/setup_nrf_tools.sh" >&2
      echo "  bash ${REPO_ROOT}/scripts/prepare_dongle_firmware_cache.sh" >&2
      PYTHONPATH="${REPO_ROOT}/pi-companion" python "${REPO_ROOT}/scripts/run_koala_mode_switcher.py" cache-status || true
      if [[ "${STRICT_DONGLE_CACHE}" == "1" ]]; then
        echo "STRICT_DONGLE_CACHE=1 is set, failing install because firmware cache was not prepared." >&2
        exit 1
      fi
    fi
    ;;
  *)
    echo "Unknown PREPARE_DONGLE_CACHE value: ${PREPARE_DONGLE_CACHE}. Use auto, 1, or 0." >&2
    exit 1
    ;;
esac

echo
echo "Pi companion install complete."
echo "System dependency helper:"
echo "  bash ${REPO_ROOT}/scripts/setup_system_packages.sh"
echo "ESP32 PlatformIO helper:"
echo "  bash ${REPO_ROOT}/scripts/setup_esp32_tools.sh"
echo "west/nrfutil setup helper:"
echo "  bash ${REPO_ROOT}/scripts/setup_nrf_tools.sh"
echo "Offline nRF52840 Dongle firmware cache:"
echo "  bash ${REPO_ROOT}/scripts/prepare_dongle_firmware_cache.sh"
echo "  PYTHONPATH=${REPO_ROOT}/pi-companion ${VENV_DIR}/bin/python ${REPO_ROOT}/scripts/run_koala_mode_switcher.py cache-status"
echo "  cache file: ${REPO_ROOT}/logs/dongle_firmware_cache.json"
echo
echo "Pre-boot dongle mode selector:"
echo "  PYTHONPATH=${REPO_ROOT}/pi-companion ${VENV_DIR}/bin/python ${REPO_ROOT}/scripts/run_preboot_mode_select.py"
echo "  NRF_DFU_PORT=/dev/ttyACM0 PYTHONPATH=${REPO_ROOT}/pi-companion ${VENV_DIR}/bin/python ${REPO_ROOT}/scripts/run_preboot_mode_select.py --mode koala_konnect"
echo
echo "Normal boot wrapper with pre-boot selector, boot splash, and menu:"
echo "  bash ${REPO_ROOT}/scripts/koalabyte_blue_boot.sh"
echo
echo "Boot splash test:"
echo "  PYTHONPATH=${REPO_ROOT}/pi-companion ${VENV_DIR}/bin/python ${REPO_ROOT}/scripts/run_boot_splash.py --windowed --duration 3"
echo
echo "Jungle/eucalyptus graphical menu test:"
echo "  PYTHONPATH=${REPO_ROOT}/pi-companion ${VENV_DIR}/bin/python ${REPO_ROOT}/scripts/run_menu_screen.py --graphical --windowed"
echo
echo "Outback BlueZ module manifest test:"
echo "  PYTHONPATH=${REPO_ROOT}/pi-companion ${VENV_DIR}/bin/python ${REPO_ROOT}/scripts/run_koala_bluez.py manifest"
echo
echo "Gumleaf Gear Check inventory test:"
echo "  PYTHONPATH=${REPO_ROOT}/pi-companion ${VENV_DIR}/bin/python ${REPO_ROOT}/scripts/run_koala_bluez.py inventory"
echo
echo "Koala Kan Kommander InnoMaker manifest test:"
echo "  PYTHONPATH=${REPO_ROOT}/pi-companion ${VENV_DIR}/bin/python ${REPO_ROOT}/scripts/run_koala_kan_kommander.py manifest"
echo
echo "killerkoala voice preview:"
echo "  PYTHONPATH=${REPO_ROOT}/pi-companion ${VENV_DIR}/bin/python ${REPO_ROOT}/scripts/run_killerkoala_voice.py status --xp 100"
echo
echo "All-component helper:"
echo "  bash ${REPO_ROOT}/scripts/flash_all_components.sh --all"
echo
echo "Terminal menu validation:"
echo "  PYTHONPATH=${REPO_ROOT}/pi-companion ${VENV_DIR}/bin/python ${REPO_ROOT}/scripts/run_menu_screen.py"
