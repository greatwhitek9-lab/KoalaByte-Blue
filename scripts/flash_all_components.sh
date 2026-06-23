#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"
ORIGINAL_ARGS=("$@")

CANONICAL_HELTEC_BRANCH="${KOALABYTE_HELTEC_BRANCH:-koalabyte_blue_v2_heltec_edition}"
RUN_PI=0
RUN_ESP32=0
RUN_HELTEC_T114=0
RUN_T114_PROFILE_PREP=0
RUN_BLE_NODE_MANAGER=0
RUN_NRF_KONNECT=0
RUN_CAN_CHECK=0
RUN_AI_VOICE=0
RUN_GREATWHITE_SUPPORT=0
BUILD_ONLY=0
CHECK_ONLY=0
RUN_SMOKE=0
NO_MONITOR_DEFAULT=1
CHECKOUT_HELTEC=0
PREFLIGHT_BUILD=0
ONE_SCRIPT_INSTALL=0

usage() {
  cat <<EOF
KoalaByte Blue all-component flash/install helper - Heltec T114 Edition

Usage:
  bash scripts/flash_all_components.sh --install-firmware
  bash scripts/flash_all_components.sh --all
  bash scripts/flash_all_components.sh --prepare-t114-profiles
  bash scripts/flash_all_components.sh --pi --esp32 --heltec-t114
  bash scripts/flash_all_components.sh --ble-node-manager
  bash scripts/flash_all_components.sh --ai-voice
  bash scripts/flash_all_components.sh --can-check
  bash scripts/flash_all_components.sh --greatwhite
  bash scripts/flash_all_components.sh --nrf-konnect
  ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32
  KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --heltec-t114
  T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_all_components.sh --nrf-konnect

Targets:
  --install-firmware       One-script Heltec Edition install: checkout ${CANONICAL_HELTEC_BRANCH}, readiness check, dependency setup, Pi companion, ESP32 DualEye, both T114 profile build checks, normal Heltec T114 profile, BLE node manager service, Greatwhite/tshark support, CAN setup/checks, and CAN manifest/status checks
  --all                    Install Pi companion, prepare KillerKoala AI voice, flash ESP32 DualEye, prepare both Heltec T114 profiles, flash normal Heltec T114 mouth/GNSS/BLE firmware, install/start BLE node manager service, prepare Greatwhite/tshark support, set up/check can0, and run Koala Kan checks
  --prepare-t114-profiles  Build/check both Heltec T114 profiles: Lab/mouth/BLE/GNSS and Koala Konnect T114
  --pi                     Install/update Raspberry Pi companion environment
  --ai-voice               Prepare/verify KillerKoala phrase-first companion config and optional TinyLlama/Ollama settings
  --esp32                  Build and flash ESP32-S3 DualEye firmware with PlatformIO
  --heltec-t114            Build and flash Heltec Mesh Node T114 v2 nRF52840 mouth/GNSS/BLE firmware over USB-C
  --ble-node-manager       Install/enable/start the Pi-side BLE node manager service with Heltec T114 as primary BLE node
  --greatwhite             Install/check Greatwhite Wireshark/tshark support and nRF Sniffer host-side status
  --nrf-konnect            Build/apply the optional Heltec T114 Koala Konnect USB-HCI profile
  --can-check              Load Linux CAN modules, optionally bring up can0, then run Koala Kan Kommander manifest/inventory/status checks

Modes:
  --build-only             Build/package/check only; do not upload/apply firmware, install services, or configure can0
  --preflight-build        Run the all-firmware build helper before selected targets
  --checkout-heltec        Compatibility alias: checkout the canonical Heltec Edition branch before continuing
  --check-only             Run repo readiness check only
  --smoke                  After selected actions, run safe local Pi companion smoke checks
  --monitor                Open ESP32/Heltec serial monitor after flash where supported
  -h, --help               Show this help

Environment:
  KOALABYTE_HELTEC_BRANCH       Canonical Heltec Edition branch. Default: koalabyte_blue_v2_heltec_edition
  ESP32_PORT                    Optional PlatformIO upload/monitor port, for example /dev/ttyUSB0 or COM5
  HELTEC_PORT                   Optional Heltec T114 USB CDC upload/monitor port, for example /dev/ttyACM0 or COM7
  KOALABYTE_HELTEC_USB_PORT     Optional Pi runtime USB CDC port for T114 face/GNSS/BLE JSON bridge
  KOALABYTE_ESP32_FACE_PORT     Optional ESP32 runtime serial port for eyes and optional secondary BLE node
  T114_BOARD                    Zephyr board target for Koala Konnect T114. Recommended: heltec_t114_v2/nrf52840
  T114_FLASH_METHOD             west or uf2 for Koala Konnect T114. Default: west
  T114_STARTUP_SELECTOR         1 enables startup choice in scripts/koalabyte_blue_boot.sh. Default: 1
  T114_STARTUP_DEFAULT_MODE     lab or konnect. Default: lab
  T114_STARTUP_MODE             Optional non-interactive startup mode: lab or konnect
  T114_STARTUP_NO_APPLY         1 records startup selection without applying a T114 profile
  CAN_INTERFACE                 SocketCAN interface for Koala Kan Kommander. Default: can0
  CAN_BITRATE                   CAN bitrate for setup_can0.sh. Default: 500000
  STRICT_CAN_SETUP              1 fails if can0 setup cannot complete. Default: 0
  INSTALL_SYSTEM_PACKAGES       auto/1/0. Default: auto. Attempts apt install on Raspberry Pi OS
  STRICT_SYSTEM_PACKAGES        1 fails if system packages cannot be checked/installed
  STRICT_ESP32_TOOLS            1 fails if PlatformIO is unavailable before ESP32/Heltec build/flash
  STRICT_NRF_TOOLS              1 fails if west tooling is unavailable before Koala Konnect T114 build/check
  STRICT_NCS_TOOLCHAIN          1 fails if the full NCS/Zephyr toolchain cannot be prepared
  STRICT_GREATWHITE_SUPPORT     1 fails if Greatwhite/tshark support status generation fails. Default: 0

Startup profile selection:
  --install-firmware prepares both Heltec T114 profiles, but the T114 onboard nRF52840 can run only one profile at a time.
  At startup, scripts/koalabyte_blue_boot.sh runs scripts/select_t114_startup_mode.py so the operator can choose Lab or Koala Konnect T114.
EOF
}

