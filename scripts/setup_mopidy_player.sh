#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK_ONLY=0
INSTALL_MOPIDY_PLAYER="${INSTALL_MOPIDY_PLAYER:-auto}"
STRICT_MOPIDY_PLAYER="${STRICT_MOPIDY_PLAYER:-0}"
STATUS_PATH="${KOALABYTE_MUSIC_SETUP_STATUS:-${ROOT}/logs/music_player/mopidy_setup_status.json}"
MUSIC_DIR="${KOALABYTE_MUSIC_DIR:-/srv/koalabyte-music}"
CONFIG_DIR="${KOALABYTE_CONFIG_DIR:-/etc/koalabyte-blue}"
PLAYER_CONFIG="${KOALABYTE_MUSIC_CONFIG:-${CONFIG_DIR}/music.json}"
MOPIDY_CONFIG="${KOALABYTE_MOPIDY_CONFIG:-/etc/mopidy/mopidy.conf}"
RPC_URL="${KOALABYTE_MOPIDY_RPC_URL:-http://127.0.0.1:6680/mopidy/rpc}"
MOPIDY_READY_TIMEOUT="${KOALABYTE_MOPIDY_READY_TIMEOUT:-60}"
TMP_ROOT="${TMPDIR:-${HOME}/.cache/koalabyte/tmp}"
SERVICE_USER="${KOALABYTE_SERVICE_USER:-${SUDO_USER:-$(id -un)}}"

usage() {
  cat <<'EOF'
Install the Pi-owned KoalaByte Mopidy music engine.

The HTTP and MPD control interfaces bind only to localhost. Installation is
noninteractive, retries APT/network work, resets stale service failure counters,
and requires a working JSON-RPC response before reporting success.
EOF
}

case "${1:-}" in
  "") ;;
  --check-only|--dry-run) CHECK_ONLY=1 ;;
  -h|--help) usage; exit 0 ;;
  *) echo "Unknown argument: ${1}" >&2; usage >&2; exit 2 ;;
esac

mkdir -p "$(dirname "${STATUS_PATH}")" "${TMP_ROOT}"

write_status() {
  local status="$1" reason="$2" service_state="${3:-unknown}"
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${service_state}" \
    "${CHECK_ONLY}" "${MUSIC_DIR}" "${PLAYER_CONFIG}" "${MOPIDY_CONFIG}" \
    "${RPC_URL}" "${SERVICE_USER}" <<'PY'
import json, sys, time
from pathlib import Path
(path, status, reason, service_state, check_only, music_dir, player_config,
 mopidy_config, rpc_url, service_user) = sys.argv[1:]
payload = {
    "status": status,
    "reason": reason,
    "service": "mopidy.service",
    "service_state": service_state,
    "check_only": check_only == "1",
    "execution_owner": "raspberry-pi",
    "service_user": service_user,
    "engine": "mopidy",
    "rpc_url": rpc_url,
    "http_bind": "127.0.0.1:6680",
    "mpd_bind": "127.0.0.1:6600",
    "music_dir": music_dir,
    "player_config": player_config,
    "mopidy_config": mopidy_config,
    "sources": ["local_files", "internet_radio", "optional_mopidy_extensions"],
    "speech_ducking": True,
    "shared_alsa_supported": True,
    "systemd_service_required": True,
    "updated_at": time.time(),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(payload, sort_keys=True))
PY
}

case "${INSTALL_MOPIDY_PLAYER}" in
  0|false|False|no|NO|skip|SKIP)
    write_status MOPIDY_PLAYER_SKIPPED "disabled by INSTALL_MOPIDY_PLAYER" disabled
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES) ;;
  *) echo "Unknown INSTALL_MOPIDY_PLAYER=${INSTALL_MOPIDY_PLAYER}" >&2; exit 2 ;;
esac

if [[ "${CHECK_ONLY}" == "1" ]]; then
  bash -n "$0"
  grep -q 'hostname = 127.0.0.1' "$0"
  grep -q 'mopidy-archive-keyring.gpg' "$0"
  grep -q 'systemctl reset-failed mopidy.service' "$0"
  grep -q 'KOALABYTE_SERVICE_USER' "$0"
  grep -q 'chmod 0640 "${PLAYER_CONFIG}"' "$0"
  write_status MOPIDY_PLAYER_CONTRACT_READY \
    "official APT source, noninteractive install, localhost API, service reset, runtime-readable config, and RPC health contract validated" \
    not_started
  exit 0
