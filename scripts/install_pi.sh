#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${REPO_ROOT}/pi-companion/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CONNECT_WIFI_FIRST_BOOT="${CONNECT_WIFI_FIRST_BOOT:-auto}"
STRICT_WIFI_FIRST_BOOT="${STRICT_WIFI_FIRST_BOOT:-0}"
INSTALL_SYSTEM_PACKAGES="${INSTALL_SYSTEM_PACKAGES:-auto}"
STRICT_SYSTEM_PACKAGES="${STRICT_SYSTEM_PACKAGES:-0}"
INSTALL_ESP32_TOOLS="${INSTALL_ESP32_TOOLS:-auto}"
STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS:-0}"
INSTALL_HELTEC_T114_TOOLS="${INSTALL_HELTEC_T114_TOOLS:-auto}"
STRICT_HELTEC_T114_TOOLS="${STRICT_HELTEC_T114_TOOLS:-0}"
INSTALL_HELTEC_NRF_TOOLS="${INSTALL_HELTEC_NRF_TOOLS:-auto}"
INSTALL_HELTEC_V2_EXTRAS="${INSTALL_HELTEC_V2_EXTRAS:-auto}"
STRICT_HELTEC_V2_EXTRAS="${STRICT_HELTEC_V2_EXTRAS:-0}"
FLASH_T114_ON_PLUG="${FLASH_T114_ON_PLUG:-auto}"
STRICT_T114_PLUG_FLASH="${STRICT_T114_PLUG_FLASH:-1}"
T114_PLUG_FLASH_PROFILE="${T114_PLUG_FLASH_PROFILE:-color-mouth}"
PREPARE_DONGLE_CACHE="${PREPARE_DONGLE_CACHE:-0}"
STRICT_DONGLE_CACHE="${STRICT_DONGLE_CACHE:-0}"
INSTALL_NRF_TOOLS="${INSTALL_NRF_TOOLS:-auto}"
INSTALL_NCS_TOOLCHAIN="${INSTALL_NCS_TOOLCHAIN:-auto}"
STRICT_NCS_TOOLCHAIN="${STRICT_NCS_TOOLCHAIN:-${STRICT_DONGLE_CACHE}}"
INSTALL_THATS_NOT_A_KNIFE_SERVICE="${INSTALL_THATS_NOT_A_KNIFE_SERVICE:-auto}"
STRICT_THATS_NOT_A_KNIFE_SERVICE="${STRICT_THATS_NOT_A_KNIFE_SERVICE:-0}"
VENV_SYSTEM_SITE_PACKAGES="${VENV_SYSTEM_SITE_PACKAGES:-1}"

cd "${REPO_ROOT}"

echo "KoalaByte Blue V2 Heltec Edition Pi companion installer"
echo "Repository root: ${REPO_ROOT}"
echo "System dependency helper covers WiFi, BlueZ, Heltec T114 USB serial/udev, SDL2, can-utils, iproute2, USB, build, and GPIO packages when apt is available."
echo

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python 3 is required but was not found." >&2
  exit 1
fi

echo "Checking first-boot WiFi/internet before downloads..."
CONNECT_WIFI_FIRST_BOOT="${CONNECT_WIFI_FIRST_BOOT}" STRICT_WIFI_FIRST_BOOT="${STRICT_WIFI_FIRST_BOOT}" bash "${REPO_ROOT}/scripts/setup_wifi_first_boot.sh" || {
  if [[ "${STRICT_WIFI_FIRST_BOOT}" == "1" ]]; then
    echo "STRICT_WIFI_FIRST_BOOT=1 is set, failing install because WiFi/internet setup did not complete." >&2
    exit 1
  fi
  echo "Continuing install because STRICT_WIFI_FIRST_BOOT is not enabled." >&2
}