if [[ $# -eq 0 ]]; then
  usage
  exit 0
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-firmware)
      ONE_SCRIPT_INSTALL=1
      CHECKOUT_HELTEC=1
      PREFLIGHT_BUILD=1
      RUN_PI=1
      RUN_AI_VOICE=1
      RUN_ESP32=1
      RUN_T114_PROFILE_PREP=1
      RUN_HELTEC_T114=1
      RUN_BLE_NODE_MANAGER=1
      RUN_GREATWHITE_SUPPORT=1
      RUN_CAN_CHECK=1
      ;;
    --all)
      RUN_PI=1
      RUN_AI_VOICE=1
      RUN_ESP32=1
      RUN_T114_PROFILE_PREP=1
      RUN_HELTEC_T114=1
      RUN_BLE_NODE_MANAGER=1
      RUN_GREATWHITE_SUPPORT=1
      RUN_CAN_CHECK=1
      ;;
    --prepare-t114-profiles) RUN_T114_PROFILE_PREP=1 ;;
    --pi) RUN_PI=1 ;;
    --ai-voice) RUN_PI=1; RUN_AI_VOICE=1 ;;
    --esp32) RUN_ESP32=1 ;;
    --heltec-t114) RUN_HELTEC_T114=1 ;;
    --ble-node-manager) RUN_PI=1; RUN_BLE_NODE_MANAGER=1 ;;
    --greatwhite) RUN_GREATWHITE_SUPPORT=1 ;;
    --nrf-konnect) RUN_NRF_KONNECT=1 ;;
    --can-check) RUN_CAN_CHECK=1 ;;
    --build-only) BUILD_ONLY=1 ;;
    --preflight-build) PREFLIGHT_BUILD=1 ;;
    --checkout-heltec) CHECKOUT_HELTEC=1 ;;
    --check-only) CHECK_ONLY=1 ;;
    --smoke) RUN_SMOKE=1 ;;
    --monitor) NO_MONITOR_DEFAULT=0 ;;
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

