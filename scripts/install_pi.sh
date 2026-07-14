#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_ROOT}/pi-companion/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CONNECT_WIFI_FIRST_BOOT="${CONNECT_WIFI_FIRST_BOOT:-auto}"
STRICT_WIFI_FIRST_BOOT="${STRICT_WIFI_FIRST_BOOT:-0}"
INSTALL_SYSTEM_PACKAGES="${INSTALL_SYSTEM_PACKAGES:-auto}"
STRICT_SYSTEM_PACKAGES="${STRICT_SYSTEM_PACKAGES:-0}"
INSTALL_GATTTOOL="${INSTALL_GATTTOOL:-auto}"
STRICT_GATTTOOL="${STRICT_GATTTOOL:-0}"
INSTALL_ESP32_TOOLS="${INSTALL_ESP32_TOOLS:-auto}"
STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS:-0}"
INSTALL_HELTEC_T114_TOOLS="${INSTALL_HELTEC_T114_TOOLS:-auto}"
STRICT_HELTEC_T114_TOOLS="${STRICT_HELTEC_T114_TOOLS:-0}"
INSTALL_HELTEC_NRF_TOOLS="${INSTALL_HELTEC_NRF_TOOLS:-1}"
INSTALL_HELTEC_V2_EXTRAS="${INSTALL_HELTEC_V2_EXTRAS:-auto}"
STRICT_HELTEC_V2_EXTRAS="${STRICT_HELTEC_V2_EXTRAS:-0}"
INSTALL_KILLERKOALA_OLLAMA="${INSTALL_KILLERKOALA_OLLAMA:-auto}"
STRICT_KILLERKOALA_OLLAMA="${STRICT_KILLERKOALA_OLLAMA:-0}"
KILLERKOALA_BASE_MODEL="${KILLERKOALA_BASE_MODEL:-tinyllama:1.1b}"
KILLERKOALA_LLM_MODEL="${KILLERKOALA_LLM_MODEL:-killerkoala-tinyllama:latest}"
FLASH_T114_ON_PLUG="${FLASH_T114_ON_PLUG:-auto}"
STRICT_T114_PLUG_FLASH="${STRICT_T114_PLUG_FLASH:-1}"
T114_PLUG_FLASH_PROFILE="${T114_PLUG_FLASH_PROFILE:-combined-safe}"
INSTALL_THATS_NOT_A_KNIFE_SERVICE="${INSTALL_THATS_NOT_A_KNIFE_SERVICE:-auto}"
STRICT_THATS_NOT_A_KNIFE_SERVICE="${STRICT_THATS_NOT_A_KNIFE_SERVICE:-0}"
INSTALL_GPIO_BUTTONS="${INSTALL_GPIO_BUTTONS:-auto}"
STRICT_GPIO_BUTTONS="${STRICT_GPIO_BUTTONS:-0}"
VENV_SYSTEM_SITE_PACKAGES="${VENV_SYSTEM_SITE_PACKAGES:-1}"
PIP_RETRIES="${PIP_RETRIES:-25}"
PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT:-300}"

cd "${REPO_ROOT}"
export PATH="${VENV_DIR}/bin:${HOME}/ncs/.venv/bin:${HOME}/.local/bin:/usr/bin:/bin:${PATH}"
export PIP_RETRIES PIP_DEFAULT_TIMEOUT

echo "KoalaByte Blue V2 Heltec Edition Pi companion installer"
echo "Repository root: ${REPO_ROOT}"
echo "Raspberry Pi OS Bookworm/Trixie compatibility enabled."

run_optional() {
  local strict="$1" label="$2"
  shift 2
  if ! "$@"; then
    if [[ "${strict}" == "1" ]]; then
      echo "${label} failed and strict mode is enabled." >&2
      exit 1
    fi
    echo "Continuing because strict mode is not enabled: ${label}" >&2
  fi
}

