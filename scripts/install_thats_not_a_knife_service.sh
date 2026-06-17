#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="koalabyte-thats-not-a-knife.service"
UNIT_TEMPLATE="${REPO_ROOT}/systemd/${SERVICE_NAME}.in"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/pi-companion/.venv/bin/python}"
SERVICE_USER="${KOALABYTE_SERVICE_USER:-${SUDO_USER:-$(id -un)}}"
INTERVAL_SECONDS="${THATS_NOT_A_KNIFE_INTERVAL_SECONDS:-10}"
THRESHOLD="${THATS_NOT_A_KNIFE_THRESHOLD:-5}"
XP_COOLDOWN_SECONDS="${THATS_NOT_A_KNIFE_XP_COOLDOWN_SECONDS:-300}"
ENABLE_NOW="${THATS_NOT_A_KNIFE_ENABLE_NOW:-1}"
STRICT_SERVICE_INSTALL="${STRICT_THATS_NOT_A_KNIFE_SERVICE:-0}"

if [[ ! -f "${UNIT_TEMPLATE}" ]]; then
  echo "Missing systemd unit template: ${UNIT_TEMPLATE}" >&2
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl is not available; skipping ${SERVICE_NAME} install." >&2
  if [[ "${STRICT_SERVICE_INSTALL}" == "1" ]]; then
    exit 1
  fi
  exit 0
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python venv not found at ${PYTHON_BIN}; run scripts/install_pi.sh first or set PYTHON_BIN." >&2
  if [[ "${STRICT_SERVICE_INSTALL}" == "1" ]]; then
    exit 1
  fi
  exit 0
fi

TMP_UNIT="$(mktemp)"
python3 - "${UNIT_TEMPLATE}" "${TMP_UNIT}" <<'PY'
from pathlib import Path
import os
import sys

template = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = {
    "{{SERVICE_USER}}": os.environ["SERVICE_USER"],
    "{{REPO_ROOT}}": os.environ["REPO_ROOT"],
    "{{PYTHON_BIN}}": os.environ["PYTHON_BIN"],
    "{{INTERVAL_SECONDS}}": os.environ["INTERVAL_SECONDS"],
    "{{THRESHOLD}}": os.environ["THRESHOLD"],
    "{{XP_COOLDOWN_SECONDS}}": os.environ["XP_COOLDOWN_SECONDS"],
}
for key, value in replacements.items():
    template = template.replace(key, value)
Path(sys.argv[2]).write_text(template, encoding="utf-8")
PY

if [[ "${EUID}" -eq 0 ]]; then
  SUDO=()
else
  SUDO=(sudo)
fi

"${SUDO[@]}" install -m 0644 "${TMP_UNIT}" "${UNIT_PATH}"
rm -f "${TMP_UNIT}"
"${SUDO[@]}" systemctl daemon-reload

if [[ "${ENABLE_NOW}" == "1" ]]; then
  "${SUDO[@]}" systemctl enable --now "${SERVICE_NAME}"
else
  "${SUDO[@]}" systemctl enable "${SERVICE_NAME}"
fi

echo "Installed ${SERVICE_NAME}"
echo "Status: systemctl status ${SERVICE_NAME}"
echo "Logs:   journalctl -u ${SERVICE_NAME} -f"
