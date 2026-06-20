#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PREBOOT_SELECTOR="${PREBOOT_SELECTOR:-1}"
PREBOOT_TIMEOUT="${PREBOOT_TIMEOUT:-8}"
PREBOOT_DEFAULT_MODE="${PREBOOT_DEFAULT_MODE:-current}"
PREBOOT_MODE="${PREBOOT_MODE:-}"
PREBOOT_NO_APPLY="${PREBOOT_NO_APPLY:-0}"
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

if [[ "${PREBOOT_SELECTOR}" == "1" ]]; then
  echo "== KoalaByte Blue pre-boot dongle mode selector =="
  PREBOOT_ARGS=("${REPO_ROOT}/scripts/run_preboot_mode_select.py" --timeout "${PREBOOT_TIMEOUT}" --default-mode "${PREBOOT_DEFAULT_MODE}")
  if [[ -n "${PREBOOT_MODE}" ]]; then
    PREBOOT_ARGS+=(--mode "${PREBOOT_MODE}")
  fi
  if [[ "${PREBOOT_NO_APPLY}" == "1" ]]; then
    PREBOOT_ARGS+=(--no-apply)
  fi
  "${PYTHON_BIN}" "${PREBOOT_ARGS[@]}"
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
