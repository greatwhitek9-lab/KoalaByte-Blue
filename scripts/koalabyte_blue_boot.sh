#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/pi-companion/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi
PREBOOT_SELECTOR="${PREBOOT_SELECTOR:-1}"
PREBOOT_TIMEOUT="${PREBOOT_TIMEOUT:-8}"
PREBOOT_DEFAULT_MODE="${PREBOOT_DEFAULT_MODE:-current}"
PREBOOT_MODE="${PREBOOT_MODE:-}"
PREBOOT_NO_APPLY="${PREBOOT_NO_APPLY:-0}"
KILLERKOALA_BOOT_WELCOME="${KILLERKOALA_BOOT_WELCOME:-1}"
BOOT_SPLASH="${BOOT_SPLASH:-1}"
MENU_GRAPHICAL="${MENU_GRAPHICAL:-1}"
MENU_WINDOWED="${MENU_WINDOWED:-0}"
MENU_NO_TERMINAL_FALLBACK="${MENU_NO_TERMINAL_FALLBACK:-1}"
BOOT_SPLASH_DURATION="${BOOT_SPLASH_DURATION:-3}"
KOALABYTE_TTS="${KOALABYTE_TTS:-1}"

cd "${REPO_ROOT}"
export PYTHONPATH="${REPO_ROOT}/pi-companion${PYTHONPATH:+:${PYTHONPATH}}"
export KOALABYTE_TTS
export MENU_NO_TERMINAL_FALLBACK

if [[ -z "${DISPLAY:-}" ]]; then
  export SDL_VIDEODRIVER="${SDL_VIDEODRIVER:-kmsdrm}"
  export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/koalabyte-runtime-$(id -u)}"
  mkdir -p "${XDG_RUNTIME_DIR}"
  chmod 700 "${XDG_RUNTIME_DIR}" || true
fi

echo "== KoalaByte Blue boot launcher =="
echo "Repo: ${REPO_ROOT}"
echo "Python: ${PYTHON_BIN}"
echo "Interface: wrapped graphical jungle UI"
echo "Terminal fallback: ${MENU_NO_TERMINAL_FALLBACK} means disabled"

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

if [[ "${KILLERKOALA_BOOT_WELCOME}" == "1" ]]; then
  echo "== KillerKoala mode-aware boot welcome =="
  "${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_killerkoala_boot_welcome.py"
fi

if [[ "${BOOT_SPLASH}" == "1" ]]; then
  echo "== KoalaByte Blue boot splash =="
  "${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_boot_splash.py" --duration "${BOOT_SPLASH_DURATION}"
fi

echo "== KoalaByte Blue wrapped menu interface =="
if [[ "${MENU_GRAPHICAL}" == "1" ]]; then
  MENU_ARGS=("${REPO_ROOT}/scripts/run_menu_screen.py" --graphical --no-terminal-fallback)
  if [[ "${MENU_WINDOWED}" == "1" ]]; then
    MENU_ARGS+=(--windowed)
  fi
  exec "${PYTHON_BIN}" "${MENU_ARGS[@]}"
fi

echo "MENU_GRAPHICAL=${MENU_GRAPHICAL}; terminal mode is for explicit debugging only."
exec "${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_menu_screen.py" --terminal