if [[ "${ONE_SCRIPT_INSTALL}" == "1" ]]; then
  export HELTEC_PORT="${HELTEC_PORT:-/dev/ttyACM0}"
  export KOALABYTE_HELTEC_USB_PORT="${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT}}"
fi

checkout_heltec_if_requested() {
  if [[ "${CHECKOUT_HELTEC}" != "1" ]]; then
    return 0
  fi
  if ! command -v git >/dev/null 2>&1; then
    echo "git is required for --checkout-heltec / --install-firmware." >&2
    exit 1
  fi
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Not inside a git checkout; cannot switch to ${CANONICAL_HELTEC_BRANCH}." >&2
    exit 1
  fi
  local current_branch
  current_branch="$(git rev-parse --abbrev-ref HEAD)"
  if [[ "${current_branch}" == "${CANONICAL_HELTEC_BRANCH}" ]]; then
    echo "Already on ${CANONICAL_HELTEC_BRANCH}."
    return 0
  fi
  echo "Checking out canonical Heltec Edition branch: ${CANONICAL_HELTEC_BRANCH}"
  git fetch origin "${CANONICAL_HELTEC_BRANCH}" || true
  git checkout "${CANONICAL_HELTEC_BRANCH}"
  if [[ "${KOALABYTE_FLASH_ALL_REEXECED:-0}" != "1" ]]; then
    echo "Re-running flash helper from the canonical Heltec Edition branch copy..."
    exec env KOALABYTE_FLASH_ALL_REEXECED=1 bash scripts/flash_all_components.sh "${ORIGINAL_ARGS[@]}"
  fi
}

any_selected_for_network_or_packages() {
  [[ "${RUN_PI}" == "1" || "${RUN_AI_VOICE}" == "1" || "${RUN_ESP32}" == "1" || "${RUN_HELTEC_T114}" == "1" || "${RUN_T114_PROFILE_PREP}" == "1" || "${RUN_BLE_NODE_MANAGER}" == "1" || "${RUN_GREATWHITE_SUPPORT}" == "1" || "${RUN_NRF_KONNECT}" == "1" || "${RUN_CAN_CHECK}" == "1" ]]
}

setup_wifi_for_selected_mode() {
  if ! any_selected_for_network_or_packages; then
    return 0
  fi
  echo
  echo "== First-startup WiFi/internet setup =="
  CONNECT_WIFI_FIRST_BOOT="${CONNECT_WIFI_FIRST_BOOT:-auto}" STRICT_WIFI_FIRST_BOOT="${STRICT_WIFI_FIRST_BOOT:-0}" bash scripts/setup_wifi_first_boot.sh
}

setup_system_packages_for_selected_mode() {
  if ! any_selected_for_network_or_packages; then
    return 0
  fi
  echo
  echo "== Raspberry Pi/system package dependency setup, including CAN, python-can, Greatwhite/tshark, and AI voice/TTS packages =="
  STRICT_SYSTEM_PACKAGES="${STRICT_SYSTEM_PACKAGES:-0}" bash scripts/setup_system_packages.sh
}

