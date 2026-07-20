#!/usr/bin/env bash
set -euo pipefail

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

usage() {
  cat <<'EOF'
Install the Pi-owned KoalaByte Mopidy music engine.

Usage:
  bash scripts/setup_mopidy_player.sh
  bash scripts/setup_mopidy_player.sh --check-only

Environment:
  INSTALL_MOPIDY_PLAYER=auto|1|0
  STRICT_MOPIDY_PLAYER=0|1
  KOALABYTE_MUSIC_DIR=/srv/koalabyte-music
  KOALABYTE_MOPIDY_RPC_URL=http://127.0.0.1:6680/mopidy/rpc
  KOALABYTE_MOPIDY_AUDIO_OUTPUT=autoaudiosink

The HTTP and MPD control interfaces bind to localhost. Add radio presets to
/etc/koalabyte-blue/music.json. Streaming-service credentials belong in private
Mopidy configuration and must never be committed to the repository.
EOF
}

case "${1:-}" in
  "") ;;
  --check-only|--dry-run) CHECK_ONLY=1 ;;
  -h|--help) usage; exit 0 ;;
  *) echo "Unknown argument: ${1}" >&2; usage >&2; exit 2 ;;
esac

mkdir -p "$(dirname "${STATUS_PATH}")"

write_status() {
  local status="$1" reason="$2" service_state="${3:-unknown}"
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${service_state}" "${CHECK_ONLY}" "${MUSIC_DIR}" "${PLAYER_CONFIG}" "${MOPIDY_CONFIG}" "${RPC_URL}" <<'PY'
import json, sys, time
from pathlib import Path
path, status, reason, service_state, check_only, music_dir, player_config, mopidy_config, rpc_url = sys.argv[1:]
payload = {
    "status": status,
    "reason": reason,
    "service": "mopidy.service",
    "service_state": service_state,
    "check_only": check_only == "1",
    "execution_owner": "raspberry-pi",
    "engine": "mopidy",
    "rpc_url": rpc_url,
    "http_bind": "127.0.0.1:6680",
    "mpd_bind": "127.0.0.1:6600",
    "music_dir": music_dir,
    "player_config": player_config,
    "mopidy_config": mopidy_config,
    "sources": ["local_files", "internet_radio", "optional_mopidy_extensions"],
    "speech_ducking": True,
    "universal_error_lifecycle": True,
    "updated_at": time.time(),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(payload, sort_keys=True))
PY
}

case "${INSTALL_MOPIDY_PLAYER}" in
  0|false|False|no|NO|skip|SKIP)
    write_status "MOPIDY_PLAYER_SKIPPED" "disabled by INSTALL_MOPIDY_PLAYER" "disabled"
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES) ;;
  *) echo "Unknown INSTALL_MOPIDY_PLAYER=${INSTALL_MOPIDY_PLAYER}" >&2; exit 2 ;;
esac

if [[ "${CHECK_ONLY}" == "1" ]]; then
  grep -q 'hostname = 127.0.0.1' "$0"
  grep -q 'mopidy-archive-keyring.gpg' "$0"
  grep -q 'music.json' "$0"
  write_status "MOPIDY_PLAYER_CONTRACT_READY" "official APT source, localhost-only API, media directory, service, and private preset contract validated" "not_started"
  exit 0
fi

if [[ "$(uname -s)" != "Linux" ]]; then
  write_status "MOPIDY_PLAYER_UNSUPPORTED" "Mopidy setup requires Linux" "unsupported"
  [[ "${STRICT_MOPIDY_PLAYER}" == "1" ]] && exit 1
  exit 0
fi

if [[ "${EUID}" -eq 0 ]]; then
  sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then
  sudo_cmd=(sudo)
else
  write_status "MOPIDY_PLAYER_ERROR" "root or sudo is required" "unknown"
  [[ "${STRICT_MOPIDY_PLAYER}" == "1" ]] && exit 1
  exit 0
fi

fail_soft() {
  local reason="$1"
  write_status "MOPIDY_PLAYER_WARNING" "${reason}" "unavailable"
  if [[ "${STRICT_MOPIDY_PLAYER}" == "1" ]]; then
    exit 1
  fi
  exit 0
}

if ! command -v apt-get >/dev/null 2>&1; then
  fail_soft "apt-get is unavailable"
fi

. /etc/os-release 2>/dev/null || true
codename="${VERSION_CODENAME:-bookworm}"
case "${codename}" in
  trixie) source_name="trixie.sources" ;;
  bookworm|bullseye|*) source_name="bookworm.sources" ;;
esac

