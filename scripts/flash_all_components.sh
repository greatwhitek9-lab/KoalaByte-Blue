#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

RUN_PI=0
RUN_ESP32=0
RUN_NRF_LAB=0
RUN_NRF_KONNECT=0
RUN_NRF_T114_LAB=0
RUN_CAN_CHECK=0
BUILD_ONLY=0
CHECK_ONLY=0
RUN_SMOKE=0
NO_MONITOR_DEFAULT=1

usage() {
  cat <<'EOF'
KoalaByte Blue all-component flash/install helper

Usage:
  bash scripts/flash_all_components.sh --all
  bash scripts/flash_all_components.sh --pi --esp32 --nrf-lab
  WIFI_INTERACTIVE=1 bash scripts/flash_all_components.sh --all
  WIFI_SSID="YourNetwork" WIFI_PASSWORD="YourPassword" bash scripts/flash_all_components.sh --all
  NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --nrf-lab
  T114_BOARD=<confirmed_zephyr_board_target> bash scripts/flash_all_components.sh --nrf-t114-lab --build-only
  T114_BOARD=<confirmed_zephyr_board_target> T114_FLASH_CMD='<confirmed flash command>' bash scripts/flash_all_components.sh --nrf-t114-lab
  ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32

Targets:
  --all            Install Pi companion, flash ESP32, build/package/flash nRF52840 KoalaByte Lab, and run CAN manifest check
  --pi             Install/update Raspberry Pi companion environment
  --esp32          Build and flash ESP32-S3 DualEye firmware with PlatformIO
  --nrf-lab        Build/package/flash nRF52840 Dongle KoalaByte Lab firmware
  --nrf-konnect    Build/package/flash optional Koala Konnect USB HCI profile instead of KoalaByte Lab
  --nrf-t114-lab   Build/flash alternate Heltec Mesh Node T114 V2 nRF52840 KoalaByte Lab target; not used by --all
  --can-check      Write Koala Kan Kommander InnoMaker manifest artifact; no CAN traffic is sent

Modes:
  --build-only     Build/package only; do not upload/flash firmware
  --check-only     Run repo readiness check only
  --smoke          After selected actions, run safe local Pi companion smoke checks
  --monitor        Open ESP32 serial monitor after flash
  -h, --help       Show this help

Environment:
  WIFI_SSID               Optional WiFi SSID used before download/install steps.
  WIFI_PASSWORD           Optional WiFi password. Never printed by the WiFi helper.
  WIFI_INTERACTIVE        1 prompts for SSID/password during first startup.
  STRICT_WIFI_FIRST_BOOT  1 fails if WiFi/internet cannot be verified before downloads.
  ESP32_PORT              Optional PlatformIO upload/monitor port, for example /dev/ttyUSB0 or COM5
  NRF_DFU_PORT           Optional nRF52840 Dongle bootloader serial port, for example /dev/ttyACM0 or COM7
  T114_BOARD              Confirmed Zephyr/NCS board target for the Heltec Mesh Node T114 V2 alternate path.
  T114_PORT               Optional serial/DFU port for the T114 alternate path.
  T114_FLASH_CMD          Confirmed vendor/bootloader flash command for the T114 alternate path.
  INSTALL_SYSTEM_PACKAGES auto/1/0. Default: auto. Attempts apt install on Raspberry Pi OS.
  STRICT_SYSTEM_PACKAGES  1 fails if system packages cannot be checked/installed.
  INSTALL_ESP32_TOOLS     auto/1/0. Default: auto. Attempts to install missing PlatformIO.
  STRICT_ESP32_TOOLS      1 fails if PlatformIO is unavailable before ESP32 build/flash.
  INSTALL_NRF_TOOLS       auto/1/0. Default: auto. Attempts to install missing west/nrfutil when possible.
  STRICT_NRF_TOOLS        1 fails if west/nrfutil are unavailable before nRF build/flash.
  INSTALL_NCS_TOOLCHAIN   auto/1/0. Default: auto. Downloads/updates full nRF Connect SDK/Zephyr toolchain.
  STRICT_NCS_TOOLCHAIN    1 fails if the full NCS/Zephyr toolchain cannot be prepared.
  NCS_WORKSPACE           Default: $HOME/ncs
  NCS_REVISION            Default: v2.9.0
  ZEPHYR_SDK_VERSION      Default: 0.17.0
  NRFUTIL_INSTALL_CMD     Optional custom nrfutil install command for scripts/setup_nrf_tools.sh.
  BUILD_KOALA_KONNECT=1 can still be used with scripts/build_firmware_all.sh for optional HCI builds.
  KOALABYTE_TTS=1 enables Boomerang/KillerKoala spoken alerts after espeak-ng/espeak is installed.

Notes:
  - The Nordic nRF52840 Dongle remains the default KoalaByte Lab / Koala Konnect target.
  - The T114 nRF52840 path is opt-in and experimental until its exact Zephyr board target and flash method are validated.
  - The T114 board can run KoalaByte firmware or Meshtastic firmware, not both at once unless a future combined firmware is built.
  - WiFi/internet can be configured first so the Pi can download SDK/toolchain dependencies.
  - System packages, PlatformIO, west, nrfutil, and the full NCS/Zephyr toolchain are checked/prepared before relevant flashing steps.
  - Pi system package setup also installs AI voice/TTS dependencies: espeak-ng, espeak, ALSA tools, PulseAudio CLI utilities, PortAudio, and python3-pyaudio.
  - KillerKoala boot welcome speech runs after the mode selector and before the splash/menu unless KILLERKOALA_BOOT_WELCOME=0.
  - macOS say is an optional fallback on Apple systems; Raspberry Pi OS uses espeak-ng/espeak.
  - If NRF_DFU_PORT is unset, the nRF helper creates the DFU ZIP but does not flash.
  - If T114_FLASH_CMD is unset, the T114 helper builds but refuses to guess a flash method.
  - Koala Kan Kommander remains gated for isolated bench CAN transmit; this script only writes a manifest/check artifact.
EOF
}