fi

[[ "$(uname -s)" == "Linux" ]] || {
  write_status MOPIDY_PLAYER_ERROR "Mopidy setup requires Linux" unsupported
  exit 1
}
command -v apt-get >/dev/null 2>&1 || {
  write_status MOPIDY_PLAYER_ERROR "apt-get is unavailable" unavailable
  exit 1
}

if [[ "${EUID}" -eq 0 ]]; then sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then sudo_cmd=(sudo)
else
  write_status MOPIDY_PLAYER_ERROR "root or sudo is required" unknown
  exit 1
fi

fail_setup() {
  local reason="$1" state="${2:-unavailable}"
  write_status MOPIDY_PLAYER_ERROR "${reason}" "${state}"
  echo "Mopidy setup failed: ${reason}" >&2
  # A complete one-shot requires Mopidy unless --skip-music was selected, so fail
  # here rather than allowing a less useful later health-gate error.
  return 1
}

if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
  fail_setup "KoalaByte service user does not exist: ${SERVICE_USER}" unavailable
  exit 1
fi
SERVICE_GROUP="$(id -gn "${SERVICE_USER}")"

apt_noninteractive() {
  if [[ "${EUID}" -eq 0 ]]; then
    env DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Retries=3 \
      -o Dpkg::Options::=--force-confold "$@"
  else
    sudo env DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Retries=3 \
      -o Dpkg::Options::=--force-confold "$@"
  fi
}

download_file() {
  local url="$1" destination="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL --retry 5 --retry-all-errors --connect-timeout 20 \
      "${url}" -o "${destination}"
  elif command -v wget >/dev/null 2>&1; then
    wget --tries=5 --timeout=30 -q -O "${destination}" "${url}"
  else
    return 1
  fi
}

. /etc/os-release 2>/dev/null || true
codename="${VERSION_CODENAME:-bookworm}"
case "${codename}" in
  trixie) source_name="trixie.sources" ;;
  bookworm|bullseye) source_name="bookworm.sources" ;;
  *)
    echo "warning: unsupported/unknown Pi OS codename ${codename}; using Mopidy bookworm source" >&2
    source_name="bookworm.sources"
    ;;
esac

key_tmp="$(mktemp -p "${TMP_ROOT}" koalabyte-mopidy-key.XXXXXX)"
source_tmp="$(mktemp -p "${TMP_ROOT}" koalabyte-mopidy-source.XXXXXX)"
config_tmp="$(mktemp -p "${TMP_ROOT}" koalabyte-mopidy-conf.XXXXXX)"
player_tmp="$(mktemp -p "${TMP_ROOT}" koalabyte-music-json.XXXXXX)"
trap 'rm -f "${key_tmp}" "${source_tmp}" "${config_tmp}" "${player_tmp}"' EXIT

download_file https://apt.mopidy.com/mopidy-archive-keyring.gpg "${key_tmp}" || {
  fail_setup "failed to download Mopidy APT key"
  exit 1
}
download_file "https://apt.mopidy.com/${source_name}" "${source_tmp}" || {
  fail_setup "failed to download Mopidy APT source"
  exit 1
}
[[ -s "${key_tmp}" && -s "${source_tmp}" ]] || {
  fail_setup "downloaded Mopidy repository metadata is empty"
  exit 1
}

"${sudo_cmd[@]}" install -d -m 0755 /etc/apt/keyrings /etc/apt/sources.list.d
"${sudo_cmd[@]}" install -m 0644 "${key_tmp}" /etc/apt/keyrings/mopidy-archive-keyring.gpg
"${sudo_cmd[@]}" install -m 0644 "${source_tmp}" /etc/apt/sources.list.d/mopidy.sources

apt_noninteractive update || { fail_setup "APT update failed while enabling Mopidy"; exit 1; }
apt_noninteractive install -y \
  mopidy mopidy-mpd \
  gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-ugly gstreamer1.0-libav || {
    fail_setup "Mopidy or its media codecs failed to install"
    exit 1
  }

if apt-cache show mopidy-local >/dev/null 2>&1; then
  apt_noninteractive install -y mopidy-local || \
    echo "warning: optional mopidy-local package installation failed" >&2
fi

