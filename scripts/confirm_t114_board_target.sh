#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

T114_BOARD="${T114_BOARD:-}"
LOG_DIR="${LOG_DIR:-logs}"
OUT_JSON="${OUT_JSON:-${LOG_DIR}/t114_board_target.json}"
ALLOW_T114_BOARD_SMOKE_FALLBACK="${ALLOW_T114_BOARD_SMOKE_FALLBACK:-0}"
T114_BOARD_SMOKE_FALLBACK="${T114_BOARD_SMOKE_FALLBACK:-}"

T114_BOARD_CANDIDATES=(
  heltec_t114_v2/nrf52840
  heltec_t114_v2/nrf52840/uf2
  heltec_t114_v2
  heltec_mesh_node_t114_nrf52840
  heltec_t114_nrf52840
  mesh_node_t114_nrf52840
  t114_nrf52840
)

T114_BOARD_SMOKE_FALLBACK_CANDIDATES=(
  nrf52840dk/nrf52840
  nrf52840dk_nrf52840
)

mkdir -p "${LOG_DIR}"

candidate_board_dir() {
  local candidate="$1"
  printf '%s\n' "${candidate%%/*}"
}

find_board_dir() {
  local candidate="$1"
  local board_dir
  board_dir="$(candidate_board_dir "${candidate}")"
  local legacy_yaml="${candidate//\//_}"
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
    if find "${root}" -path "*/boards/*/${board_dir}" -type d -print -quit 2>/dev/null | grep -q .; then
      return 0
    fi
    if find "${root}" -path "*/boards/*/${legacy_yaml}.yaml" -type f -print -quit 2>/dev/null | grep -q .; then
      return 0
    fi
    if find "${root}" -path "*/boards/*/${board_dir}.yaml" -type f -print -quit 2>/dev/null | grep -q .; then
      return 0
    fi
  done
  return 1
}

emit_json_array() {
  local sep=""
  printf '['
  local candidate
  for candidate in "$@"; do
    printf '%s"%s"' "${sep}" "${candidate}"
    sep=', '
  done
  printf ']'
}

resolve_smoke_fallback() {
  if [[ -n "${T114_BOARD_SMOKE_FALLBACK}" ]] && find_board_dir "${T114_BOARD_SMOKE_FALLBACK}"; then
    printf '%s\n' "${T114_BOARD_SMOKE_FALLBACK}"
    return 0
  fi
  local candidate
  for candidate in "${T114_BOARD_SMOKE_FALLBACK_CANDIDATES[@]}"; do
    if find_board_dir "${candidate}"; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

FALLBACK_USED="false"
REQUESTED_BOARD="${T114_BOARD}"

if [[ -z "${T114_BOARD}" ]]; then
  for candidate in "${T114_BOARD_CANDIDATES[@]}"; do
    if find_board_dir "${candidate}"; then
      T114_BOARD="${candidate}"
      REQUESTED_BOARD="${candidate}"
      break
    fi
  done
  if [[ -z "${T114_BOARD}" && "${ALLOW_T114_BOARD_SMOKE_FALLBACK}" == "1" ]]; then
    if T114_BOARD="$(resolve_smoke_fallback)"; then
      REQUESTED_BOARD="heltec_t114_v2/nrf52840"
      FALLBACK_USED="true"
      echo "No Heltec T114 board definition found; using CI smoke-test fallback board: ${T114_BOARD}" >&2
    fi
  fi
fi

if [[ -z "${T114_BOARD}" ]]; then
  cat >"${OUT_JSON}" <<JSON
{
  "status": "not_found",
  "board": null,
  "message": "No known Heltec T114 V2 Zephyr board definition was found. Install the board support package or set T114_BOARD explicitly.",
  "official_target": "heltec_t114_v2/nrf52840",
  "uf2_target": "heltec_t114_v2/nrf52840/uf2",
  "allow_smoke_fallback": "${ALLOW_T114_BOARD_SMOKE_FALLBACK}",
  "smoke_fallback_candidates": $(emit_json_array "${T114_BOARD_SMOKE_FALLBACK_CANDIDATES[@]}"),
  "candidates_checked": $(emit_json_array "${T114_BOARD_CANDIDATES[@]}")
}
JSON
  echo "T114_BOARD is not set, and no known Heltec T114 V2 Zephyr board definition was found." >&2
  echo "Try: T114_BOARD=heltec_t114_v2/nrf52840" >&2
  exit 2
fi

if ! find_board_dir "${T114_BOARD}"; then
  if [[ "${ALLOW_T114_BOARD_SMOKE_FALLBACK}" == "1" ]]; then
    if fallback_board="$(resolve_smoke_fallback)"; then
      echo "T114_BOARD=${T114_BOARD} was set, but no matching board definition was found." >&2
      echo "Using CI smoke-test fallback board: ${fallback_board}" >&2
      REQUESTED_BOARD="${T114_BOARD}"
      T114_BOARD="${fallback_board}"
      FALLBACK_USED="true"
    else
      echo "T114_BOARD=${T114_BOARD} was set, but no matching board definition or smoke fallback board was found." >&2
      exit 2
    fi
  else
    echo "T114_BOARD=${T114_BOARD} was set, but no matching board definition was found." >&2
    echo "For Heltec Tracker V2 T114 / Mesh Node T114 V2, try: T114_BOARD=heltec_t114_v2/nrf52840" >&2
    exit 2
  fi
fi

cat >"${OUT_JSON}" <<JSON
{
  "status": "confirmed",
  "board": "${T114_BOARD}",
  "requested_board": "${REQUESTED_BOARD}",
  "smoke_fallback_used": ${FALLBACK_USED},
  "message": "T114 Zephyr board target confirmed in the current workspace.",
  "official_target": "heltec_t114_v2/nrf52840",
  "uf2_target": "heltec_t114_v2/nrf52840/uf2"
}
JSON

if [[ "${FALLBACK_USED}" == "true" ]]; then
  echo "Confirmed T114 Zephyr board target: ${T114_BOARD}"
  echo "WARNING: using smoke-test fallback board for CI/toolchain validation only; do not flash this artifact to the Heltec T114." >&2
else
  echo "Confirmed T114 Zephyr board target: ${T114_BOARD}"
fi
echo "Wrote: ${OUT_JSON}"