if [[ $# -eq 0 ]]; then
  usage
  exit 0
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)
      RUN_PI=1
      RUN_ESP32=1
      RUN_NRF_LAB=1
      RUN_CAN_CHECK=1
      ;;
    --pi) RUN_PI=1 ;;
    --esp32) RUN_ESP32=1 ;;
    --nrf-lab) RUN_NRF_LAB=1 ;;
    --nrf-konnect) RUN_NRF_KONNECT=1 ;;
    --nrf-t114-lab) RUN_NRF_T114_LAB=1 ;;
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

if [[ "${RUN_NRF_LAB}" == "1" && "${RUN_NRF_KONNECT}" == "1" && "${BUILD_ONLY}" != "1" ]]; then
  echo "Refusing to flash both nRF dongle profiles in one run. The dongle can hold only one active profile." >&2
  echo "Run one of: --nrf-lab or --nrf-konnect. Use --build-only if you only want to build/package both." >&2
  exit 2
fi

if [[ "${RUN_NRF_T114_LAB}" == "1" && ( "${RUN_NRF_LAB}" == "1" || "${RUN_NRF_KONNECT}" == "1" ) && "${BUILD_ONLY}" != "1" ]]; then
  echo "Refusing to flash the T114 alternate target and Nordic dongle target in the same non-build-only run." >&2
  echo "Build both with --build-only, or flash one physical target at a time." >&2
  exit 2
fi

