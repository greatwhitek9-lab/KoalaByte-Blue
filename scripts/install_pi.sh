#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_ROOT}/pi-companion/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

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
  echo "Install Nordic nrfutil separately if you want this Pi to flash the nRF52840 Dongle from cached DFU ZIPs."
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
echo "Pi companion install complete."
echo "Prepare offline nRF52840 Dongle firmware cache on this Pi:"
echo "  bash ${REPO_ROOT}/scripts/prepare_dongle_firmware_cache.sh"
echo "  PYTHONPATH=${REPO_ROOT}/pi-companion ${VENV_DIR}/bin/python ${REPO_ROOT}/scripts/run_koala_mode_switcher.py cache-status"
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
