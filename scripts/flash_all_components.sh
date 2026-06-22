#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"
ORIGINAL_ARGS=("$@")

RUN_PI=0
RUN_ESP32=0
RUN_HELTEC_T114=0
RUN_BLE_NODE_MANAGER=0
RUN_NRF_LAB=0
RUN_NRF_KONNECT=0
RUN_CAN_CHECK=0
RUN_AI_VOICE=0
BUILD_ONLY=0
CHECK_ONLY=0
RUN_SMOKE=0
NO_MONITOR_DEFAULT=1
CHECKOUT_HELTEC=0
PREFLIGHT_BUILD=0
ONE_SCRIPT_INSTALL=0

usage() {
  cat <<'EOF'
KoalaByte Blue all-component flash/install helper

Usage:
  bash scripts/flash_all_components.sh --install-firmware
  bash scripts/flash_all_components.sh --all
  bash scripts/flash_all_components.sh --pi --esp32 --heltec-t114
  bash scripts/flash_all_components.sh --ble-node-manager
  bash scripts/flash_all_components.sh --ai-voice
  bash scripts/flash_all_components.sh --can-check
  bash scripts/flash_all_components.sh --nrf-konnect
  WIFI_INTERACTIVE=1 bash scripts/flash_all_components.sh --install-firmware
  WIFI_SSID="YourNetwork" WIFI_PASSWORD="YourPassword" bash scripts/flash_all_components.sh --install-firmware
  ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32
  HELTEC_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --heltec-t114
  NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --nrf-lab
  T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/flash_all_components.sh --nrf-konnect

Targets:
  --install-firmware  One-script Heltec branch install: git checkout heltec, readiness check, build-only preflight, then install/flash Pi companion, ESP32 DualEye, Heltec T114, BLE node manager service, CAN setup/checks, and CAN manifest/status checks
  --all               Install Pi companion, prepare KillerKoala AI voice, flash ESP32 DualEye, flash Heltec T114 color mouth/GNSS/BLE firmware, install/start BLE node manager service, set up/check can0, and run Koala Kan checks
  --pi                Install/update Raspberry Pi companion environment
  --ai-voice          Prepare/verify KillerKoala phrase-first companion config and optional TinyLlama/Ollama settings
  --esp32             Build and flash ESP32-S3 DualEye firmware with PlatformIO
  --heltec-t114       Build and flash Heltec Mesh Node T114 v2 nRF52840 color TFT mouth/GNSS/BLE-primary firmware over USB-C
  --ble-node-manager  Install/enable/start the Pi-side BLE node manager service with Heltec T114 as primary BLE node
  --nrf-lab           Optional: build/package/flash separate nRF52840 Dongle KoalaByte Lab firmware
  --nrf-konnect       Optional Koala Konnect action: build/flash the Heltec T114 USB HCI profile for supported BlueZ host use
  --can-check         Load Linux CAN modules, optionally bring up can0, then run Koala Kan Kommander manifest/inventory/status checks

Modes:
  --build-only        Build/package only; do not upload/flash firmware, install services, or configure can0
  --preflight-build   Run the all-firmware build helper before flashing selected targets
  --checkout-heltec   Checkout the heltec branch before continuing
  --check-only        Run repo readiness check only
  --smoke             After selected actions, run safe local Pi companion smoke checks
  --monitor           Open ESP32/Heltec serial monitor after flash where supported
  -h, --help          Show this help

Environment:
  WIFI_SSID               Optional WiFi SSID used before download/install steps.
  WIFI_PASSWORD           Optional WiFi password. Never printed by the WiFi helper.
  WIFI_INTERACTIVE        1 prompts for SSID/password during first startup.
  STRICT_WIFI_FIRST_BOOT  1 fails if WiFi/internet cannot be verified before downloads.
  ESP32_PORT              Optional PlatformIO upload/monitor port, for example /dev/ttyUSB0 or COM5
  HELTEC_PORT             Optional Heltec T114 USB CDC upload/monitor port, for example /dev/ttyACM0 or COM7
  KOALABYTE_HELTEC_USB_PORT Optional Pi runtime USB CDC port for T114 face/GNSS/BLE JSON bridge.
  KOALABYTE_ESP32_FACE_PORT Optional ESP32 runtime serial port for eyes and optional secondary BLE node.
  T114_BOARD              Optional Zephyr board target for --nrf-konnect. Recommended: heltec_t114_v2/nrf52840
  T114_FLASH_METHOD       west or uf2 for --nrf-konnect. Default: west
  T114_PORT               Mounted UF2 bootloader path when T114_FLASH_METHOD=uf2
  T114_2G4_ANTENNA        connector/external/hardware/onboard/disabled for T114 2.4 GHz antenna handling. Default: connector
  CAN_INTERFACE           SocketCAN interface for Koala Kan Kommander. Default: can0
  CAN_BITRATE             CAN bitrate for setup_can0.sh. Default: 500000
  STRICT_CAN_SETUP        1 fails if can0 setup cannot complete. Default: 0.
  INSTALL_BLE_NODE_MANAGER_SERVICE auto/1/0. Default: auto. Installs/enables the BLE node manager service on systemd systems.
  STRICT_BLE_NODE_MANAGER_SERVICE 1 fails if the BLE node manager service cannot be installed/started.
  NRF_DFU_PORT           Optional separate nRF52840 Dongle bootloader serial port, for example /dev/ttyACM0 or COM7
  INSTALL_SYSTEM_PACKAGES auto/1/0. Default: auto. Attempts apt install on Raspberry Pi OS.
  STRICT_SYSTEM_PACKAGES  1 fails if system packages cannot be checked/installed.
  INSTALL_ESP32_TOOLS     auto/1/0. Default: auto. Attempts to install missing PlatformIO.
  STRICT_ESP32_TOOLS      1 fails if PlatformIO is unavailable before ESP32/Heltec build/flash.
  INSTALL_NRF_TOOLS       auto/1/0. Default: auto. Attempts to install missing west/nrfutil when possible.
  STRICT_NRF_TOOLS        1 fails if west/nrfutil are unavailable before separate nRF dongle or T114 HCI USB build/flash.
  INSTALL_NCS_TOOLCHAIN   auto/1/0. Default: auto. Downloads/updates full nRF Connect SDK/Zephyr toolchain.
  STRICT_NCS_TOOLCHAIN    1 fails if the full NCS/Zephyr toolchain cannot be prepared.
  NCS_WORKSPACE           Default: $HOME/ncs
  NCS_REVISION            Default: v2.9.0
  ZEPHYR_SDK_VERSION      Default: 0.17.0
  NRFUTIL_INSTALL_CMD     Optional custom nrfutil install command for scripts/setup_nrf_tools.sh.
  BUILD_SEPARATE_NRF=1 builds the optional separate nRF52840 Dongle KoalaByte Lab firmware in scripts/build_firmware_all.sh.
  BUILD_KOALA_KONNECT=1 builds the optional Koala Konnect HCI adapter firmware.
  KOALABYTE_TTS=1 enables Boomerang/KillerKoala spoken alerts after espeak-ng/espeak is installed.
  KILLERKOALA_LLM_MODE    fast_default/off/force. Default: fast_default; phrase engine remains default.
  KILLERKOALA_LLM_MODEL   Optional local Ollama model. Default: killerkoala-tinyllama:latest.
  KILLERKOALA_LLM_TIMEOUT_SECONDS Optional local model timeout. Default: 2.5.

One-script install flow:
  --install-firmware folds this manual sequence into one command:
    git checkout heltec
    python3 scripts/check_repo_readiness.py
    BUILD_ONLY=1 bash scripts/flash_all_components.sh --all
    HELTEC_PORT=${HELTEC_PORT:-/dev/ttyACM0} bash scripts/flash_all_components.sh --heltec-t114
    KOALABYTE_HELTEC_USB_PORT=${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-/dev/ttyACM0}} bash scripts/install_ble_node_manager_service.sh
    CAN_INTERFACE=${CAN_INTERFACE:-can0} CAN_BITRATE=${CAN_BITRATE:-500000} bash scripts/setup_can0.sh

