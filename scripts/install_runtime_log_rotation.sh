#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_USER="${KOALABYTE_SERVICE_USER:-${SUDO_USER:-${USER:-pi}}}"
SERVICE_GROUP="${KOALABYTE_SERVICE_GROUP:-}"
ROTATE_SIZE="${KOALABYTE_LOG_ROTATE_SIZE:-8M}"
ROTATE_COUNT="${KOALABYTE_LOG_ROTATE_COUNT:-3}"
CONFIG_PATH="${KOALABYTE_LOGROTATE_CONFIG:-/etc/logrotate.d/koalabyte-blue}"
CHECK_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) CHECK_ONLY=1 ;;
    -h|--help)
      echo "Install bounded rotation for KoalaByte .jsonl, .log, and .err files."
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

[[ "${ROTATE_COUNT}" =~ ^[1-9][0-9]*$ ]] || {
  echo "KOALABYTE_LOG_ROTATE_COUNT must be a positive integer." >&2
  exit 2
}
id "${SERVICE_USER}" >/dev/null 2>&1 || {
  echo "Service user does not exist: ${SERVICE_USER}" >&2
  exit 1
}
[[ -n "${SERVICE_GROUP}" ]] || SERVICE_GROUP="$(id -gn "${SERVICE_USER}")"

if [[ "${CHECK_ONLY}" == "1" ]]; then
  bash -n "$0"
  echo "Runtime log rotation contract ready for ${SERVICE_USER}:${SERVICE_GROUP}."
  exit 0
fi

if [[ "${EUID}" -eq 0 ]]; then
  sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then
  sudo_cmd=(sudo)
else
  echo "Root or sudo is required to install runtime log rotation." >&2
  exit 1
fi

apt_noninteractive() {
  if [[ "${EUID}" -eq 0 ]]; then
    env DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Retries=3 "$@"
  else
    sudo env DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Retries=3 "$@"
  fi
}

if ! command -v logrotate >/dev/null 2>&1; then
  apt_noninteractive update
  apt_noninteractive install -y logrotate
fi

tmp="$(mktemp)"
cat >"${tmp}" <<EOF
${ROOT}/logs/*/*.jsonl ${ROOT}/logs/*/*.log ${ROOT}/logs/*/*.err ${ROOT}/logs/*.jsonl ${ROOT}/logs/*.log ${ROOT}/logs/*.err {
    su ${SERVICE_USER} ${SERVICE_GROUP}
    size ${ROTATE_SIZE}
    rotate ${ROTATE_COUNT}
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF

"${sudo_cmd[@]}" install -m 0644 "${tmp}" "${CONFIG_PATH}"
rm -f "${tmp}"
"${sudo_cmd[@]}" logrotate --debug "${CONFIG_PATH}" >/dev/null

echo "Installed KoalaByte runtime log rotation: ${ROTATE_SIZE}, ${ROTATE_COUNT} backups."