pip_install_retry() {
  local attempt rc=1
  for attempt in 1 2 3; do
    set +e
    python -m pip install --retries "${PIP_RETRIES}" --timeout "${PIP_DEFAULT_TIMEOUT}" --prefer-binary --no-input "$@"
    rc=$?
    set -e
    [[ ${rc} -eq 0 ]] && return 0
    echo "pip attempt ${attempt}/3 failed; retrying..." >&2
    sleep $((attempt * 10))
  done
  return "${rc}"
}

command -v "${PYTHON_BIN}" >/dev/null 2>&1 || { echo "Python 3 is required." >&2; exit 1; }

run_optional "${STRICT_WIFI_FIRST_BOOT}" "WiFi/internet setup" \
  env CONNECT_WIFI_FIRST_BOOT="${CONNECT_WIFI_FIRST_BOOT}" STRICT_WIFI_FIRST_BOOT="${STRICT_WIFI_FIRST_BOOT}" \
  bash "${REPO_ROOT}/scripts/setup_wifi_first_boot.sh"

run_optional "${STRICT_SYSTEM_PACKAGES}" "system package setup" \
  env INSTALL_SYSTEM_PACKAGES="${INSTALL_SYSTEM_PACKAGES}" STRICT_SYSTEM_PACKAGES="${STRICT_SYSTEM_PACKAGES}" \
  bash "${REPO_ROOT}/scripts/setup_system_packages.sh"

run_optional "${STRICT_GATTTOOL}" "legacy BlueZ gatttool setup" \
  env INSTALL_GATTTOOL="${INSTALL_GATTTOOL}" STRICT_GATTTOOL="${STRICT_GATTTOOL}" \
  bash "${REPO_ROOT}/scripts/setup_bluez_gatttool.sh"

echo "Creating/updating virtual environment: ${VENV_DIR}"
if [[ -f "${VENV_DIR}/pyvenv.cfg" && "${VENV_SYSTEM_SITE_PACKAGES}" == "1" ]] && ! grep -qi '^include-system-site-packages = true' "${VENV_DIR}/pyvenv.cfg"; then
  rm -rf "${VENV_DIR}"
fi
if [[ "${VENV_SYSTEM_SITE_PACKAGES}" == "1" ]]; then
  "${PYTHON_BIN}" -m venv --system-site-packages "${VENV_DIR}"
else
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"
pip_install_retry --upgrade pip wheel setuptools
pip_install_retry -r "${REPO_ROOT}/pi-companion/requirements.txt"

case "${INSTALL_HELTEC_V2_EXTRAS}" in
  0|false|False|no|NO|skip|SKIP) echo "Skipping optional Heltec v2 extras." ;;
  auto|AUTO|1|true|True|yes|YES)
    run_optional "${STRICT_HELTEC_V2_EXTRAS}" "Heltec v2 Python extras" \
      pip_install_retry -r "${REPO_ROOT}/pi-companion/requirements-heltec-v2-extra.txt"
    ;;
  *) echo "Unknown INSTALL_HELTEC_V2_EXTRAS=${INSTALL_HELTEC_V2_EXTRAS}" >&2; exit 2 ;;
esac

run_optional "${STRICT_KILLERKOALA_OLLAMA}" "KillerKoala Ollama setup" \
  env INSTALL_KILLERKOALA_OLLAMA="${INSTALL_KILLERKOALA_OLLAMA}" \
      STRICT_KILLERKOALA_OLLAMA="${STRICT_KILLERKOALA_OLLAMA}" \
      KILLERKOALA_BASE_MODEL="${KILLERKOALA_BASE_MODEL}" \
      KILLERKOALA_LLM_MODEL="${KILLERKOALA_LLM_MODEL}" \
  bash "${REPO_ROOT}/scripts/setup_killerkoala_ollama.sh"

