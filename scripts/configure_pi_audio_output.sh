#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATUS_PATH="${KOALABYTE_AUDIO_STATUS_PATH:-${REPO_ROOT}/logs/one_shot/pi_audio_output_status.json}"
PREFERRED_PATTERN="${KOALABYTE_AUDIO_SINK_PATTERN:-JBL|USB|speaker|audio}"
ENV_FILE="${KOALABYTE_ENV_FILE:-/etc/koalabyte-blue/killerkoala.env}"
VOICE_SERVICE="koalabyte-dualeye-voice-bridge.service"
STRICT="${STRICT_PI_AUDIO_OUTPUT:-0}"
CHECK_ONLY=0

if [[ "${1:-}" == "--check-only" ]]; then
  CHECK_ONLY=1
elif [[ -n "${1:-}" ]]; then
  echo "Usage: $0 [--check-only]" >&2
  exit 2
fi

mkdir -p "$(dirname "${STATUS_PATH}")"

write_status() {
  local status="$1" backend="$2" selected="$3" reason="$4"
  python3 - "${STATUS_PATH}" "${status}" "${backend}" "${selected}" \
    "${reason}" "${PREFERRED_PATTERN}" "${CHECK_ONLY}" "${ENV_FILE}" <<'PY'
import json, sys, time
from pathlib import Path
path, status, backend, selected, reason, pattern, check_only, env_file = sys.argv[1:]
payload = {
    "status": status,
    "backend": backend,
    "selected_output": selected,
    "preferred_pattern": pattern,
    "check_only": check_only == "1",
    "service_environment_file": env_file,
    "pi_generated_speech_owner": "raspberry-pi",
    "esp32_local_speech_only": True,
    "shared_with_mopidy": selected == "koalabyte",
    "reason": reason,
    "updated_at": time.time(),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(payload, sort_keys=True))
PY
}

sudo_prefix() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    return 1
  fi
}

persist_env_value() {
  local key="$1" value="$2" temp
  [[ "${CHECK_ONLY}" == "1" ]] && return 0
  temp="$(mktemp)"
  if sudo_prefix test -f "${ENV_FILE}"; then
    sudo_prefix cat "${ENV_FILE}" | grep -v -E "^${key}=" >"${temp}" || true
  fi
  printf '%s=%s\n' "${key}" "${value}" >>"${temp}"
  sudo_prefix install -d -m 0750 "$(dirname "${ENV_FILE}")"
  sudo_prefix install -m 0600 "${temp}" "${ENV_FILE}"
  rm -f "${temp}"
}

restart_voice_service_if_installed() {
  [[ "${CHECK_ONLY}" == "1" ]] && return 0
  command -v systemctl >/dev/null 2>&1 || return 0
  if sudo_prefix systemctl list-unit-files "${VOICE_SERVICE}" >/dev/null 2>&1; then
    sudo_prefix systemctl try-restart "${VOICE_SERVICE}" >/dev/null 2>&1 || true
  fi
}

choose_wpctl_sink() {
  wpctl status 2>/dev/null | awk -v pattern="${PREFERRED_PATTERN}" '
    BEGIN { IGNORECASE=1; in_sinks=0 }
    /Sinks:/ { in_sinks=1; next }
    in_sinks && /Sources:/ { exit }
    in_sinks && $0 ~ pattern {
      line=$0
      sub(/^.*[[:space:]]([0-9]+)\..*$/, "\\1", line)
      if (line ~ /^[0-9]+$/) { print line; exit }
    }
  '
}

choose_pactl_sink() {
  pactl list short sinks 2>/dev/null | awk -v pattern="${PREFERRED_PATTERN}" '
    BEGIN { IGNORECASE=1 }
    $0 ~ pattern { print $2; exit }
  '
}

if command -v wpctl >/dev/null 2>&1; then
  sink="$(choose_wpctl_sink || true)"
  if [[ -n "${sink}" ]]; then
    if [[ "${CHECK_ONLY}" != "1" ]]; then
      wpctl set-default "${sink}"
      wpctl set-mute "${sink}" 0 || true
      wpctl set-volume "${sink}" "${KOALABYTE_AUDIO_VOLUME:-0.85}" || true
    fi
    write_status "PI_AUDIO_OUTPUT_READY" "wireplumber" "${sink}" \
      "Preferred JBL/USB/external sink selected."
    exit 0
  fi
fi

if command -v pactl >/dev/null 2>&1; then
  sink="$(choose_pactl_sink || true)"
  if [[ -n "${sink}" ]]; then
    if [[ "${CHECK_ONLY}" != "1" ]]; then
      pactl set-default-sink "${sink}"
      pactl set-sink-mute "${sink}" 0 || true
      pactl set-sink-volume "${sink}" "${KOALABYTE_AUDIO_VOLUME_PERCENT:-85%}" || true
    fi
    write_status "PI_AUDIO_OUTPUT_READY" "pulseaudio" "${sink}" \
      "Preferred JBL/USB/external sink selected."
    exit 0
  fi
fi

if command -v aplay >/dev/null 2>&1; then
  record="$(aplay -l 2>/dev/null | sed -nE \
    "/^card [0-9]+: .*(${PREFERRED_PATTERN})/I { s/^card ([0-9]+): ([^ ]+).*$/\\1\\t\\2/p; q; }")"
  if [[ -n "${record}" ]]; then
    card="${record%%$'\t'*}"
    card_id="${record#*$'\t'}"
    device=""
    if [[ "${CHECK_ONLY}" != "1" && -n "${card_id}" && "${card_id}" != "${record}" && \
          -f "${REPO_ROOT}/scripts/configure_shared_alsa_output.sh" ]]; then
      if KOALABYTE_ENV_FILE="${ENV_FILE}" \
        bash "${REPO_ROOT}/scripts/configure_shared_alsa_output.sh" "${card_id}"; then
        device="koalabyte"
      fi
    fi
    if [[ -z "${device}" ]]; then
      if [[ -n "${card_id}" && "${card_id}" != "${record}" ]]; then
        device="plughw:CARD=${card_id},DEV=0"
      else
        device="plughw:${card},0"
      fi
      persist_env_value "KOALABYTE_PI_ALSA_DEVICE" "${device}"
      restart_voice_service_if_installed
    fi
    write_status "PI_AUDIO_OUTPUT_READY" "alsa" "${device}" \
      "External ALSA device selected; shared mixing is enabled when supported."
    exit 0
  fi
fi

write_status "PI_AUDIO_OUTPUT_NOT_FOUND" "none" "" \
  "No JBL/USB/external output matched. The installer leaves the current Pi default output unchanged."
if [[ "${STRICT}" == "1" ]]; then
  exit 1
fi
