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
  echo "Optional Raspberry Pi OS packages for full graphical boot splash:"
  echo "  sudo apt install -y libsdl2-2.0-0 bluetooth bluez sqlite3"
  echo
fi

echo "Creating/updating virtual environment: ${VENV_DIR}"
"${PYTHON_BIN}" -m venv "${VENV_DIR}"
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip wheel setuptools
python -m pip install -r "${REPO_ROOT}/pi-companion/requirements.txt"

echo
echo "Running Python compile check..."
python -m compileall "${REPO_ROOT}/pi-companion" "${REPO_ROOT}/scripts"

echo
echo "Pi companion install complete."
echo "Test the KoalaByte Blue boot splash windowed with:"
echo "  PYTHONPATH=${REPO_ROOT}/pi-companion ${VENV_DIR}/bin/python ${REPO_ROOT}/scripts/run_boot_splash.py --windowed --duration 3"
echo
echo "Install desktop autostart for the boot splash with:"
echo "  bash ${REPO_ROOT}/scripts/install_boot_splash_autostart.sh"
echo
echo "Run the menu validation screen with:"
echo "  PYTHONPATH=${REPO_ROOT}/pi-companion ${VENV_DIR}/bin/python ${REPO_ROOT}/scripts/run_menu_screen.py"
