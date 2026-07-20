#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_BOOT_SERVICES="${INSTALL_BOOT_SERVICES:-auto}"
STRICT_BOOT_SERVICES="${STRICT_BOOT_SERVICES:-0}"
CHECK_ONLY=0
SERVICE_USER="${KOALABYTE_SERVICE_USER:-${SUDO_USER:-${USER:-pi}}}"
SERVICE_GROUP="${KOALABYTE_SERVICE_GROUP:-${SERVICE_USER}}"
INSTALL_ROOT="${KOALABYTE_SERVICE_ROOT:-/opt/KoalaByte-Blue}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) CHECK_ONLY=1 ;;
    -h|--help)
      cat <<'EOF'
Install KoalaByte Blue Raspberry Pi boot services.

Services:
  koalabyte-menu.service      Headless K1-K8/menu/action/display-sync controller
  koalabyte-menu-sync.service Display-state synchronization support
  koalabyte-doctor.service    Field diagnostics
EOF
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

case "${INSTALL_BOOT_SERVICES}" in
  0|false|False|no|NO|skip|SKIP) echo "Skipping KoalaByte boot services by request."; exit 0 ;;
  auto|AUTO|1|true|True|yes|YES) ;;
  *) echo "Unknown INSTALL_BOOT_SERVICES=${INSTALL_BOOT_SERVICES}" >&2; exit 2 ;;
esac

for svc in koalabyte-menu.service koalabyte-menu-sync.service koalabyte-doctor.service; do
  [[ -f "${REPO_ROOT}/systemd/${svc}" ]] || { echo "Missing service template: systemd/${svc}" >&2; exit 1; }
done

menu_service_text="$(cat "${REPO_ROOT}/systemd/koalabyte-menu.service")"
for marker in \
  "scripts/run_headless_menu.py" \
  "WantedBy=multi-user.target" \
  "Restart=always" \
  "Environment=PYTHON_BIN=/opt/KoalaByte-Blue/pi-companion/.venv/bin/python"; do
  [[ "${menu_service_text}" == *"${marker}"* ]] || { echo "koalabyte-menu.service missing marker: ${marker}" >&2; exit 1; }
done

if [[ "${CHECK_ONLY}" == "1" ]]; then
  bash -n scripts/install_koalabyte_boot_services.sh
  python3 -m py_compile scripts/run_headless_menu.py
  echo "KoalaByte headless boot service templates are ready."
  exit 0
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl not available; boot services cannot be installed." >&2
  [[ "${STRICT_BOOT_SERVICES}" == "1" ]] && exit 1
  exit 0
fi

if [[ "${EUID}" -eq 0 ]]; then
  sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then
  sudo_cmd=(sudo)
else
  echo "Root or sudo is required to install systemd services." >&2
  [[ "${STRICT_BOOT_SERVICES}" == "1" ]] && exit 1
  exit 0
fi

if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
  echo "Service user does not exist: ${SERVICE_USER}" >&2
  exit 1
fi

if [[ "${REPO_ROOT}" != "${INSTALL_ROOT}" ]]; then
  "${sudo_cmd[@]}" mkdir -p "$(dirname "${INSTALL_ROOT}")"
  if [[ -L "${INSTALL_ROOT}" ]]; then
    current_target="$(readlink -f "${INSTALL_ROOT}" || true)"
    if [[ "${current_target}" != "${REPO_ROOT}" ]]; then
      "${sudo_cmd[@]}" rm -f "${INSTALL_ROOT}"
      "${sudo_cmd[@]}" ln -s "${REPO_ROOT}" "${INSTALL_ROOT}"
    fi
  elif [[ ! -e "${INSTALL_ROOT}" ]]; then
    "${sudo_cmd[@]}" ln -s "${REPO_ROOT}" "${INSTALL_ROOT}"
  fi
fi

for svc in koalabyte-menu.service koalabyte-menu-sync.service koalabyte-doctor.service; do
  tmp="$(mktemp)"
  sed -e "s#WorkingDirectory=/opt/KoalaByte-Blue#WorkingDirectory=${INSTALL_ROOT}#g" \
      -e "s#/opt/KoalaByte-Blue#${INSTALL_ROOT}#g" \
      -e "s#User=pi#User=${SERVICE_USER}#g" \
      -e "s#Group=pi#Group=${SERVICE_GROUP}#g" \
      "${REPO_ROOT}/systemd/${svc}" > "${tmp}"
  "${sudo_cmd[@]}" install -m 0644 "${tmp}" "/etc/systemd/system/${svc}"
  rm -f "${tmp}"
done

"${sudo_cmd[@]}" systemctl daemon-reload
"${sudo_cmd[@]}" systemctl enable koalabyte-menu.service koalabyte-menu-sync.service koalabyte-doctor.service

echo "Installed KoalaByte headless menu, display sync, and doctor boot services for ${SERVICE_USER}."
