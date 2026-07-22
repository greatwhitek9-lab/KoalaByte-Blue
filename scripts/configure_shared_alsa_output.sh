#!/usr/bin/env bash
set -Eeuo pipefail

CARD_ID="${1:-}"
ENV_FILE="${KOALABYTE_ENV_FILE:-/etc/koalabyte-blue/killerkoala.env}"
ALSA_CONF="${KOALABYTE_ALSA_SHARED_CONFIG:-/etc/alsa/conf.d/99-koalabyte-shared-output.conf}"
MOPIDY_CONF="${KOALABYTE_MOPIDY_CONFIG:-/etc/mopidy/mopidy.conf}"
VOICE_SERVICE="koalabyte-dualeye-voice-bridge.service"
MUSIC_SERVICE="mopidy.service"

[[ "${CARD_ID}" =~ ^[A-Za-z0-9_.-]+$ ]] || {
  echo "Unsafe or empty ALSA card identifier: ${CARD_ID}" >&2
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

if command -v systemctl >/dev/null 2>&1; then
  for service in "${MUSIC_SERVICE}" "${VOICE_SERVICE}"; do
    if "${sudo_cmd[@]}" systemctl list-unit-files "${service}" >/dev/null 2>&1; then
      "${sudo_cmd[@]}" systemctl try-restart "${service}" >/dev/null 2>&1 || true
    fi
  done
fi

echo "Configured shared ALSA PCM 'koalabyte' on card ${CARD_ID}."