echo "Checking/installing Raspberry Pi system packages..."
INSTALL_SYSTEM_PACKAGES="${INSTALL_SYSTEM_PACKAGES}" STRICT_SYSTEM_PACKAGES="${STRICT_SYSTEM_PACKAGES}" bash "${REPO_ROOT}/scripts/setup_system_packages.sh" || {
  if [[ "${STRICT_SYSTEM_PACKAGES}" == "1" ]]; then
    echo "STRICT_SYSTEM_PACKAGES=1 is set, failing install because system package setup did not complete." >&2
    exit 1
  fi
  echo "Continuing install because STRICT_SYSTEM_PACKAGES is not enabled." >&2
}

echo "Creating/updating virtual environment: ${VENV_DIR}"
if [[ -f "${VENV_DIR}/pyvenv.cfg" && "${VENV_SYSTEM_SITE_PACKAGES}" == "1" ]] && ! grep -qi '^include-system-site-packages = true' "${VENV_DIR}/pyvenv.cfg"; then
  echo "Existing venv was not created with system site packages; recreating it so Pi GPIO apt packages are visible."
  rm -rf "${VENV_DIR}"
fi
if [[ "${VENV_SYSTEM_SITE_PACKAGES}" == "1" ]]; then
  "${PYTHON_BIN}" -m venv --system-site-packages "${VENV_DIR}"
else
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip wheel setuptools
python -m pip install -r "${REPO_ROOT}/pi-companion/requirements.txt"

case "${INSTALL_HELTEC_V2_EXTRAS}" in
  0|false|False|no|NO|skip|SKIP)
    echo "Skipping optional Heltec v2 extra Python requirements."
    ;;
  auto|AUTO|1|true|True|yes|YES)
    echo "Installing/checking optional Heltec v2 extra Python requirements..."
    python -m pip install -r "${REPO_ROOT}/pi-companion/requirements-heltec-v2-extra.txt" || {
      if [[ "${STRICT_HELTEC_V2_EXTRAS}" == "1" ]]; then
        echo "STRICT_HELTEC_V2_EXTRAS=1 is set, failing install because optional Heltec v2 extras did not install." >&2
        exit 1
      fi
      echo "Continuing install because STRICT_HELTEC_V2_EXTRAS is not enabled." >&2
    }
    ;;
  *)
    echo "Unknown INSTALL_HELTEC_V2_EXTRAS value: ${INSTALL_HELTEC_V2_EXTRAS}. Use auto, 1, or 0." >&2
    exit 1
    ;;
esac

echo
echo "Checking/preparing Heltec T114 runtime dependencies and port discovery..."
INSTALL_HELTEC_T114_TOOLS="${INSTALL_HELTEC_T114_TOOLS}" \
STRICT_HELTEC_T114_TOOLS="${STRICT_HELTEC_T114_TOOLS}" \
INSTALL_HELTEC_NRF_TOOLS="${INSTALL_HELTEC_NRF_TOOLS}" \
PYTHON_BIN="${VENV_DIR}/bin/python" \
  bash "${REPO_ROOT}/scripts/setup_heltec_t114_tools.sh" || {
    if [[ "${STRICT_HELTEC_T114_TOOLS}" == "1" ]]; then
      echo "STRICT_HELTEC_T114_TOOLS=1 is set, failing install because Heltec T114 setup did not complete." >&2
      exit 1
    fi
    echo "Continuing install because STRICT_HELTEC_T114_TOOLS is not enabled." >&2
  }

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
echo "Generating default T114 HCI USB, color-mouth, GNSS, face-state, and passive BLE protocol artifacts..."
PYTHONPATH="${REPO_ROOT}/pi-companion" python "${REPO_ROOT}/scripts/write_optional_t114_firmware_artifacts.py"

echo
echo "Generating KoalaByte external antenna readiness artifacts..."
bash "${REPO_ROOT}/scripts/configure_koalabyte_external_antennas.sh" --check-only

