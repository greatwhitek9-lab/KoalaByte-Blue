#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATUS_PATH="${KOALABYTE_AUDIO_STATUS_PATH:-${REPO_ROOT}/logs/one_shot/pi_audio_output_status.json}"
PREFERRED_PATTERN="${KOALABYTE_AUDIO_SINK_PATTERN:-JBL|USB|speaker|audio}"
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
  python3 - <<'PY' "${STATUS_PATH}" "${status}" "${backend}" "${selected}" "${reason}" "${PREFERRED_PATTERN}" "${CHECK_ONLY}"
import json, sys, time
from pathlib import Path
path, status, backend, selected, reason, pattern, check_only = sys.argv[1:]
payload = {
    "status": status,
    "backend": backend,
    "selected_output": selected,
    "preferred_pattern": pattern,
    "check_only": check_only == "1",
    "pi_generated_speech_owner": "raspberry-pi",
    "esp32_local_speech_only": True,
    "reason": reason,
    "updated_at": time.time(),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(payload, sort_keys=True))
PY
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
    write_status "PI_AUDIO_OUTPUT_READY" "wireplumber" "${sink}" "Preferred JBL/USB/external sink selected."
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
    write_status "PI_AUDIO_OUTPUT_READY" "pulseaudio" "${sink}" "Preferred JBL/USB/external sink selected."
    exit 0
  fi
fi

if command -v aplay >/dev/null 2>&1; then
  card="$(aplay -l 2>/dev/null | awk -v pattern="${PREFERRED_PATTERN}" '
    BEGIN { IGNORECASE=1 }
    /^card [0-9]+:/ && $0 ~ pattern {
      line=$0; sub(/^card /, "", line); sub(/:.*/, "", line); print line; exit
    }
  ')"
  if [[ -n "${card}" ]]; then
    write_status "PI_AUDIO_OUTPUT_DETECTED" "alsa" "hw:${card},0" "External audio device detected. ALSA applications may select this device explicitly; no global PipeWire/PulseAudio default was available."
    exit 0
  fi
fi

write_status "PI_AUDIO_OUTPUT_NOT_FOUND" "none" "" "No JBL/USB/external output matched. The installer leaves the current Pi default output unchanged."
if [[ "${STRICT}" == "1" ]]; then
  exit 1
fi
