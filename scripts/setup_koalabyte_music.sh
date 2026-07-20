#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_MUSIC="${INSTALL_KOALABYTE_MUSIC:-auto}"
STRICT_MUSIC="${STRICT_KOALABYTE_MUSIC:-0}"
CHECK_ONLY=0
STATUS_PATH="${ROOT}/logs/music/music_setup_status.json"
CONFIG_PATH="/etc/mopidy/mopidy.conf"
SOURCES_PATH="${ROOT}/config/music_sources.json"
MEDIA_DIR="${KOALABYTE_MUSIC_DIR:-/var/lib/mopidy/media}"
MOPIDY_RPC="${KOALABYTE_MOPIDY_RPC:-http://127.0.0.1:6680/mopidy/rpc}"

usage() {
  cat <<'EOF'
Install the KoalaByte Blue Pi-owned Mopidy music engine.

Usage:
  bash scripts/setup_koalabyte_music.sh
  bash scripts/setup_koalabyte_music.sh --check-only

Environment:
  INSTALL_KOALABYTE_MUSIC=auto|1|0
  STRICT_KOALABYTE_MUSIC=0|1
  KOALABYTE_MUSIC_DIR=/var/lib/mopidy/media
  KOALABYTE_MOPIDY_RPC=http://127.0.0.1:6680/mopidy/rpc
  MOPIDY_EXTRA_PYPI_PACKAGES='mopidy-subidy'

The core install provides local-file playback, direct HTTP/HTTPS radio streams,
MPD clients, menu/voice controls, and a localhost-only JSON-RPC API. Optional
Mopidy extensions and their credentials remain user-configured.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only|--dry-run) CHECK_ONLY=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

mkdir -p "$(dirname "${STATUS_PATH}")"

write_status() {
  local status="$1" reason="$2"
  python3 - "${STATUS_PATH}" "${status}" "${reason}" "${CHECK_ONLY}" "${MOPIDY_RPC}" "${MEDIA_DIR}" "${SOURCES_PATH}" <<'PY'
import json, sys, time
from pathlib import Path
path, status, reason, check_only, rpc, media_dir, sources_path = sys.argv[1:]
payload = {
    "status": status,
    "reason": reason,
    "check_only": check_only == "1",
    "engine": "Mopidy",
    "rpc_url": rpc,
    "rpc_scope": "localhost_only",
    "media_dir": media_dir,
    "sources_path": sources_path,
    "core_sources": ["local_files", "direct_http_https_streams", "mopidy_extensions"],
    "controls": ["status", "play", "pause", "stop", "next", "previous", "volume", "refresh", "favorite_stream"],
    "tts_ducking": True,
    "updated_at": time.time(),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

case "${INSTALL_MUSIC}" in
  0|false|False|no|NO|skip|SKIP)
    write_status "MUSIC_SKIPPED" "disabled by INSTALL_KOALABYTE_MUSIC"
    echo "Skipping KoalaByte music engine."
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES) ;;
  *) echo "Unknown INSTALL_KOALABYTE_MUSIC=${INSTALL_MUSIC}" >&2; exit 2 ;;
esac

validate_contract() {
  bash -n "${ROOT}/scripts/setup_koalabyte_music.sh"
  python3 -m py_compile \
    "${ROOT}/pi-companion/koalablue/music_player.py" \
    "${ROOT}/pi-companion/koalablue/full_menu_catalog.py" \
    "${ROOT}/scripts/check_music_player.py"
  [[ -f "${ROOT}/config/music_sources.example.json" ]]
}

validate_contract
if [[ "${CHECK_ONLY}" == "1" ]]; then
  write_status "MUSIC_INSTALLER_READY" "Mopidy installer and KoalaByte music control contract validated"
  echo "KoalaByte Mopidy installer check passed."
  exit 0
fi

if [[ "$(uname -s)" != "Linux" ]]; then
  write_status "MUSIC_UNSUPPORTED_HOST" "Mopidy system install requires Linux"
  [[ "${STRICT_MUSIC}" == "1" ]] && exit 1
  exit 0
fi

if [[ "${EUID}" -eq 0 ]]; then
  sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then
  sudo_cmd=(sudo)
else
  write_status "MUSIC_INSTALL_FAILED" "root or sudo is required"
  [[ "${STRICT_MUSIC}" == "1" ]] && exit 1
  exit 0
fi

install_failed=0
set +e
. /etc/os-release 2>/dev/null
codename="${VERSION_CODENAME:-bookworm}"
case "${codename}" in
  bookworm|trixie) ;;
  *) codename="bookworm" ;;
esac