echo
echo "T114 plug-in flash policy: FLASH_T114_ON_PLUG=${FLASH_T114_ON_PLUG}, T114_PLUG_FLASH_PROFILE=${T114_PLUG_FLASH_PROFILE}"
case "${FLASH_T114_ON_PLUG}" in
  auto|AUTO|1|true|True|yes|YES)
    T114_PLUG_FLASH_PROFILE="${T114_PLUG_FLASH_PROFILE}" bash "${REPO_ROOT}/scripts/flash_t114_when_plugged.sh" || {
      if [[ "${STRICT_T114_PLUG_FLASH}" == "1" ]]; then
        echo "STRICT_T114_PLUG_FLASH=1 is set, failing install because T114 plug-in flash did not complete." >&2
        exit 1
      fi
      echo "Continuing install because STRICT_T114_PLUG_FLASH is not enabled." >&2
    }
    ;;
  0|false|False|no|NO|skip|SKIP)
    echo "Skipping T114 plug-in firmware flash by request."
    ;;
  *)
    echo "Unknown FLASH_T114_ON_PLUG value: ${FLASH_T114_ON_PLUG}. Use auto, 1, or 0." >&2
    exit 1
    ;;
esac

echo
echo "Legacy external nRF52840 Dongle cache policy: PREPARE_DONGLE_CACHE=${PREPARE_DONGLE_CACHE}, STRICT_DONGLE_CACHE=${STRICT_DONGLE_CACHE}"
case "${PREPARE_DONGLE_CACHE}" in
  0|false|False|no|NO|skip|SKIP)
    echo "Skipping legacy external dongle firmware cache preparation. Heltec T114 is the default primary BLE board."
    ;;
  auto|AUTO|1|true|True|yes|YES)
    echo "Preparing legacy external dongle cache because PREPARE_DONGLE_CACHE requested it."
    STRICT_NRF_TOOLS="${STRICT_DONGLE_CACHE}" INSTALL_NRF_TOOLS="${INSTALL_NRF_TOOLS}" PYTHON_BIN="${VENV_DIR}/bin/python" bash "${REPO_ROOT}/scripts/setup_nrf_tools.sh" || {
      if [[ "${STRICT_DONGLE_CACHE}" == "1" ]]; then
        echo "STRICT_DONGLE_CACHE=1 is set, failing install because west/nrfutil setup did not complete." >&2
        exit 1
      fi
      echo "Continuing install because STRICT_DONGLE_CACHE is not enabled." >&2
    }
    INSTALL_NCS_TOOLCHAIN="${INSTALL_NCS_TOOLCHAIN}" STRICT_NCS_TOOLCHAIN="${STRICT_NCS_TOOLCHAIN}" PYTHON_BIN="${VENV_DIR}/bin/python" bash "${REPO_ROOT}/scripts/setup_nrf_connect_sdk_toolchain.sh" || {
      if [[ "${STRICT_NCS_TOOLCHAIN}" == "1" ]]; then
        echo "STRICT_NCS_TOOLCHAIN=1 is set, failing install because full NCS/Zephyr toolchain setup did not complete." >&2
        exit 1
      fi
      echo "Continuing install because STRICT_NCS_TOOLCHAIN is not enabled." >&2
    }
    if command -v west >/dev/null 2>&1 && command -v nrfutil >/dev/null 2>&1; then
      PYTHON_BIN="${VENV_DIR}/bin/python" PYTHONPATH="${REPO_ROOT}/pi-companion" bash "${REPO_ROOT}/scripts/prepare_dongle_firmware_cache.sh"
    else
      echo "west and/or nrfutil not found, so legacy dongle DFU ZIPs cannot be prepared automatically." >&2
      if [[ "${STRICT_DONGLE_CACHE}" == "1" ]]; then
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
echo "Installing/enabling that's not a knife local guard service: INSTALL_THATS_NOT_A_KNIFE_SERVICE=${INSTALL_THATS_NOT_A_KNIFE_SERVICE}"
case "${INSTALL_THATS_NOT_A_KNIFE_SERVICE}" in
  0|false|False|no|NO|skip|SKIP)
    echo "Skipping that's not a knife service install by request."
    ;;
  auto|AUTO|1|true|True|yes|YES)
    PYTHON_BIN="${VENV_DIR}/bin/python" STRICT_THATS_NOT_A_KNIFE_SERVICE="${STRICT_THATS_NOT_A_KNIFE_SERVICE}" bash "${REPO_ROOT}/scripts/install_thats_not_a_knife_service.sh" || {
      if [[ "${STRICT_THATS_NOT_A_KNIFE_SERVICE}" == "1" ]]; then
        echo "STRICT_THATS_NOT_A_KNIFE_SERVICE=1 is set, failing install because the local guard service did not install." >&2
        exit 1
      fi
      echo "Continuing install because STRICT_THATS_NOT_A_KNIFE_SERVICE is not enabled." >&2
    }
    ;;
  *)
    echo "Unknown INSTALL_THATS_NOT_A_KNIFE_SERVICE value: ${INSTALL_THATS_NOT_A_KNIFE_SERVICE}. Use auto, 1, or 0." >&2
    exit 1
    ;;