setup_wifi_for_selected_mode() {
  if [[ "${RUN_PI}" != "1" && "${RUN_ESP32}" != "1" && "${RUN_NRF_LAB}" != "1" && "${RUN_NRF_KONNECT}" != "1" && "${RUN_NRF_T114_LAB}" != "1" && "${RUN_CAN_CHECK}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== First-startup WiFi/internet setup =="
  CONNECT_WIFI_FIRST_BOOT="${CONNECT_WIFI_FIRST_BOOT:-auto}" STRICT_WIFI_FIRST_BOOT="${STRICT_WIFI_FIRST_BOOT:-0}" bash scripts/setup_wifi_first_boot.sh
}

setup_system_packages_for_selected_mode() {
  if [[ "${RUN_PI}" != "1" && "${RUN_ESP32}" != "1" && "${RUN_NRF_LAB}" != "1" && "${RUN_NRF_KONNECT}" != "1" && "${RUN_NRF_T114_LAB}" != "1" && "${RUN_CAN_CHECK}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== Raspberry Pi/system package dependency setup, including AI voice/TTS packages =="
  STRICT_SYSTEM_PACKAGES="${STRICT_SYSTEM_PACKAGES:-0}" bash scripts/setup_system_packages.sh
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
  if [[ "${RUN_NRF_LAB}" != "1" && "${RUN_NRF_KONNECT}" != "1" && "${RUN_NRF_T114_LAB}" != "1" ]]; then
    return 0
  fi
  echo
  echo "== west/nrfutil setup for nRF52840 workflows =="
  if [[ "${BUILD_ONLY}" == "1" || "${RUN_NRF_T114_LAB}" == "1" ]]; then
    STRICT_NRF_TOOLS="${STRICT_NRF_TOOLS:-1}" bash scripts/setup_nrf_tools.sh --west-only
  else
    STRICT_NRF_TOOLS="${STRICT_NRF_TOOLS:-1}" bash scripts/setup_nrf_tools.sh
  fi
  echo
  echo "== Full nRF Connect SDK / Zephyr toolchain setup =="
  STRICT_NCS_TOOLCHAIN="${STRICT_NCS_TOOLCHAIN:-${STRICT_NRF_TOOLS:-1}}" INSTALL_NCS_TOOLCHAIN="${INSTALL_NCS_TOOLCHAIN:-auto}" bash scripts/setup_nrf_connect_sdk_toolchain.sh
}

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

if [[ "${RUN_NRF_LAB}" == "1" ]]; then
  echo
  echo "== nRF52840 Dongle KoalaByte Lab firmware =="
  bash scripts/build_nrf52840_dongle_lab.sh
  if [[ "${BUILD_ONLY}" != "1" ]]; then
    bash scripts/flash_nrf52840_dongle_lab_dfu.sh
  else
    echo "Build-only mode: skipping KoalaByte Lab DFU package/flash step."
  fi
fi

if [[ "${RUN_NRF_T114_LAB}" == "1" ]]; then
  echo
  echo "== Alternate Heltec Mesh Node T114 V2 nRF52840 KoalaByte Lab firmware =="
  bash scripts/build_nrf52840_t114_lab.sh
  if [[ "${BUILD_ONLY}" != "1" ]]; then
    bash scripts/flash_nrf52840_t114_lab.sh
  else
    echo "Build-only mode: skipping T114 alternate target flash step."
  fi
fi

if [[ "${RUN_NRF_KONNECT}" == "1" ]]; then
  echo
  echo "== nRF52840 Dongle Koala Konnect firmware =="
  bash scripts/build_koala_konnect.sh
  if [[ "${BUILD_ONLY}" != "1" ]]; then
    bash scripts/flash_koala_konnect.sh
  else
    echo "Build-only mode: skipping Koala Konnect DFU package/flash step."
  fi
fi

if [[ "${RUN_CAN_CHECK}" == "1" ]]; then
  echo
  echo "== Koala Kan Kommander InnoMaker CAN manifest check =="
  PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
fi

if [[ "${RUN_SMOKE}" == "1" ]]; then
  echo
  echo "== Safe local smoke checks =="
  PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py manifest
  PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py inventory
  PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py status --xp 100
  PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
  PYTHONPATH=pi-companion python3 scripts/check_killerkoala_boot_welcome.py
  KOALABYTE_TTS=0 PYTHONPATH=pi-companion python3 scripts/run_killerkoala_boot_welcome.py --mode koalabyte_lab --no-tts >/dev/null
  PYTHONPATH=pi-companion python3 scripts/run_boomerang.py <<< $'quit' >/dev/null || true
  PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py manifest
fi

echo
echo "KoalaByte Blue flash/install helper complete."
