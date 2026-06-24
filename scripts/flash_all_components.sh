#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

RUN_PI=0
RUN_ESP32=0
RUN_NRF_BLE_PRIMARY=0
RUN_BLE_NODE_MANAGER=0
RUN_NRF_LAB=0
RUN_NRF_KONNECT=0
RUN_CAN_CHECK=0
RUN_AI_VOICE=0
BUILD_ONLY=0
CHECK_ONLY=0
RUN_SMOKE=0
NO_MONITOR_DEFAULT=1
ONE_SCRIPT_INSTALL=0

usage() {
  cat <<'EOF'
KoalaByte Blue V2 Heltec Edition all-component flash/install helper

Usage:
  bash scripts/flash_all_components.sh --install-firmware
  bash scripts/flash_all_components.sh --all
  bash scripts/flash_all_components.sh --pi --esp32 --ble-node-manager
  bash scripts/flash_all_components.sh --ai-voice
  bash scripts/flash_all_components.sh --can-check
  WIFI_INTERACTIVE=1 bash scripts/flash_all_components.sh --install-firmware
  WIFI_SSID="YourNetwork" WIFI_PASSWORD="YourPassword" bash scripts/flash_all_components.sh --install-firmware
  KOALABYTE_PRIMARY_BLE_PORT=/dev/koalabyte-heltec bash scripts/flash_all_components.sh --ble-node-manager
  ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32

Targets:
  --install-firmware  One-shot Heltec Edition install: Pi companion, AI voice, ESP32 DualEye, Heltec T114 dependency setup, Heltec-primary BLE node manager service, CAN setup/checks, and CAN manifest/status checks
  --all               Same target set as --install-firmware, without changing branches
  --pi                Install/update Raspberry Pi companion environment
  --ai-voice          Prepare/verify KillerKoala phrase-first companion config and optional TinyLlama/Ollama settings
  --esp32             Build and flash ESP32-S3 DualEye firmware with PlatformIO
  --ble-node-manager  Install/enable/start the Pi-side BLE node manager service with Heltec T114 nRF52840 as primary BLE board, ESP32-S3 as secondary node, and Pi BlueZ as secondary/fallback node
  --can-check         Load Linux CAN modules, optionally bring up can0, then run Koala Kan Kommander manifest/inventory/status checks
  --nrf-ble-primary   Legacy external dongle only: build/package/flash nRF52840 USB Dongle BLE-primary observer firmware
  --nrf-lab           Legacy external dongle only: build/package/flash nRF52840 Dongle KoalaByte Lab peripheral firmware
  --nrf-konnect       Legacy external dongle only: build/package/flash Koala Konnect USB HCI profile

Modes:
  --build-only        Build/package only; do not upload/flash firmware, install services, or configure can0
  --check-only        Run repo readiness check only
  --smoke             After selected actions, run safe local Pi companion smoke checks
  --monitor           Open ESP32 serial monitor after flash
  -h, --help          Show this help

Environment:
  WIFI_SSID               Optional WiFi SSID used before download/install steps.
  WIFI_PASSWORD           Optional WiFi password. Never printed by the WiFi helper.
  WIFI_INTERACTIVE        1 prompts for SSID/password during first startup.
  STRICT_WIFI_FIRST_BOOT  1 fails if WiFi/internet cannot be verified before downloads.
  ESP32_PORT              Optional PlatformIO upload/monitor port, for example /dev/ttyUSB0 or COM5
  KOALABYTE_PRIMARY_BLE_PORT Optional primary BLE serial port for the Heltec T114 nRF52840. Default: /dev/koalabyte-heltec, then /dev/ttyACM0
  KOALABYTE_HELTEC_USB_PORT  Optional Heltec T114 USB-C CDC serial port. Used as primary BLE when KOALABYTE_PRIMARY_BLE_PORT is unset.
  KOALABYTE_ESP32_FACE_PORT Optional ESP32 runtime serial port for eyes and secondary BLE observations.
  KOALABYTE_PI_BLUEZ_NODE 1/0. Default: 1. Enables Raspberry Pi onboard BlueZ as a secondary/fallback BLE node.
  INSTALL_HELTEC_T114_TOOLS auto/1/0. Default: auto. Installs/checks Heltec USB serial, udev, pyserial, bleak, and port discovery helpers.
  STRICT_HELTEC_T114_TOOLS 1 fails if Heltec runtime dependencies are missing.
  INSTALL_HELTEC_NRF_TOOLS auto/1/0. Default: auto. Set 1 to prepare west/nrfutil/NCS for future Heltec T114 firmware targets.
  NRF_DFU_PORT            Legacy external dongle bootloader serial port for explicit --nrf-* targets only.
  KOALABYTE_NRF_BLE_PORT  Legacy alias. In the Heltec Edition this may point at the Heltec T114 onboard nRF52840 for compatibility.
  CAN_INTERFACE           SocketCAN interface for Koala Kan Kommander. Default: can0
  CAN_BITRATE             CAN bitrate for setup_can0.sh. Default: 500000
  STRICT_CAN_SETUP        1 fails if can0 setup cannot complete. Default: 0.
  INSTALL_BLE_NODE_MANAGER_SERVICE auto/1/0. Default: auto. Installs/enables the BLE node manager service on systemd systems.
  STRICT_BLE_NODE_MANAGER_SERVICE 1 fails if the BLE node manager service cannot be installed/started.
  INSTALL_SYSTEM_PACKAGES auto/1/0. Default: auto. Attempts apt install on Raspberry Pi OS.
  STRICT_SYSTEM_PACKAGES  1 fails if packages cannot be checked/installed.
  INSTALL_ESP32_TOOLS     auto/1/0. Default: auto. Attempts to install missing PlatformIO.
  STRICT_ESP32_TOOLS      1 fails if PlatformIO is unavailable before ESP32 build/flash.
  INSTALL_NRF_TOOLS       auto/1/0. Default: auto. Attempts to install missing west/nrfutil when possible for explicit legacy --nrf-* targets.
  STRICT_NRF_TOOLS        1 fails if west/nrfutil are unavailable before nRF build/flash.
  INSTALL_NCS_TOOLCHAIN   auto/1/0. Default: auto. Downloads/updates full nRF Connect SDK/Zephyr toolchain for explicit legacy --nrf-* targets or INSTALL_HELTEC_NRF_TOOLS=1.
  STRICT_NCS_TOOLCHAIN    1 fails if the full NCS/Zephyr toolchain cannot be prepared.
  NCS_WORKSPACE           Default: $HOME/ncs
  NCS_REVISION            Default: v2.9.0
  ZEPHYR_SDK_VERSION      Default: 0.17.0
  NRFUTIL_INSTALL_CMD     Optional custom nrfutil install command for scripts/setup_nrf_tools.sh.
  BUILD_KOALA_KONNECT=1 can still be used with scripts/build_firmware_all.sh for optional HCI builds.
  KOALABYTE_TTS=1 enables Boomerang/KillerKoala spoken alerts after espeak-ng/espeak is installed.
  KILLERKOALA_LLM_MODE    fast_default/off/force. Default: fast_default; phrase engine remains default.
  KILLERKOALA_LLM_MODEL   Optional local Ollama model. Default: killerkoala-tinyllama:latest.
  KILLERKOALA_LLM_TIMEOUT_SECONDS Optional local model timeout. Default: 2.5.

Notes:
  - The Heltec Mesh Node T114 onboard nRF52840 is the default primary BLE board for the Heltec Edition.
  - The flasher now runs scripts/setup_heltec_t114_tools.sh for Heltec USB serial, udev, pyserial/bleak, and port discovery checks before installing the BLE node manager.
  - ESP32-S3 DualEye and Raspberry Pi onboard BlueZ are BLE nodes used for local UI observations, enrichment, and fallback checks.
  - The InnoMaker CAN adapter does not get flashed; KoalaByte uses Linux SocketCAN, can-utils, python-can, and Koala Kan Kommander scripts.
  - --install-firmware and --all run setup_can0.sh, then Koala Kan Kommander manifest, inventory, and status checks.
  - Legacy external dongle firmware targets remain explicit opt-in targets and are not part of the default Heltec Edition install.
  - WiFi/internet can be configured first so the Pi can download SDK/toolchain dependencies.
  - System packages, Heltec runtime dependencies, and PlatformIO are checked/prepared before relevant steps.
  - Pi system package setup also installs AI voice/TTS dependencies: espeak-ng, espeak, ALSA tools, PulseAudio CLI utilities, PortAudio, and python3-pyaudio.
  - KillerKoala AI voice setup keeps the anti-repeat phrase engine as the fast default and only uses TinyLlama/Ollama for flexible banter when enabled.
  - KillerKoala boot welcome speech runs after the mode selector and before the splash/menu unless KILLERKOALA_BOOT_WELCOME=0.
  - Koala Kan Kommander transmit remains gated for isolated bench CAN use; this script only sets up/checks can0 and writes safe status artifacts.
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
      RUN_PI=1
      RUN_AI_VOICE=1
      RUN_ESP32=1
      RUN_BLE_NODE_MANAGER=1
      RUN_CAN_CHECK=1
      ;;
    --all)
      RUN_PI=1
      RUN_AI_VOICE=1
      RUN_ESP32=1
      RUN_BLE_NODE_MANAGER=1
      RUN_CAN_CHECK=1
      ;;
    --pi) RUN_PI=1 ;;
    --ai-voice) RUN_PI=1; RUN_AI_VOICE=1 ;;
    --esp32) RUN_ESP32=1 ;;
    --nrf-ble-primary) RUN_NRF_BLE_PRIMARY=1 ;;
    --ble-node-manager) RUN_PI=1; RUN_BLE_NODE_MANAGER=1 ;;
    --nrf-lab) RUN_NRF_LAB=1 ;;
    --nrf-konnect) RUN_NRF_KONNECT=1 ;;
    --can-check) RUN_CAN_CHECK=1 ;;
    --build-only) BUILD_ONLY=1 ;;
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
  if [[ -e /dev/koalabyte-heltec ]]; then
    DEFAULT_PRIMARY_PORT="/dev/koalabyte-heltec"
  else
    DEFAULT_PRIMARY_PORT="/dev/ttyACM0"
  fi
  export KOALABYTE_PRIMARY_BLE_PORT="${KOALABYTE_PRIMARY_BLE_PORT:-${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-${DEFAULT_PRIMARY_PORT}}}}"
  export KOALABYTE_HELTEC_USB_PORT="${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT}}"
  export KOALABYTE_NRF_BLE_PORT="${KOALABYTE_NRF_BLE_PORT:-${KOALABYTE_PRIMARY_BLE_PORT}}"