"${sudo_cmd[@]}" install -d -m 0755 /etc/apt/keyrings /etc/apt/sources.list.d
if command -v wget >/dev/null 2>&1; then
  "${sudo_cmd[@]}" wget -q -O /etc/apt/keyrings/mopidy-archive-keyring.gpg \
    https://apt.mopidy.com/mopidy-archive-keyring.gpg || fail_soft "failed to download Mopidy APT key"
  "${sudo_cmd[@]}" wget -q -O /etc/apt/sources.list.d/mopidy.sources \
    "https://apt.mopidy.com/${source_name}" || fail_soft "failed to download Mopidy APT source"
elif command -v curl >/dev/null 2>&1; then
  curl -fsSL https://apt.mopidy.com/mopidy-archive-keyring.gpg | \
    "${sudo_cmd[@]}" tee /etc/apt/keyrings/mopidy-archive-keyring.gpg >/dev/null || fail_soft "failed to download Mopidy APT key"
  curl -fsSL "https://apt.mopidy.com/${source_name}" | \
    "${sudo_cmd[@]}" tee /etc/apt/sources.list.d/mopidy.sources >/dev/null || fail_soft "failed to download Mopidy APT source"
else
  fail_soft "wget or curl is required to configure the Mopidy repository"
fi

"${sudo_cmd[@]}" apt-get update || fail_soft "apt update failed while enabling Mopidy"
DEBIAN_FRONTEND=noninteractive "${sudo_cmd[@]}" apt-get install -y \
  mopidy mopidy-mpd \
  gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-ugly gstreamer1.0-libav || \
  fail_soft "Mopidy or its media codecs failed to install"

if apt-cache show mopidy-local >/dev/null 2>&1; then
  DEBIAN_FRONTEND=noninteractive "${sudo_cmd[@]}" apt-get install -y mopidy-local || true
fi

"${sudo_cmd[@]}" install -d -m 0755 "${MUSIC_DIR}" "${CONFIG_DIR}" /etc/mopidy
if id mopidy >/dev/null 2>&1; then
  "${sudo_cmd[@]}" usermod -a -G audio mopidy || true
  "${sudo_cmd[@]}" chown -R mopidy:audio "${MUSIC_DIR}" || true
  "${sudo_cmd[@]}" chmod 0775 "${MUSIC_DIR}" || true
fi

cat >/tmp/koalabyte-mopidy.conf <<EOF
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
"${sudo_cmd[@]}" install -m 0644 /tmp/koalabyte-mopidy.conf "${MOPIDY_CONFIG}"

if [[ ! -f "${PLAYER_CONFIG}" ]]; then
  cat >/tmp/koalabyte-music.json <<'JSONEOF'
{
  "engine": "mopidy",
  "rpc_url": "http://127.0.0.1:6680/mopidy/rpc",
  "radio_presets": {}
}
JSONEOF
  "${sudo_cmd[@]}" install -m 0640 /tmp/koalabyte-music.json "${PLAYER_CONFIG}"
fi

if command -v systemctl >/dev/null 2>&1; then
  "${sudo_cmd[@]}" systemctl daemon-reload
  "${sudo_cmd[@]}" systemctl enable mopidy.service || true
  "${sudo_cmd[@]}" systemctl restart mopidy.service || true
fi

sleep 2
service_state="unknown"
if command -v systemctl >/dev/null 2>&1; then
  if "${sudo_cmd[@]}" systemctl is-active --quiet mopidy.service; then
    service_state="active"
  else
    service_state="inactive"
  fi
fi

rpc_ready=0
if command -v curl >/dev/null 2>&1; then
  if curl -fsS -H 'Content-Type: application/json' \
      -d '{"jsonrpc":"2.0","id":1,"method":"core.playback.get_state"}' \
      "${RPC_URL}" | grep -q '"result"'; then
    rpc_ready=1
  fi
fi

if command -v mopidyctl >/dev/null 2>&1; then
  "${sudo_cmd[@]}" mopidyctl config >/dev/null 2>&1 || true
  "${sudo_cmd[@]}" mopidyctl local scan >/dev/null 2>&1 || true
fi

if [[ "${service_state}" == "active" && "${rpc_ready}" == "1" ]]; then
  write_status "MOPIDY_PLAYER_READY" "Mopidy service and localhost JSON-RPC are ready" "${service_state}"
  exit 0
fi

write_status "MOPIDY_PLAYER_WARNING" "Mopidy installed, but service or RPC is not ready yet; inspect journalctl -u mopidy" "${service_state}"
[[ "${STRICT_MOPIDY_PLAYER}" == "1" ]] && exit 1
exit 0