"${sudo_cmd[@]}" install -d -m 0755 /etc/apt/keyrings
"${sudo_cmd[@]}" wget -q -O /etc/apt/keyrings/mopidy-archive-keyring.gpg \
  https://apt.mopidy.com/mopidy-archive-keyring.gpg || install_failed=1
"${sudo_cmd[@]}" wget -q -O /etc/apt/sources.list.d/mopidy.sources \
  "https://apt.mopidy.com/${codename}.sources" || install_failed=1
if [[ "${install_failed}" == "0" ]]; then
  "${sudo_cmd[@]}" apt-get update || install_failed=1
  "${sudo_cmd[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    mopidy mopidy-mpd gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly || install_failed=1
fi
set -e

if [[ "${install_failed}" != "0" || ! -x "$(command -v mopidy || true)" ]]; then
  write_status "MUSIC_INSTALL_DEFERRED" "Mopidy package installation failed or network/package archive was unavailable"
  if [[ "${STRICT_MUSIC}" == "1" || "${INSTALL_MUSIC}" =~ ^(1|true|True|yes|YES)$ ]]; then
    exit 1
  fi
  echo "Mopidy installation deferred; KoalaByte controls remain installed and will report MUSIC_UNAVAILABLE."
  exit 0
fi

"${sudo_cmd[@]}" install -d -o mopidy -g audio -m 0775 "${MEDIA_DIR}"
if getent group audio >/dev/null 2>&1; then
  "${sudo_cmd[@]}" usermod -aG audio mopidy || true
fi
"${sudo_cmd[@]}" install -d -m 0755 /etc/mopidy
"${sudo_cmd[@]}" touch "${CONFIG_PATH}"

python3 - "${CONFIG_PATH}" "${MEDIA_DIR}" <<'PY' >/tmp/koalabyte-mopidy.conf
from pathlib import Path
import sys

path = Path(sys.argv[1])
media_dir = sys.argv[2]
start = "# BEGIN KOALABYTE BLUE MUSIC"
end = "# END KOALABYTE BLUE MUSIC"
text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
if start in text and end in text:
    before, remainder = text.split(start, 1)
    _, after = remainder.split(end, 1)
    text = before.rstrip() + "\n\n" + after.lstrip()
block = f"""{start}
[core]
restore_state = true

[audio]
mixer = software
output = autoaudiosink

[http]
enabled = true
hostname = 127.0.0.1
port = 6680

[mpd]
enabled = true
hostname = 127.0.0.1
port = 6600

[file]
enabled = true
media_dirs =
    {media_dir}|KoalaByte Music

[stream]
enabled = true
protocols =
    http
    https
    mms
    rtmp
    rtmps
    rtsp
{end}
"""
print(text.rstrip() + "\n\n" + block)
PY
"${sudo_cmd[@]}" install -o root -g root -m 0644 /tmp/koalabyte-mopidy.conf "${CONFIG_PATH}"

if [[ ! -f "${SOURCES_PATH}" ]]; then
  cp "${ROOT}/config/music_sources.example.json" "${SOURCES_PATH}"
fi

if [[ -n "${MOPIDY_EXTRA_PYPI_PACKAGES:-}" ]]; then
  "${sudo_cmd[@]}" apt-get install -y python3-pip
  # shellcheck disable=SC2086
  "${sudo_cmd[@]}" python3 -m pip install --break-system-packages ${MOPIDY_EXTRA_PYPI_PACKAGES}
fi

if command -v systemctl >/dev/null 2>&1; then
  "${sudo_cmd[@]}" systemctl daemon-reload
  "${sudo_cmd[@]}" systemctl enable mopidy.service
  "${sudo_cmd[@]}" systemctl restart mopidy.service || true
fi

sleep 1
rpc_ready=0
python3 - "${MOPIDY_RPC}" <<'PY' && rpc_ready=1 || true
import json, sys
from urllib.request import Request, urlopen
payload = json.dumps({"jsonrpc":"2.0","id":1,"method":"core.playback.get_state"}).encode()
request = Request(sys.argv[1], data=payload, headers={"Content-Type":"application/json"})
with urlopen(request, timeout=4) as response:
    data = json.loads(response.read().decode())
if "result" not in data:
    raise SystemExit(1)
PY

if [[ "${rpc_ready}" == "1" ]]; then
  write_status "MUSIC_READY" "Mopidy service and localhost JSON-RPC are ready"
  echo "KoalaByte Mopidy music engine is ready."
else
  write_status "MUSIC_SERVICE_PENDING" "Mopidy installed but JSON-RPC is not responding yet"
  [[ "${STRICT_MUSIC}" == "1" ]] && exit 1
fi
