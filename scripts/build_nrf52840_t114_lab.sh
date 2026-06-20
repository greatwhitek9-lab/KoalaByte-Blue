#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

APP_DIR="${APP_DIR:-firmware/nrf52840-dongle-ear-tag-tx-lab}"
BUILD_DIR="${BUILD_DIR:-build/nrf52840-t114-lab}"
T114_BOARD="${T114_BOARD:-}"
T114_BOARD_CANDIDATES=(
  heltec_t114_nrf52840
  heltec_mesh_node_t114_nrf52840
  mesh_node_t114_nrf52840
  t114_nrf52840
)

STRICT_NRF_TOOLS="${STRICT_NRF_TOOLS:-1}" bash scripts/setup_nrf_tools.sh --west-only
STRICT_NCS_TOOLCHAIN="${STRICT_NCS_TOOLCHAIN:-1}" bash scripts/setup_nrf_connect_sdk_toolchain.sh
if [[ -f "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh" ]]; then
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/logs/nrf_connect_sdk_env.sh"
fi

if [[ ! -f "${APP_DIR}/CMakeLists.txt" || ! -f "${APP_DIR}/prj.conf" || ! -f "${APP_DIR}/src/main.c" ]]; then
  echo "Missing KoalaByte Lab source files under ${APP_DIR}." >&2
  exit 1
fi

find_board_dir() {
  local candidate="$1"
  local roots=()
  if [[ -n "${ZEPHYR_BASE:-}" ]]; then
    roots+=("${ZEPHYR_BASE}")
  fi
  if [[ -n "${NCS_WORKSPACE:-}" ]]; then
    roots+=("${NCS_WORKSPACE}")
  fi
  roots+=("${REPO_ROOT}")

  local root
  for root in "${roots[@]}"; do
    [[ -d "${root}" ]] || continue
    if find "${root}" -path "*/boards/*/${candidate}" -type d -print -quit 2>/dev/null | grep -q .; then
      return 0
    fi
    if find "${root}" -path "*/boards/*/${candidate}.yaml" -type f -print -quit 2>/dev/null | grep -q .; then
      return 0
    fi
  done
  return 1
}

if [[ -z "${T114_BOARD}" ]]; then
  for candidate in "${T114_BOARD_CANDIDATES[@]}"; do
    if find_board_dir "${candidate}"; then
      T114_BOARD="${candidate}"
      break
    fi
  done
fi

if [[ -z "${T114_BOARD}" ]]; then
  cat >&2 <<'EOF'
T114_BOARD is not set, and no known T114 Zephyr board definition was found in this workspace.

This helper intentionally refuses to build for a guessed board target.
Confirm the exact Zephyr/NCS board name for the Heltec Mesh Node T114 V2 support package, then run:

  T114_BOARD=<confirmed_zephyr_board_target> bash scripts/build_nrf52840_t114_lab.sh

The Nordic nRF52840 Dongle path remains unchanged:

  bash scripts/build_nrf52840_dongle_lab.sh
EOF
  exit 2
fi

echo "Building KoalaByte Lab for alternate Heltec Mesh Node T114 V2 nRF52840 target"
echo "Repository root: ${REPO_ROOT}"
echo "Board: ${T114_BOARD}"
echo "App: ${APP_DIR}"
echo "Build dir: ${BUILD_DIR}"
west build -b "${T114_BOARD}" "${APP_DIR}" -d "${BUILD_DIR}"

echo "T114 alternate KoalaByte Lab firmware build complete: ${BUILD_DIR}"
echo "Primary artifacts normally appear under: ${BUILD_DIR}/zephyr/"
echo "Next step after confirming bootloader/flash method: T114_FLASH_CMD='<command>' bash scripts/flash_nrf52840_t114_lab.sh"