esac

echo
echo "Pi companion install complete."
echo "WiFi first-boot helper:"
echo "  WIFI_INTERACTIVE=1 bash ${REPO_ROOT}/scripts/setup_wifi_first_boot.sh"
echo "System dependency helper:"
echo "  bash ${REPO_ROOT}/scripts/setup_system_packages.sh"
echo "Heltec T114 dependency helper:"
echo "  bash ${REPO_ROOT}/scripts/setup_heltec_t114_tools.sh"
echo "  INSTALL_HELTEC_NRF_TOOLS=1 bash ${REPO_ROOT}/scripts/setup_heltec_t114_tools.sh"
echo "Optional Heltec v2 extra Python requirements:"
echo "  python -m pip install -r ${REPO_ROOT}/pi-companion/requirements-heltec-v2-extra.txt"
echo "External antenna readiness:"
echo "  bash ${REPO_ROOT}/scripts/configure_koalabyte_external_antennas.sh --check-only"
echo "T114 plug-in firmware flash:"
echo "  T114_PLUG_FLASH_PROFILE=color-mouth bash ${REPO_ROOT}/scripts/flash_t114_when_plugged.sh"
echo "  T114_PLUG_FLASH_PROFILE=hci-usb bash ${REPO_ROOT}/scripts/flash_t114_when_plugged.sh"
echo "Optional T114 protocol artifact manifest:"
echo "  python3 ${REPO_ROOT}/scripts/write_optional_t114_firmware_artifacts.py"
echo "  bash ${REPO_ROOT}/scripts/configure_t114_2g4_antenna.sh --check-only"
echo "ESP32 PlatformIO helper:"
echo "  bash ${REPO_ROOT}/scripts/setup_esp32_tools.sh"
echo
echo "Heltec primary BLE node check:"
echo "  python3 ${REPO_ROOT}/scripts/discover_koalabyte_ports.py --profile heltec"
echo "  cat ${REPO_ROOT}/logs/preflight/koalabyte_ports.env"
echo "  KOALABYTE_PRIMARY_BLE_PORT=/dev/koalabyte-heltec PYTHONPATH=${REPO_ROOT}/pi-companion ${VENV_DIR}/bin/python ${REPO_ROOT}/scripts/run_ble_node_manager.py --duration 30"
echo
echo "Koala Kan Kommander InnoMaker manifest test:"
echo "  PYTHONPATH=${REPO_ROOT}/pi-companion ${VENV_DIR}/bin/python ${REPO_ROOT}/scripts/run_koala_kan_kommander.py manifest"
echo
echo "that's not a knife local guard service:"
echo "  bash ${REPO_ROOT}/scripts/install_thats_not_a_knife_service.sh"
echo "  systemctl status koalabyte-thats-not-a-knife.service"
echo "  journalctl -u koalabyte-thats-not-a-knife.service -f"
echo
echo "Normal boot wrapper with boot splash and menu:"
echo "  bash ${REPO_ROOT}/scripts/koalabyte_blue_boot.sh"