setup_platformio_for_selected_mode() {
  if [[ "${RUN_ESP32}" != "1" && "${RUN_HELTEC_T114}" != "1" && "${RUN_T114_PROFILE_PREP}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== PlatformIO setup for ESP32-S3 DualEye and Heltec T114 workflows =="
  STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS:-1}" bash scripts/setup_esp32_tools.sh
}

setup_nrf_tools_for_selected_mode() {
  if [[ "${RUN_NRF_KONNECT}" != "1" && "${RUN_T114_PROFILE_PREP}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== west/NCS setup for Heltec T114 Koala Konnect build/checks =="
  STRICT_NRF_TOOLS="${STRICT_NRF_TOOLS:-1}" bash scripts/setup_nrf_tools.sh --west-only
  echo
  echo "== Full nRF Connect SDK / Zephyr toolchain setup =="
  STRICT_NCS_TOOLCHAIN="${STRICT_NCS_TOOLCHAIN:-${STRICT_NRF_TOOLS:-1}}" INSTALL_NCS_TOOLCHAIN="${INSTALL_NCS_TOOLCHAIN:-auto}" bash scripts/setup_nrf_connect_sdk_toolchain.sh
}

prepare_t114_profiles_for_selected_mode() {
  if [[ "${RUN_T114_PROFILE_PREP}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== Preparing both Heltec T114 firmware profiles for startup selection =="
  T114_BOARD="${T114_BOARD:-heltec_t114_v2/nrf52840}" bash scripts/prepare_t114_firmware_profiles.sh
}

setup_killerkoala_ai_voice_for_selected_mode() {
  if [[ "${RUN_AI_VOICE}" != "1" && "${RUN_SMOKE}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== KillerKoala AI voice companion setup =="
  mkdir -p logs/killerkoala
  cat > logs/killerkoala/flash_all_ai_voice_config.json <<JSON
{
  "mode": "${KILLERKOALA_LLM_MODE:-fast_default}",
  "model": "${KILLERKOALA_LLM_MODEL:-killerkoala-tinyllama:latest}",
  "timeout_seconds": "${KILLERKOALA_LLM_TIMEOUT_SECONDS:-2.5}",
  "fast_default": "pi-companion/koalblue/killerkoala_vocabulary.py",
  "hybrid_companion": "pi-companion/koalablue/killerkoala_hybrid_companion.py",
  "runner": "scripts/run_killerkoala_hybrid.py",
  "heltec_t114_usb": "${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-auto}}"
}
JSON
  PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py --manifest >/dev/null
  KILLERKOALA_LLM_MODE="${KILLERKOALA_LLM_MODE:-fast_default}" \
    KILLERKOALA_LLM_MODEL="${KILLERKOALA_LLM_MODEL:-killerkoala-tinyllama:latest}" \
    KILLERKOALA_LLM_TIMEOUT_SECONDS="${KILLERKOALA_LLM_TIMEOUT_SECONDS:-2.5}" \
    PYTHONPATH=pi-companion python3 scripts/run_killerkoala_hybrid.py status --xp 100 --no-history > logs/killerkoala/flash_all_ai_voice_preview.json
  echo "KillerKoala AI voice config written to logs/killerkoala/flash_all_ai_voice_config.json"
  echo "Phrase-first preview written to logs/killerkoala/flash_all_ai_voice_preview.json"
}

setup_greatwhite_support_for_selected_mode() {
  if [[ "${RUN_GREATWHITE_SUPPORT}" != "1" && "${RUN_SMOKE}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== Greatwhite Wireshark/tshark and nRF Sniffer host-side support =="
  mkdir -p logs/greatwhite logs/hardware_validation
  bash scripts/setup_nrf_sniffer_ble.sh --check-only || true
  if ! python3 scripts/run_gw.py status; then
    echo "warning: Greatwhite status check reported an issue" >&2
    [[ "${STRICT_GREATWHITE_SUPPORT:-0}" == "1" ]] && exit 1
  fi
}

install_ble_node_manager_for_selected_mode() {
  if [[ "${RUN_BLE_NODE_MANAGER}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== KoalaByte BLE node manager service: Heltec T114 primary BLE node =="
  if [[ "${BUILD_ONLY}" == "1" ]]; then
    echo "Build-only mode: skipping BLE node manager service install/start."
    return 0
  fi
  KOALABYTE_HELTEC_USB_PORT="${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-/dev/ttyACM0}}" \
  KOALABYTE_ESP32_FACE_PORT="${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-}}" \
  PYTHON_BIN="${REPO_ROOT}/pi-companion/.venv/bin/python" \
  INSTALL_BLE_NODE_MANAGER_SERVICE="${INSTALL_BLE_NODE_MANAGER_SERVICE:-auto}" \
  STRICT_BLE_NODE_MANAGER_SERVICE="${STRICT_BLE_NODE_MANAGER_SERVICE:-0}" \
    bash scripts/install_ble_node_manager_service.sh
}

run_can_setup_and_checks() {
  if [[ "${RUN_CAN_CHECK}" != "1" ]]; then
    return 0
  fi
  local iface="${CAN_INTERFACE:-can0}"
  local bitrate="${CAN_BITRATE:-500000}"
  echo
  echo "== Koala Kan Kommander InnoMaker CAN setup and safe checks =="
  if [[ "${BUILD_ONLY}" == "1" ]]; then
    echo "Build-only mode: skipping can0 kernel/interface setup."
  else
    CAN_INTERFACE="${iface}" CAN_BITRATE="${bitrate}" STRICT_CAN_SETUP="${STRICT_CAN_SETUP:-0}" bash scripts/setup_can0.sh --interface "${iface}" --bitrate "${bitrate}"
  fi
  PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest --interface "${iface}"
  PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py inventory --interface "${iface}"
  PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py status --interface "${iface}"
}

checkout_heltec_if_requested

echo "== KoalaByte Blue readiness check =="
python3 scripts/check_repo_readiness.py

if [[ "${CHECK_ONLY}" == "1" ]]; then
  echo "Check-only mode complete."
  exit 0
fi

setup_wifi_for_selected_mode
setup_system_packages_for_selected_mode

if [[ "${RUN_PI}" == "1" ]]; then
  echo
  echo "== Installing/updating Raspberry Pi companion =="
  bash scripts/install_pi.sh
fi

setup_killerkoala_ai_voice_for_selected_mode
setup_greatwhite_support_for_selected_mode
setup_platformio_for_selected_mode
setup_nrf_tools_for_selected_mode

if [[ "${PREFLIGHT_BUILD}" == "1" ]]; then
  echo
  echo "== Build-only preflight for selected Heltec Edition firmware =="
  STRICT_TOOLS="${STRICT_TOOLS:-0}" bash scripts/build_firmware_all.sh
fi

prepare_t114_profiles_for_selected_mode

if [[ "${RUN_ESP32}" == "1" ]]; then
  echo
  echo "== ESP32-S3 DualEye firmware =="
  if [[ "${BUILD_ONLY}" == "1" ]]; then
    pio run -d firmware/esp32-dualeye
  else
    if [[ "${NO_MONITOR_DEFAULT}" == "1" ]]; then
      NO_MONITOR=1 bash scripts/flash_esp32.sh
    else
      NO_MONITOR=0 bash scripts/flash_esp32.sh
    fi
  fi
fi

if [[ "${RUN_HELTEC_T114}" == "1" ]]; then
  echo
  echo "== Heltec Mesh Node T114 v2 color mouth/GNSS/BLE firmware =="
  if [[ "${BUILD_ONLY}" == "1" ]]; then
    BUILD_ONLY=1 bash scripts/flash_heltec_mouth.sh --build-only
  else
    if [[ "${NO_MONITOR_DEFAULT}" == "1" ]]; then
      NO_MONITOR=1 bash scripts/flash_heltec_mouth.sh
    else
      NO_MONITOR=0 bash scripts/flash_heltec_mouth.sh
    fi
  fi
fi

install_ble_node_manager_for_selected_mode

if [[ "${RUN_NRF_KONNECT}" == "1" ]]; then
  echo
  echo "== Optional Koala Konnect: Heltec T114 USB HCI profile =="
  T114_BOARD="${T114_BOARD:-heltec_t114_v2/nrf52840}" bash scripts/build_koala_konnect_t114.sh
  if [[ "${BUILD_ONLY}" != "1" ]]; then
    T114_FLASH_METHOD="${T114_FLASH_METHOD:-west}" bash scripts/flash_koala_konnect_t114.sh
  else
    echo "Build-only mode: skipping T114 Koala Konnect apply step."
  fi
fi

run_can_setup_and_checks

if [[ "${RUN_SMOKE}" == "1" ]]; then
  echo
  echo "== Safe local smoke checks =="
  PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py status --xp 100
  PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest --interface "${CAN_INTERFACE:-can0}"
  python3 scripts/run_gw.py status || true
  bash scripts/setup_nrf_sniffer_ble.sh --check-only || true
  PYTHONPATH=pi-companion python3 scripts/check_killerkoala_boot_welcome.py || true
  PYTHONPATH=pi-companion python3 scripts/check_eucalyptus_cyberpet.py
  PYTHONPATH=pi-companion python3 scripts/check_thats_not_a_knife_monitors.py
  PYTHONPATH=pi-companion python3 scripts/run_thats_not_a_knife_loop.py --once
  PYTHONPATH=pi-companion python3 scripts/run_killerkoala_face_demo.py --sequence || true
fi

echo
echo "KoalaByte Blue flash/install helper complete."
