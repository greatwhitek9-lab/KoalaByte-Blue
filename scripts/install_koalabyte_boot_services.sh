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
    --check-only)
      CHECK_ONLY=1
      ;;
    -h|--help)
      cat <<'EOF'
Install KoalaByte Blue boot services.

Usage:
  bash scripts/install_koalabyte_boot_services.sh
  bash scripts/install_koalabyte_boot_services.sh --check-only

Services:
  koalabyte-menu.service      Starts scripts/koalabyte_blue_boot.sh automatically on boot.
  koalabyte-menu-sync.service Keeps menu/display state synced.
  koalabyte-doctor.service    Runs field diagnostics.
EOF
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

case "${INSTALL_BOOT_SERVICES}" in
  0|false|False|no|NO|skip|SKIP)
    echo "Skipping KoalaByte boot services by request."
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES)
    ;;
  *) echo "Unknown INSTALL_BOOT_SERVICES=${INSTALL_BOOT_SERVICES}" >&2; exit 2 ;;
esac

for svc in koalabyte-menu.service koalabyte-menu-sync.service koalabyte-doctor.service; do
  if [[ ! -f "${REPO_ROOT}/systemd/${svc}" ]]; then
    echo "Missing service template: systemd/${svc}" >&2
    exit 1
  fi
  bash -n <(grep -v '^\[' "${REPO_ROOT}/systemd/${svc}" | grep '^ExecStart=' | sed 's/^ExecStart=//' || true) >/dev/null 2>&1 || true
done

menu_service_text="$(cat "${REPO_ROOT}/systemd/koalabyte-menu.service")"
for marker in \
  "ExecStart=/usr/bin/bash /opt/KoalaByte-Blue/scripts/koalabyte_blue_boot.sh" \
  "WantedBy=multi-user.target" \
  "Restart=always" \
  "Environment=PYTHON_BIN=/opt/KoalaByte-Blue/pi-companion/.venv/bin/python"; do
  if [[ "${menu_service_text}" != *"${marker}"* ]]; then
    echo "koalabyte-menu.service missing boot autostart marker: ${marker}" >&2
    exit 1
  fi
done

if [[ "${CHECK_ONLY}" == "1" ]]; then
  echo "KoalaByte boot service templates are present and koalabyte_blue_boot.sh is configured for autostart."
  exit 0
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl not available; boot services cannot be installed on this OS." >&2
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

if [[ "${REPO_ROOT}" != "${INSTALL_ROOT}" ]]; then
  "${sudo_cmd[@]}" mkdir -p "$(dirname "${INSTALL_ROOT}")"
  if [[ ! -e "${INSTALL_ROOT}" ]]; then
    "${sudo_cmd[@]}" ln -s "${REPO_ROOT}" "${INSTALL_ROOT}" || true
  fi
fi

for svc in koalabyte-menu.service koalabyte-menu-sync.service koalabyte-doctor.service; do
  tmp="/tmp/${svc}"
  sed -e "s#WorkingDirectory=/opt/KoalaByte-Blue#WorkingDirectory=${INSTALL_ROOT}#g" \
      -e "s#/opt/KoalaByte-Blue#${INSTALL_ROOT}#g" \
      -e "s#User=pi#User=${SERVICE_USER}#g" \
      -e "s#Group=pi#Group=${SERVICE_GROUP}#g" \
      "${REPO_ROOT}/systemd/${svc}" > "${tmp}"
  "${sudo_cmd[@]}" install -m 0644 "${tmp}" "/etc/systemd/system/${svc}"
done

"${sudo_cmd[@]}" systemctl daemon-reload
"${sudo_cmd[@]}" systemctl enable koalabyte-menu.service koalabyte-menu-sync.service koalabyte-doctor.service

if "${sudo_cmd[@]}" systemctl is-enabled --quiet koalabyte-menu.service; then
  echo "KoalaByte boot launcher enabled: scripts/koalabyte_blue_boot.sh will run automatically on the next boot."
else
  echo "koalabyte-menu.service was installed but is not enabled." >&2
  [[ "${STRICT_BOOT_SERVICES}" == "1" ]] && exit 1
fi

echo "Installed KoalaByte boot services. Reboot to auto-start the KoalaByte Blue menu, or start now with: sudo systemctl start koalabyte-menu.service"
