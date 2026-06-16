#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_ROOT}/pi-companion/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PREPARE_DONGLE_CACHE="${PREPARE_DONGLE_CACHE:-auto}"
STRICT_DONGLE_CACHE="${STRICT_DONGLE_CACHE:-0}"

cd "${REPO_ROOT}"

echo "KoalaByte Blue Pi companion installer"
echo "Repository root: ${REPO_ROOT}"
echo

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python 3 is required but was not found." >&2
  exit 1
fi

if command -v apt-get >/dev/null 2>&1; then
  echo "Recommended Raspberry Pi OS packages for graphical UI, Outback BlueZ, optional InnoMaker SocketCAN checks, and dongle mode flashing:"
  echo "  sudo apt update"
  echo "  sudo apt install -y libsdl2-2.0-0 bluetooth bluez rfkill sqlite3 iproute2 can-utils"
  echo "Optional BlueZ helpers may be present on some images: btmgmt btmon hciconfig hcitool sdptool rfcomm l2ping gatttool busctl"
  echo "Install Nordic nrfutil and nRF Connect SDK/west if you want install_pi.sh to build and cache both nRF52840 Dongle DFU ZIPs during install."
  echo
fi

echo "Creating/updating virtual environment: ${VENV_DIR}"
"${PYTHON_BIN}" -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip wheel setuptools
python -m pip install -r "${REPO_ROOT}/pi-companion/requirements.txt"

echo
echo "Running Python compile check..."
python -m compileall "${REPO_ROOT}/pi-companion" "${REPO_ROOT}/scripts"

echo
echo "Running repo readiness check..."
python "${REPO_ROOT}/scripts/check_repo_readiness.py"

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
      echo "Install nRF Connect SDK/west and Nordic nrfutil, then run:" >&2
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
