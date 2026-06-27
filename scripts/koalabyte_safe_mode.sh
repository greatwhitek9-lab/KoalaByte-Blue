#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/pi-companion/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN=python3
fi
cd "${REPO_ROOT}"
mkdir -p logs/safe_mode logs/menu_sync

cat > logs/safe_mode/current_safe_mode.json <<JSON
{
  "status": "KOALABYTE_SAFE_MODE_ACTIVE",
  "note": "Optional services disabled for recovery. Use B1/menu or terminal menu after fixing hardware.",
  "disabled_optional_paths": [
    "KOALABYTE_MENU_SYNC hardware serial sends",
    "optional CAN strict failure",
    "strict Ollama failure",
    "strict display sync hardware port failure"
  ],
  "updated_at": $(date +%s)
}
JSON

export KOALABYTE_MENU_SYNC=0
export STRICT_INNOMAKER_CAN=0
export STRICT_KILLERKOALA_OLLAMA=0
export STRICT_MENU_DISPLAY_SYNC=0
export STRICT_FACE_MOUTH_SYNC=0
export STRICT_T114_STATUS_DASHBOARD=0
export INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE=0
export INSTALL_BLE_NODE_MANAGER_SERVICE=0

if [[ "${1:-}" == "--doctor" ]]; then
  bash scripts/koalabyte_doctor.sh --quick || true
fi

if [[ "${1:-}" == "--terminal" || "${2:-}" == "--terminal" ]]; then
  PYTHONPATH="${REPO_ROOT}/pi-companion:${REPO_ROOT}:${PYTHONPATH:-}" "${PYTHON_BIN}" scripts/run_menu_screen.py
else
  echo "KoalaByte safe mode is active."
  echo "Run terminal menu: bash scripts/koalabyte_safe_mode.sh --terminal"
  echo "Run quick doctor:  bash scripts/koalabyte_safe_mode.sh --doctor"
fi
