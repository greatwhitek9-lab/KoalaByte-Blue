#!/usr/bin/env bash
set -Eeuo pipefail

CARD_ID="${1:-}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${KOALABYTE_ENV_FILE:-/etc/koalabyte-blue/killerkoala.env}"
ALSA_CONF="${KOALABYTE_ALSA_SHARED_CONFIG:-/etc/alsa/conf.d/99-koalabyte-shared-output.conf}"
MOPIDY_CONF="${KOALABYTE_MOPIDY_CONFIG:-/etc/mopidy/mopidy.conf}"
VOICE_SERVICE="koalabyte-dualeye-voice-bridge.service"
MUSIC_SERVICE="mopidy.service"
VERIFY_TIMEOUT="${KOALABYTE_AUDIO_SERVICE_TIMEOUT:-60}"

[[ "${CARD_ID}" =~ ^[A-Za-z0-9_.-]+$ ]] || {
  echo "Unsafe or empty ALSA card identifier: ${CARD_ID}" >&2
  exit 2
}
[[ "${VERIFY_TIMEOUT}" =~ ^[1-9][0-9]*$ ]] || {
  echo "KOALABYTE_AUDIO_SERVICE_TIMEOUT must be a positive integer." >&2
  exit 2
}

if [[ "${EUID}" -eq 0 ]]; then sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then sudo_cmd=(sudo)
else
  echo "Root or sudo is required to configure shared ALSA output." >&2
  exit 1
fi

conf_tmp="$(mktemp)"
env_tmp="$(mktemp)"
mopidy_tmp="$(mktemp)"
trap 'rm -f "${conf_tmp}" "${env_tmp}" "${mopidy_tmp}"' EXIT

cat >"${conf_tmp}" <<EOF
# KoalaByte shared USB playback path for Mopidy and KillerKoala speech.
pcm.koalabyte_dmix {
    type dmix
    ipc_key 1262634050
    ipc_key_add_uid false
    ipc_perm 0666
    slave {
        pcm "hw:CARD=${CARD_ID},DEV=0"
        format S16_LE
        rate 48000
        channels 2
        period_time 0
        period_size 1024
        buffer_size 8192
    }
}

pcm.koalabyte {
    type plug
    slave.pcm "koalabyte_dmix"
}

ctl.koalabyte {
    type hw
    card "${CARD_ID}"
}
EOF
"${sudo_cmd[@]}" install -d -m 0755 "$(dirname "${ALSA_CONF}")"
"${sudo_cmd[@]}" install -m 0644 "${conf_tmp}" "${ALSA_CONF}"

if command -v aplay >/dev/null 2>&1; then
  if ! aplay -L 2>/dev/null | grep -Fxq 'koalabyte'; then
    echo "ALSA did not register the new 'koalabyte' PCM from ${ALSA_CONF}." >&2
    exit 1
  fi
fi

if "${sudo_cmd[@]}" test -f "${ENV_FILE}"; then
  "${sudo_cmd[@]}" cat "${ENV_FILE}" | \
    grep -v -E '^KOALABYTE_PI_ALSA_DEVICE=' >"${env_tmp}" || true
fi
printf '%s\n' 'KOALABYTE_PI_ALSA_DEVICE=koalabyte' >>"${env_tmp}"
"${sudo_cmd[@]}" install -d -m 0750 "$(dirname "${ENV_FILE}")"
"${sudo_cmd[@]}" install -m 0600 "${env_tmp}" "${ENV_FILE}"

if "${sudo_cmd[@]}" test -f "${MOPIDY_CONF}"; then
  "${sudo_cmd[@]}" cat "${MOPIDY_CONF}" | \
    sed -E '/^\[audio\]/,/^\[/ s#^output[[:space:]]*=.*#output = alsasink device=koalabyte#' \
    >"${mopidy_tmp}"
  "${sudo_cmd[@]}" install -m 0644 "${mopidy_tmp}" "${MOPIDY_CONF}"
fi

was_music_active=0
was_voice_active=0
if command -v systemctl >/dev/null 2>&1; then
  "${sudo_cmd[@]}" systemctl is-active --quiet "${MUSIC_SERVICE}" && was_music_active=1 || true
  "${sudo_cmd[@]}" systemctl is-active --quiet "${VOICE_SERVICE}" && was_voice_active=1 || true

  [[ "${was_music_active}" == "1" ]] && \
    "${sudo_cmd[@]}" systemctl restart "${MUSIC_SERVICE}"
  [[ "${was_voice_active}" == "1" ]] && \
    "${sudo_cmd[@]}" systemctl restart "${VOICE_SERVICE}"

  deadline=$(( $(date +%s) + VERIFY_TIMEOUT ))
  while (( $(date +%s) < deadline )); do
    music_ready=1
    voice_ready=1
    [[ "${was_music_active}" == "1" ]] && \
      "${sudo_cmd[@]}" systemctl is-active --quiet "${MUSIC_SERVICE}" || \
      [[ "${was_music_active}" == "0" ]] || music_ready=0
    [[ "${was_voice_active}" == "1" ]] && \
      "${sudo_cmd[@]}" systemctl is-active --quiet "${VOICE_SERVICE}" || \
      [[ "${was_voice_active}" == "0" ]] || voice_ready=0

    if [[ "${music_ready}" == "1" && "${voice_ready}" == "1" ]]; then
      if [[ "${was_music_active}" == "1" ]] && command -v curl >/dev/null 2>&1; then
        if ! curl -fsS --max-time 5 -H 'Content-Type: application/json' \
          -d '{"jsonrpc":"2.0","id":1,"method":"core.playback.get_state"}' \
          http://127.0.0.1:6680/mopidy/rpc | grep -q '"result"'; then
          sleep 2
          continue
        fi
      fi
      if [[ "${was_voice_active}" == "1" && ! -S "${ROOT}/logs/runtime/serial_bus/esp32.sock" ]]; then
        sleep 2
        continue
      fi
      break
    fi
    sleep 2
  done

  if [[ "${was_music_active}" == "1" ]] && \
     ! "${sudo_cmd[@]}" systemctl is-active --quiet "${MUSIC_SERVICE}"; then
    "${sudo_cmd[@]}" systemctl --no-pager --full status "${MUSIC_SERVICE}" >&2 || true
    "${sudo_cmd[@]}" journalctl -u "${MUSIC_SERVICE}" -n 40 --no-pager >&2 || true
    echo "Mopidy did not recover after shared ALSA configuration." >&2
    exit 1
  fi
  if [[ "${was_voice_active}" == "1" ]]; then
    if ! "${sudo_cmd[@]}" systemctl is-active --quiet "${VOICE_SERVICE}" || \
       [[ ! -S "${ROOT}/logs/runtime/serial_bus/esp32.sock" ]]; then
      "${sudo_cmd[@]}" systemctl --no-pager --full status "${VOICE_SERVICE}" >&2 || true
      "${sudo_cmd[@]}" journalctl -u "${VOICE_SERVICE}" -n 40 --no-pager >&2 || true
      echo "Voice bridge did not recover after shared ALSA configuration." >&2
      exit 1
    fi
  fi
fi

echo "Configured and verified shared ALSA PCM 'koalabyte' on card ${CARD_ID}."
