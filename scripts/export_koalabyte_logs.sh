#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${KOALABYTE_LOG_EXPORT_DIR:-${REPO_ROOT}/exports}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${OUT_DIR}/koalabyte_logs_${STAMP}.zip"
mkdir -p "${OUT_DIR}"
cd "${REPO_ROOT}"

paths=(
  logs/one_shot
  logs/menu_sync
  logs/menu_actions
  logs/killerkoala
  logs/killerkoala_face
  logs/koala_bluez
  logs/can
  logs/anteater
  logs/preflight
  logs/doctor
  logs/safe_mode
  logs/gpio_buttons
  README.md
)

present=()
for path in "${paths[@]}"; do
  [[ -e "${path}" ]] && present+=("${path}")
done

if [[ "${#present[@]}" -eq 0 ]]; then
  echo "No KoalaByte logs found to export." >&2
  exit 1
fi

if command -v zip >/dev/null 2>&1; then
  zip -r "${OUT_FILE}" "${present[@]}" >/dev/null
else
  OUT_FILE="${OUT_DIR}/koalabyte_logs_${STAMP}.tar.gz"
  tar -czf "${OUT_FILE}" "${present[@]}"
fi

echo "KoalaByte log bundle written: ${OUT_FILE}"
