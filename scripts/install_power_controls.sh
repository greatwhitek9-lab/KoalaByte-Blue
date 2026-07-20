#!/usr/bin/env bash
set -euo pipefail

CHECK_ONLY=0
SERVICE_USER="${KOALABYTE_SERVICE_USER:-${SUDO_USER:-${USER:-pi}}}"
SUDOERS_PATH="${KOALABYTE_POWER_SUDOERS_PATH:-/etc/sudoers.d/90-koalabyte-power-controls}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only|--dry-run) CHECK_ONLY=1 ;;
    -h|--help)
      cat <<'EOF'
Install narrowly scoped KoalaByte K7/K8 power permissions.

The generated sudoers rule permits only:
  - shutdown -h now
  - reboot

It does not grant general passwordless sudo access.
EOF
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

id "${SERVICE_USER}" >/dev/null 2>&1 || {
  echo "Service user does not exist: ${SERVICE_USER}" >&2
  exit 1
}

shutdown_bin="$(command -v shutdown || true)"
reboot_bin="$(command -v reboot || true)"

if [[ -z "${shutdown_bin}" || -z "${reboot_bin}" ]]; then
  echo "shutdown and reboot commands are required." >&2
  exit 1
fi

rule="${SERVICE_USER} ALL=(root) NOPASSWD: ${shutdown_bin} -h now, ${reboot_bin}"

tmp="$(mktemp)"
trap 'rm -f "${tmp}"' EXIT
printf '%s\n' "${rule}" > "${tmp}"
chmod 0440 "${tmp}"

if command -v visudo >/dev/null 2>&1; then
  visudo -cf "${tmp}"
fi

if [[ "${CHECK_ONLY}" == "1" ]]; then
  echo "KoalaByte power-control sudoers rule is valid:"
  echo "${rule}"
  exit 0
fi

if [[ "${EUID}" -eq 0 ]]; then
  sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then
  sudo_cmd=(sudo)
else
  echo "Root or sudo is required to install ${SUDOERS_PATH}." >&2
  exit 1
fi

"${sudo_cmd[@]}" install -o root -g root -m 0440 "${tmp}" "${SUDOERS_PATH}"
if command -v visudo >/dev/null 2>&1; then
  "${sudo_cmd[@]}" visudo -cf "${SUDOERS_PATH}"
fi

echo "Installed restricted K7/K8 power permissions for ${SERVICE_USER}: ${SUDOERS_PATH}"