Notes:
  - The Heltec branch treats the Heltec Mesh Node T114 v2 as a USB-C connected nRF52840 board.
  - Heltec GPS, LoRa/SX1262, BLE, and color mouth display use the T114 hardware and communicate to the Pi over USB CDC.
  - The BLE node manager service starts the Heltec T114 as the primary passive BLE scanner automatically after one-shot install.
  - Do not wire Heltec TX/RX pins to the Raspberry Pi GPIO header for the KillerKoala face/GNSS/LoRa/BLE channel.
  - The InnoMaker CAN adapter does not get flashed; KoalaByte uses Linux SocketCAN, can-utils, python-can, and Koala Kan Kommander scripts.
  - --install-firmware and --all run setup_can0.sh, then Koala Kan Kommander manifest, inventory, and status checks.
  - The separate Nordic nRF52840 Dongle is optional/legacy on this branch; it is not flashed by --all.
  - --nrf-konnect is the optional Koala Konnect action for the Heltec T114 USB HCI profile; flashing it replaces the normal Heltec mouth/GNSS/BLE-primary firmware until that profile is flashed back.
  - WiFi/internet can be configured first so the Pi can download SDK/toolchain dependencies.
  - System packages, PlatformIO, west, nrfutil, and the full NCS/Zephyr toolchain are checked/prepared before relevant flashing steps.
  - Pi system package setup also installs AI voice/TTS dependencies: espeak-ng, espeak, ALSA tools, PulseAudio CLI utilities, PortAudio, and python3-pyaudio.
  - KillerKoala AI voice setup keeps the anti-repeat phrase engine as the fast default and only uses TinyLlama/Ollama for flexible banter when enabled.
  - KillerKoala boot welcome speech runs after the mode selector and before the splash/menu unless KILLERKOALA_BOOT_WELCOME=0.
  - If NRF_DFU_PORT is unset, the optional separate nRF helper creates the DFU ZIP but does not flash.
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
      CHECKOUT_HELTEC=1
      PREFLIGHT_BUILD=1
      RUN_PI=1
      RUN_AI_VOICE=1
      RUN_ESP32=1
      RUN_HELTEC_T114=1
      RUN_BLE_NODE_MANAGER=1
      RUN_CAN_CHECK=1
      ;;
    --all)
      RUN_PI=1
      RUN_AI_VOICE=1
      RUN_ESP32=1
      RUN_HELTEC_T114=1
      RUN_BLE_NODE_MANAGER=1
      RUN_CAN_CHECK=1
      ;;
    --pi) RUN_PI=1 ;;
    --ai-voice) RUN_PI=1; RUN_AI_VOICE=1 ;;
    --esp32) RUN_ESP32=1 ;;
    --heltec-t114) RUN_HELTEC_T114=1 ;;
    --ble-node-manager) RUN_PI=1; RUN_BLE_NODE_MANAGER=1 ;;
    --nrf-lab) RUN_NRF_LAB=1 ;;
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
    echo "Not inside a git checkout; cannot switch to the heltec branch." >&2
    exit 1
  fi
  local current_branch
  current_branch="$(git rev-parse --abbrev-ref HEAD)"
  if [[ "${current_branch}" == "heltec" ]]; then
    echo "Already on heltec branch."
    return 0
  fi
  echo "Checking out heltec branch..."
  git fetch origin heltec || true
  git checkout heltec
  if [[ "${KOALABYTE_FLASH_ALL_REEXECED:-0}" != "1" ]]; then
    echo "Re-running flash helper from the heltec branch copy..."
    exec env KOALABYTE_FLASH_ALL_REEXECED=1 bash scripts/flash_all_components.sh "${ORIGINAL_ARGS[@]}"
  fi
}