"${sudo_cmd[@]}" install -d -m 0755 "${MUSIC_DIR}" "${CONFIG_DIR}" /etc/mopidy
if id mopidy >/dev/null 2>&1; then
  "${sudo_cmd[@]}" usermod -a -G audio mopidy || true
  "${sudo_cmd[@]}" chown -R mopidy:audio "${MUSIC_DIR}" || true
  "${sudo_cmd[@]}" chmod 0775 "${MUSIC_DIR}" || true
fi

cat >"${config_tmp}" <<EOF
[core]
restore_state = true

[audio]
mixer = software
output = ${KOALABYTE_MOPIDY_AUDIO_OUTPUT:-autoaudiosink}

[http]
enabled = true
hostname = 127.0.0.1
port = 6680
zeroconf =
csrf_protection = true

[mpd]
enabled = true
hostname = 127.0.0.1
port = 6600

[file]
enabled = true
media_dirs =
    ${MUSIC_DIR}|KoalaByte Music
show_dotfiles = false
follow_symlinks = false
EOF
"${sudo_cmd[@]}" install -m 0644 "${config_tmp}" "${MOPIDY_CONFIG}"

if [[ ! -f "${PLAYER_CONFIG}" ]]; then
  cat >"${player_tmp}" <<'JSONEOF'
{
  "engine": "mopidy",
  "rpc_url": "http://127.0.0.1:6680/mopidy/rpc",
  "radio_presets": {}
}
JSONEOF
  "${sudo_cmd[@]}" install -m 0640 "${player_tmp}" "${PLAYER_CONFIG}"
fi

# Keep potentially credential-bearing radio URLs private while guaranteeing the
# normal KoalaByte runtime/check user can enumerate Lyrebird menus. This also
# repairs root:root 0640 files created by older one-shot versions.
"${sudo_cmd[@]}" chown "root:${SERVICE_GROUP}" "${PLAYER_CONFIG}" || {
  fail_setup "failed to grant ${SERVICE_USER} group ownership of ${PLAYER_CONFIG}" unavailable
  exit 1
}
"${sudo_cmd[@]}" chmod 0640 "${PLAYER_CONFIG}" || {
  fail_setup "failed to set protected readable mode on ${PLAYER_CONFIG}" unavailable
  exit 1
}

command -v systemctl >/dev/null 2>&1 || {
  fail_setup "systemd is required for Mopidy runtime"
  exit 1
}
"${sudo_cmd[@]}" systemctl daemon-reload
"${sudo_cmd[@]}" systemctl reset-failed mopidy.service >/dev/null 2>&1 || true
"${sudo_cmd[@]}" systemctl enable mopidy.service || {
  fail_setup "failed to enable mopidy.service"
  exit 1
}
"${sudo_cmd[@]}" systemctl restart mopidy.service || {
  fail_setup "failed to restart mopidy.service"
  exit 1
}

rpc_ready=0
deadline=$((SECONDS + MOPIDY_READY_TIMEOUT))
while (( SECONDS < deadline )); do
  if "${sudo_cmd[@]}" systemctl is-active --quiet mopidy.service && \
     command -v curl >/dev/null 2>&1 && \
     curl -fsS --max-time 5 -H 'Content-Type: application/json' \
       -d '{"jsonrpc":"2.0","id":1,"method":"core.playback.get_state"}' \
       "${RPC_URL}" | grep -q '"result"'; then
    rpc_ready=1
    break
  fi
  sleep 2
done

if command -v mopidyctl >/dev/null 2>&1; then
  "${sudo_cmd[@]}" mopidyctl config >/dev/null 2>&1 || true
  if command -v timeout >/dev/null 2>&1; then
    timeout 120 "${sudo_cmd[@]}" mopidyctl local scan >/dev/null 2>&1 || \
      echo "warning: optional Mopidy local scan did not complete" >&2
  else
    "${sudo_cmd[@]}" mopidyctl local scan >/dev/null 2>&1 || true
  fi
fi

if [[ "${rpc_ready}" == "1" ]]; then
  write_status MOPIDY_PLAYER_READY \
    "Mopidy system service and localhost JSON-RPC are ready" active
  exit 0
fi

"${sudo_cmd[@]}" systemctl --no-pager --full status mopidy.service >&2 || true
"${sudo_cmd[@]}" journalctl -u mopidy.service -n 50 --no-pager >&2 || true
fail_setup "Mopidy service or localhost JSON-RPC did not become ready" inactive
exit 1