run_optional "${STRICT_HELTEC_T114_TOOLS}" "Heltec T114 dependency setup" \
  env INSTALL_HELTEC_T114_TOOLS="${INSTALL_HELTEC_T114_TOOLS}" \
      STRICT_HELTEC_T114_TOOLS="${STRICT_HELTEC_T114_TOOLS}" \
      INSTALL_HELTEC_NRF_TOOLS="${INSTALL_HELTEC_NRF_TOOLS}" \
      PYTHON_BIN="${VENV_DIR}/bin/python" \
  bash "${REPO_ROOT}/scripts/setup_heltec_t114_tools.sh"

run_optional "${STRICT_ESP32_TOOLS}" "PlatformIO setup" \
  env STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS}" INSTALL_ESP32_TOOLS="${INSTALL_ESP32_TOOLS}" \
      PYTHON_BIN="${VENV_DIR}/bin/python" \
  bash "${REPO_ROOT}/scripts/setup_esp32_tools.sh"

echo "Running KoalaByte source compile check (virtual environments excluded)..."
python -m compileall -q "${REPO_ROOT}/pi-companion/koalablue" "${REPO_ROOT}/scripts"

echo "Running repo readiness check..."
python "${REPO_ROOT}/scripts/check_repo_readiness.py"

PYTHONPATH="${REPO_ROOT}/pi-companion" python "${REPO_ROOT}/scripts/write_optional_t114_firmware_artifacts.py"
bash "${REPO_ROOT}/scripts/configure_koalabyte_external_antennas.sh" --check-only

case "${INSTALL_GPIO_BUTTONS}" in
  0|false|False|no|NO|skip|SKIP) echo "Skipping GPIO button check." ;;
  auto|AUTO|1|true|True|yes|YES)
    run_optional "${STRICT_GPIO_BUTTONS}" "GPIO button setup" \
      env PYTHONPATH="${REPO_ROOT}/pi-companion" "${VENV_DIR}/bin/python" "${REPO_ROOT}/scripts/setup_gpio_buttons.py" --check-only
    ;;
  *) echo "Unknown INSTALL_GPIO_BUTTONS=${INSTALL_GPIO_BUTTONS}" >&2; exit 2 ;;
esac

case "${FLASH_T114_ON_PLUG}" in
  auto|AUTO|1|true|True|yes|YES)
    run_optional "${STRICT_T114_PLUG_FLASH}" "T114 plug-in firmware flash" \
      env T114_PLUG_FLASH_PROFILE="${T114_PLUG_FLASH_PROFILE}" \
      bash "${REPO_ROOT}/scripts/flash_t114_when_plugged.sh"
    ;;
  0|false|False|no|NO|skip|SKIP) echo "Skipping T114 firmware flash." ;;
  *) echo "Unknown FLASH_T114_ON_PLUG=${FLASH_T114_ON_PLUG}" >&2; exit 2 ;;
esac

case "${INSTALL_THATS_NOT_A_KNIFE_SERVICE}" in
  0|false|False|no|NO|skip|SKIP) echo "Skipping local guard service." ;;
  auto|AUTO|1|true|True|yes|YES)
    run_optional "${STRICT_THATS_NOT_A_KNIFE_SERVICE}" "local guard service install" \
      env PYTHON_BIN="${VENV_DIR}/bin/python" STRICT_THATS_NOT_A_KNIFE_SERVICE="${STRICT_THATS_NOT_A_KNIFE_SERVICE}" \
      bash "${REPO_ROOT}/scripts/install_thats_not_a_knife_service.sh"
    ;;
  *) echo "Unknown INSTALL_THATS_NOT_A_KNIFE_SERVICE=${INSTALL_THATS_NOT_A_KNIFE_SERVICE}" >&2; exit 2 ;;
esac

echo "Pi companion install complete."
echo "Python: ${VENV_DIR}/bin/python"
echo "Trixie-compatible dependency setup: scripts/setup_system_packages.sh"
echo "NCS setup: scripts/setup_nrf_connect_sdk_toolchain.sh"