if [[ "${RUN_NRF_LAB}" == "1" && "${RUN_NRF_KONNECT}" == "1" && "${BUILD_ONLY}" != "1" ]]; then
  echo "Refusing to flash both optional nRF profiles in one run. The selected nRF target can hold only one active profile." >&2
  echo "Run one of: --nrf-lab or --nrf-konnect. Use --build-only if you only want to build/package both." >&2
  exit 2
fi

setup_wifi_for_selected_mode() {
  if [[ "${RUN_PI}" != "1" && "${RUN_AI_VOICE}" != "1" && "${RUN_ESP32}" != "1" && "${RUN_HELTEC_T114}" != "1" && "${RUN_BLE_NODE_MANAGER}" != "1" && "${RUN_NRF_LAB}" != "1" && "${RUN_NRF_KONNECT}" != "1" && "${RUN_CAN_CHECK}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== First-startup WiFi/internet setup =="
  CONNECT_WIFI_FIRST_BOOT="${CONNECT_WIFI_FIRST_BOOT:-auto}" STRICT_WIFI_FIRST_BOOT="${STRICT_WIFI_FIRST_BOOT:-0}" bash scripts/setup_wifi_first_boot.sh
}

setup_system_packages_for_selected_mode() {
  if [[ "${RUN_PI}" != "1" && "${RUN_AI_VOICE}" != "1" && "${RUN_ESP32}" != "1" && "${RUN_HELTEC_T114}" != "1" && "${RUN_BLE_NODE_MANAGER}" != "1" && "${RUN_NRF_LAB}" != "1" && "${RUN_NRF_KONNECT}" != "1" && "${RUN_CAN_CHECK}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== Raspberry Pi/system package dependency setup, including CAN, python-can, and AI voice/TTS packages =="
  STRICT_SYSTEM_PACKAGES="${STRICT_SYSTEM_PACKAGES:-0}" bash scripts/setup_system_packages.sh
}

setup_platformio_for_selected_mode() {
  if [[ "${RUN_ESP32}" != "1" && "${RUN_HELTEC_T114}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== PlatformIO setup for ESP32-S3 DualEye and Heltec T114 workflows =="
  STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS:-1}" bash scripts/setup_esp32_tools.sh
}

setup_nrf_tools_for_selected_mode() {
  if [[ "${RUN_NRF_LAB}" != "1" && "${RUN_NRF_KONNECT}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== west/nrfutil setup for optional nRF workflows, including T114 Koala Konnect HCI USB =="
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
  "ollama_modelfile": "training/killerkoala_lora/Modelfile.killerkoala-tinyllama",
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
setup_platformio_for_selected_mode
setup_nrf_tools_for_selected_mode

if [[ "${PREFLIGHT_BUILD}" == "1" ]]; then
  echo
  echo "== Build-only preflight for selected Heltec branch firmware =="
  STRICT_TOOLS="${STRICT_TOOLS:-0}" bash scripts/build_firmware_all.sh
fi

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
  echo "== Heltec Mesh Node T114 v2 color mouth/GNSS/BLE-primary firmware =="
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

if [[ "${RUN_NRF_LAB}" == "1" ]]; then
  echo
  echo "== Optional separate nRF52840 Dongle KoalaByte Lab firmware =="
  bash scripts/build_nrf52840_dongle_lab.sh
  if [[ "${BUILD_ONLY}" != "1" ]]; then
    bash scripts/flash_nrf52840_dongle_lab_dfu.sh
  else
    echo "Build-only mode: skipping KoalaByte Lab DFU package/flash step."
  fi
fi

if [[ "${RUN_NRF_KONNECT}" == "1" ]]; then
  echo
  echo "== Optional Koala Konnect: Heltec T114 USB HCI profile =="
  T114_BOARD="${T114_BOARD:-heltec_t114_v2/nrf52840}" bash scripts/build_nrf52840_t114_hci_usb.sh
  if [[ "${BUILD_ONLY}" != "1" ]]; then
    T114_FLASH_METHOD="${T114_FLASH_METHOD:-west}" bash scripts/flash_nrf52840_t114_hci_usb.sh
  else
    echo "Build-only mode: skipping T114 Koala Konnect flash step."
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
  PYTHONPATH=pi-companion python3 scripts/run_killerkoala_face_demo.py --sequence || true
  PYTHONPATH=pi-companion python3 scripts/run_boomerang.py <<< $'quit' >/dev/null || true
fi

echo
echo "KoalaByte Blue flash/install helper complete."
