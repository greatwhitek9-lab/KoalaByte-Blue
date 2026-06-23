#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
T114_STARTUP_SELECTOR="${T114_STARTUP_SELECTOR:-1}"
T114_STARTUP_TIMEOUT="${T114_STARTUP_TIMEOUT:-10}"
T114_STARTUP_DEFAULT_MODE="${T114_STARTUP_DEFAULT_MODE:-lab}"
T114_STARTUP_MODE="${T114_STARTUP_MODE:-}"
T114_STARTUP_NO_APPLY="${T114_STARTUP_NO_APPLY:-0}"
T114_STARTUP_STATE="${T114_STARTUP_STATE:-logs/t114_profiles/startup_selection.json}"
KILLERKOALA_BOOT_WELCOME="${KILLERKOALA_BOOT_WELCOME:-1}"
BOOT_SPLASH="${BOOT_SPLASH:-1}"
MENU_GRAPHICAL="${MENU_GRAPHICAL:-1}"
MENU_WINDOWED="${MENU_WINDOWED:-0}"
BOOT_SPLASH_DURATION="${BOOT_SPLASH_DURATION:-3}"
KOALABYTE_TTS="${KOALABYTE_TTS:-1}"

cd "${REPO_ROOT}"
export PYTHONPATH="${REPO_ROOT}/pi-companion${PYTHONPATH:+:${PYTHONPATH}}"
export KOALABYTE_TTS

echo "== KillerKoala spoken alerts =="
if [[ "${KOALABYTE_TTS}" == "1" ]]; then
  echo "Spoken alerts are ON by default. Set KOALABYTE_TTS=0 to mute startup/menu speech."
else
  echo "Spoken alerts are muted by KOALABYTE_TTS=${KOALABYTE_TTS}."
fi

apply_selected_t114_profile() {
  local state_file="${T114_STARTUP_STATE}"
  if [[ ! -f "${state_file}" ]]; then
    echo "T114 startup selector did not create ${state_file}; skipping T114 profile apply." >&2
    return 0
  fi
  local selected_mode
  selected_mode="$(${PYTHON_BIN} - <<PY
import json
from pathlib import Path
path = Path("${state_file}")
data = json.loads(path.read_text())
print(data.get("selected_mode", ""))
PY
)"
  case "${selected_mode}" in
    heltec_lab)
      echo "== Activating Heltec Lab / mouth / BLE / GNSS profile =="
      if [[ "${T114_STARTUP_NO_APPLY}" == "1" ]]; then
        echo "T114_STARTUP_NO_APPLY=1; recorded Lab selection only."
      else
        KOALABYTE_HELTEC_USB_PORT="${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-/dev/ttyACM0}}" \
        HELTEC_PORT="${HELTEC_PORT:-${KOALABYTE_HELTEC_USB_PORT:-/dev/ttyACM0}}" \
        NO_MONITOR="${NO_MONITOR:-1}" \
          bash scripts/flash_heltec_mouth.sh
      fi
      ;;
    koala_konnect_t114)
      echo "== Activating Koala Konnect T114 profile =="
      if [[ "${T114_STARTUP_NO_APPLY}" == "1" ]]; then
        echo "T114_STARTUP_NO_APPLY=1; recorded Koala Konnect T114 selection only."
      else
        KOALABYTE_HELTEC_USB_PORT="${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-/dev/ttyACM0}}" \
        HELTEC_PORT="${HELTEC_PORT:-${KOALABYTE_HELTEC_USB_PORT:-/dev/ttyACM0}}" \
        T114_BOARD="${T114_BOARD:-heltec_t114_v2/nrf52840}" \
          bash scripts/flash_koala_konnect_t114.sh
      fi
      ;;
    *)
      echo "Unknown T114 startup profile '${selected_mode}'; leaving current T114 firmware untouched." >&2
      ;;
  esac
}

if [[ "${T114_STARTUP_SELECTOR}" == "1" ]]; then
  echo "== Heltec T114 startup profile selector =="
  SELECT_ARGS=("${REPO_ROOT}/scripts/select_t114_startup_mode.py" --timeout "${T114_STARTUP_TIMEOUT}" --default-mode "${T114_STARTUP_DEFAULT_MODE}" --state-path "${T114_STARTUP_STATE}")
  if [[ -n "${T114_STARTUP_MODE}" ]]; then
    SELECT_ARGS+=(--mode "${T114_STARTUP_MODE}")
  fi
  "${PYTHON_BIN}" "${SELECT_ARGS[@]}"
  apply_selected_t114_profile
fi

if [[ "${KILLERKOALA_BOOT_WELCOME}" == "1" ]]; then
  echo "== KillerKoala mode-aware boot welcome =="
  "${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_killerkoala_boot_welcome.py"
fi

if [[ "${BOOT_SPLASH}" == "1" ]]; then
  echo "== KoalaByte Blue boot splash =="
  "${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_boot_splash.py" --duration "${BOOT_SPLASH_DURATION}"
fi

echo "== KoalaByte Blue menu =="
if [[ "${MENU_GRAPHICAL}" == "1" ]]; then
  if [[ "${MENU_WINDOWED}" == "1" ]]; then
    "${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_menu_screen.py" --graphical --windowed
  else
    "${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_menu_screen.py" --graphical
  fi
else
  "${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_menu_screen.py"
fi