fi

active_nrf_profiles=0
for flag in "${RUN_NRF_BLE_PRIMARY}" "${RUN_NRF_LAB}" "${RUN_NRF_KONNECT}"; do
  [[ "${flag}" == "1" ]] && active_nrf_profiles=$((active_nrf_profiles + 1))
done
if [[ "${active_nrf_profiles}" -gt 1 && "${BUILD_ONLY}" != "1" ]]; then
  echo "Refusing to flash more than one legacy external nRF52840 profile in one run." >&2
  echo "Run one of: --nrf-ble-primary, --nrf-lab, or --nrf-konnect. Use --build-only if you only want to build/package multiple profiles." >&2
  exit 2
fi

setup_wifi_for_selected_mode() {
  if [[ "${RUN_PI}" != "1" && "${RUN_AI_VOICE}" != "1" && "${RUN_ESP32}" != "1" && "${RUN_NRF_BLE_PRIMARY}" != "1" && "${RUN_BLE_NODE_MANAGER}" != "1" && "${RUN_NRF_LAB}" != "1" && "${RUN_NRF_KONNECT}" != "1" && "${RUN_CAN_CHECK}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== First-startup WiFi/internet setup =="
  CONNECT_WIFI_FIRST_BOOT="${CONNECT_WIFI_FIRST_BOOT:-auto}" STRICT_WIFI_FIRST_BOOT="${STRICT_WIFI_FIRST_BOOT:-0}" bash scripts/setup_wifi_first_boot.sh
}

setup_system_packages_for_selected_mode() {
  if [[ "${RUN_PI}" != "1" && "${RUN_AI_VOICE}" != "1" && "${RUN_ESP32}" != "1" && "${RUN_NRF_BLE_PRIMARY}" != "1" && "${RUN_BLE_NODE_MANAGER}" != "1" && "${RUN_NRF_LAB}" != "1" && "${RUN_NRF_KONNECT}" != "1" && "${RUN_CAN_CHECK}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== Raspberry Pi/system package dependency setup, including Heltec T114 USB serial, CAN, python-can, and AI voice/TTS packages =="
  STRICT_SYSTEM_PACKAGES="${STRICT_SYSTEM_PACKAGES:-0}" bash scripts/setup_system_packages.sh
}

setup_heltec_t114_tools_for_selected_mode() {
  if [[ "${RUN_BLE_NODE_MANAGER}" != "1" && "${RUN_PI}" != "1" && "${RUN_SMOKE}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== Heltec T114 dependency setup: USB serial, udev, pyserial/bleak, and port discovery =="
  if [[ "${BUILD_ONLY}" == "1" ]]; then
    echo "Build-only mode: running Heltec dependency check only."
    STRICT_HELTEC_T114_TOOLS="${STRICT_HELTEC_T114_TOOLS:-0}" PYTHON_BIN="${REPO_ROOT}/pi-companion/.venv/bin/python" bash scripts/setup_heltec_t114_tools.sh --check-only || true
    return 0
  fi
  INSTALL_HELTEC_T114_TOOLS="${INSTALL_HELTEC_T114_TOOLS:-auto}" \
  STRICT_HELTEC_T114_TOOLS="${STRICT_HELTEC_T114_TOOLS:-0}" \
  INSTALL_HELTEC_NRF_TOOLS="${INSTALL_HELTEC_NRF_TOOLS:-auto}" \
  PYTHON_BIN="${REPO_ROOT}/pi-companion/.venv/bin/python" \
    bash scripts/setup_heltec_t114_tools.sh
}

setup_esp32_tools_for_selected_mode() {
  if [[ "${RUN_ESP32}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== PlatformIO setup for ESP32-S3 DualEye workflow =="
  STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS:-1}" bash scripts/setup_esp32_tools.sh
}

setup_nrf_tools_for_selected_mode() {
  if [[ "${RUN_NRF_BLE_PRIMARY}" != "1" && "${RUN_NRF_LAB}" != "1" && "${RUN_NRF_KONNECT}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== west/nrfutil setup for explicit legacy external nRF52840 workflows =="
  if [[ "${BUILD_ONLY}" == "1" ]]; then
    STRICT_NRF_TOOLS="${STRICT_NRF_TOOLS:-1}" bash scripts/setup_nrf_tools.sh --west-only
  else
    STRICT_NRF_TOOLS="${STRICT_NRF_TOOLS:-1}" bash scripts/setup_nrf_tools.sh
  fi
  echo
  echo "== Full nRF Connect SDK / Zephyr toolchain setup =="
  STRICT_NCS_TOOLCHAIN="${STRICT_NCS_TOOLCHAIN:-${STRICT_NRF_TOOLS:-1}}" INSTALL_NCS_TOOLCHAIN="${INSTALL_NCS_TOOLCHAIN:-auto}" bash scripts/setup_nrf_connect_sdk_toolchain.sh
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
  "fast_default": "pi-companion/koalablue/killerkoala_vocabulary.py",
  "hybrid_companion": "pi-companion/koalablue/killerkoala_hybrid_companion.py",
  "runner": "scripts/run_killerkoala_hybrid.py",
  "training_doc": "docs/KILLERKOALA_LORA_TRAINING.md",
  "ollama_modelfile": "training/killerkoala_lora/Modelfile.killerkoala-tinyllama"
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

install_ble_node_manager_for_selected_mode() {
  if [[ "${RUN_BLE_NODE_MANAGER}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== KoalaByte BLE node manager service: Heltec T114 nRF52840 primary BLE board with ESP32-S3 and Pi BlueZ nodes =="
  if [[ "${BUILD_ONLY}" == "1" ]]; then
    echo "Build-only mode: skipping BLE node manager service install/start."
    return 0
  fi
  KOALABYTE_PRIMARY_BLE_PORT="${KOALABYTE_PRIMARY_BLE_PORT:-${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-/dev/koalabyte-heltec}}}" \
  KOALABYTE_HELTEC_USB_PORT="${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-/dev/koalabyte-heltec}}" \
  KOALABYTE_ESP32_FACE_PORT="${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-}}" \
  KOALABYTE_PI_BLUEZ_NODE="${KOALABYTE_PI_BLUEZ_NODE:-1}" \
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

echo "== KoalaByte Blue V2 Heltec Edition readiness check =="
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

setup_heltec_t114_tools_for_selected_mode
setup_killerkoala_ai_voice_for_selected_mode
setup_esp32_tools_for_selected_mode
setup_nrf_tools_for_selected_mode

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

if [[ "${RUN_NRF_BLE_PRIMARY}" == "1" ]]; then
  echo
  echo "== Legacy external nRF52840 Dongle BLE-primary firmware =="
  bash scripts/build_nrf52840_dongle_ble_primary.sh
  if [[ "${BUILD_ONLY}" != "1" ]]; then
    bash scripts/flash_nrf52840_dongle_ble_primary_dfu.sh
  else
    echo "Build-only mode: skipping legacy Dongle BLE-primary DFU package/flash step."
  fi
fi

install_ble_node_manager_for_selected_mode

if [[ "${RUN_NRF_LAB}" == "1" ]]; then
  echo
  echo "== Legacy external nRF52840 Dongle KoalaByte Lab firmware =="
  bash scripts/build_nrf52840_dongle_lab.sh
  if [[ "${BUILD_ONLY}" != "1" ]]; then
    bash scripts/flash_nrf52840_dongle_lab_dfu.sh
  else
    echo "Build-only mode: skipping KoalaByte Lab DFU package/flash step."
  fi
fi

if [[ "${RUN_NRF_KONNECT}" == "1" ]]; then
  echo
  echo "== Legacy external nRF52840 Dongle Koala Konnect firmware =="
  bash scripts/build_koala_konnect.sh
  if [[ "${BUILD_ONLY}" != "1" ]]; then
    bash scripts/flash_koala_konnect.sh
  else
    echo "Build-only mode: skipping Koala Konnect DFU package/flash step."
  fi
fi

run_can_setup_and_checks

if [[ "${RUN_SMOKE}" == "1" ]]; then
  echo
  echo "== Safe local smoke checks =="
  PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py manifest
  PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py inventory
  PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py status --xp 100
  PYTHONPATH=pi-companion python3 scripts/run_killerkoala_hybrid.py banter --xp 100 --flexible --text "flash all smoke check" --no-history || true
  PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest --interface "${CAN_INTERFACE:-can0}"
  PYTHONPATH=pi-companion python3 scripts/check_killerkoala_boot_welcome.py
  KOALABYTE_TTS=0 PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py preview --event boomerang_xp --xp 100 >/dev/null
  PYTHONPATH=pi-companion python3 scripts/check_eucalyptus_cyberpet.py
  PYTHONPATH=pi-companion python3 scripts/check_thats_not_a_knife_monitors.py
  PYTHONPATH=pi-companion python3 scripts/run_thats_not_a_knife_loop.py --once
  PYTHONPATH=pi-companion python3 scripts/run_boomerang.py <<< $'quit' >/dev/null || true
fi

echo
echo "KoalaByte Blue V2 Heltec Edition flash/install helper complete."