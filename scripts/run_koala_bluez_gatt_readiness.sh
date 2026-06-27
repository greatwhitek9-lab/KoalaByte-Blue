#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Gumnut GATT Gatechecker is owned-device/readiness focused. This helper records
# whether the deprecated BlueZ gatttool command is available before writing the
# readiness artifact. It does not make target-specific checks less strict.
INSTALL_GATTTOOL="${INSTALL_GATTTOOL:-auto}" STRICT_GATTTOOL="${STRICT_GATTTOOL:-0}" \
  bash "${REPO_ROOT}/scripts/setup_bluez_gatttool.sh" --check-only >/dev/null || true

PYTHONPATH="${REPO_ROOT}/pi-companion" python3 "${REPO_ROOT}/scripts/run_koala_bluez.py" gatt-readiness "$@"
