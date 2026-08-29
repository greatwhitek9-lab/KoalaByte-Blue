#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_ESP32_TOOLS="${INSTALL_ESP32_TOOLS:-auto}"
STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS:-0}"
PLATFORMIO_VERSION="${PLATFORMIO_VERSION:-6.1.19}"
EDGE_TTS_VERSION="${EDGE_TTS_VERSION:-7.2.8}"
AUDIOOP_LTS_VERSION="${AUDIOOP_LTS_VERSION:-0.2.2}"
PIP_RETRIES="${PIP_RETRIES:-25}"
PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT:-300}"
EDGE_TTS_ATTEMPTS="${EDGE_TTS_ATTEMPTS:-3}"
CHECK_ONLY=0

INSTALL_USER="${SUDO_USER:-${USER:-$(id -un)}}"
INSTALL_HOME="${HOME}"
if command -v getent >/dev/null 2>&1; then
  resolved_home="$(getent passwd "${INSTALL_USER}" | cut -d: -f6 || true)"
  [[ -n "${resolved_home}" ]] && INSTALL_HOME="${resolved_home}"
fi
ESP32_TOOLS_VENV="${ESP32_TOOLS_VENV:-${INSTALL_HOME}/.venvs/platformio}"
ESP32_USER_BIN="${INSTALL_HOME}/.local/bin"
ESP32_TMPDIR="${KOALABYTE_TMPDIR:-${TMPDIR:-${INSTALL_HOME}/.cache/koalabyte/tmp}}"
mkdir -p "${ESP32_TMPDIR}"
export TMPDIR="${ESP32_TMPDIR}" TMP="${ESP32_TMPDIR}" TEMP="${ESP32_TMPDIR}"

usage() {
  cat <<'EOF'
KoalaByte Blue ESP32/PlatformIO setup helper

The isolated environment pins PlatformIO Core 6.1.19 and edge-tts 7.2.8.
Python 3.13+ also receives audioop-lts because the embedded William response
builder still uses the standard audioop import removed from Python 3.13.
The venv also carries rich-click and intelhex so PlatformIO's bundled esptool.py
runs with the same interpreter during chip probes and flashing.
Pip, PlatformIO, and voice generation use persistent SD-card temporary storage.
William clips are cached by their exact synthesis parameters, and missing clips
retry transient network failures without rebuilding completed clips.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) CHECK_ONLY=1; INSTALL_ESP32_TOOLS=0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

cd "${REPO_ROOT}"
export PATH="${ESP32_USER_BIN}:${ESP32_TOOLS_VENV}/bin:${PATH}"

install_enabled() {
  case "${INSTALL_ESP32_TOOLS}" in 1|true|True|yes|YES|auto|AUTO) return 0 ;; *) return 1 ;; esac
}
strict_enabled() { [[ "${STRICT_ESP32_TOOLS}" == "1" ]]; }
run_as_install_user() {
  if [[ "$(id -u)" == "0" && "${INSTALL_USER}" != "root" ]]; then
    sudo -u "${INSTALL_USER}" -H env \
      HOME="${INSTALL_HOME}" TMPDIR="${ESP32_TMPDIR}" \
      TMP="${ESP32_TMPDIR}" TEMP="${ESP32_TMPDIR}" "$@"
  else
    "$@"
  fi
}

ensure_venv() {
  [[ -x "${ESP32_TOOLS_VENV}/bin/python" ]] && return 0
  echo "Creating isolated ESP32 tools venv: ${ESP32_TOOLS_VENV}"
  run_as_install_user "${PYTHON_BIN}" -m venv "${ESP32_TOOLS_VENV}" || {
    echo "Unable to create ESP32 tools venv; install python3-venv/python3-full." >&2
    return 1
  }
}

pip_install_retry() {
  local attempt rc=1
  for attempt in 1 2 3; do
    set +e
    run_as_install_user "${ESP32_TOOLS_VENV}/bin/python" -m pip install \
      --retries "${PIP_RETRIES}" --timeout "${PIP_DEFAULT_TIMEOUT}" \
      --prefer-binary --no-input "$@"
    rc=$?
    set -e
    [[ ${rc} -eq 0 ]] && return 0
    echo "ESP32 pip attempt ${attempt}/3 failed with exit ${rc}; retrying..." >&2
    sleep $((attempt * 10))
  done
  return "${rc}"
}

install_edge_tts_retry_wrapper() {
  local bin_dir="${ESP32_TOOLS_VENV}/bin"
  local real="${bin_dir}/edge-tts-real"
  local wrapper="${bin_dir}/edge-tts"
  local temp_wrapper
  [[ -x "${wrapper}" ]] || return 1

  if grep -Fq 'KOALABYTE_EDGE_TTS_RETRY_WRAPPER' "${wrapper}" 2>/dev/null && [[ -x "${real}" ]]; then
    return 0
  fi

  run_as_install_user mv -f "${wrapper}" "${real}"
  temp_wrapper="$(mktemp)"
  cat >"${temp_wrapper}" <<'EOF'
#!/usr/bin/env bash
# KOALABYTE_EDGE_TTS_RETRY_WRAPPER
set -u
real="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/edge-tts-real"
attempts="${KOALABYTE_EDGE_TTS_ATTEMPTS:-3}"
cache_root="${KOALABYTE_EDGE_TTS_CACHE:-${HOME}/.cache/koalabyte/edge-tts}"
args=("$@")
key_args=()
output=""
expect_output=0

for arg in "${args[@]}"; do
  if (( expect_output )); then
    output="${arg}"
    key_args+=("<write-media-path>")
    expect_output=0
    continue
  fi
  case "${arg}" in
    --write-media)
      key_args+=("--write-media")
      expect_output=1
      ;;
    --write-media=*)
      output="${arg#*=}"
      key_args+=("--write-media=<write-media-path>")
      ;;
    *) key_args+=("${arg}") ;;
  esac
done

cache_file=""
if [[ -n "${output}" ]] && command -v sha256sum >/dev/null 2>&1; then
  mkdir -p "${cache_root}"
  key="$(printf '%s\0' "${key_args[@]}" | sha256sum | awk '{print $1}')"
  cache_file="${cache_root}/${key}.media"
  if [[ -s "${cache_file}" ]]; then
    install -D -m 0644 "${cache_file}" "${output}"
    exit 0
  fi
fi

rc=1
for ((attempt=1; attempt<=attempts; attempt++)); do
  if "${real}" "$@"; then
    if [[ -n "${cache_file}" && -n "${output}" && -s "${output}" ]]; then
      cache_tmp="${cache_file}.tmp.$$"
      cp -f "${output}" "${cache_tmp}" && mv -f "${cache_tmp}" "${cache_file}"
    fi
    exit 0
  fi
  rc=$?
  echo "edge-tts synthesis attempt ${attempt}/${attempts} failed" >&2
  (( attempt < attempts )) && sleep $((attempt * 2))
done
exit "${rc}"
EOF
  run_as_install_user install -m 0755 "${temp_wrapper}" "${wrapper}"
  rm -f "${temp_wrapper}"
}

install_python_tools() {
  ensure_venv || return 1
  pip_install_retry --upgrade pip wheel setuptools
  pip_install_retry --upgrade \
    "platformio==${PLATFORMIO_VERSION}" \
    "edge-tts==${EDGE_TTS_VERSION}" \
    "rich-click" \
    "intelhex" \
    "audioop-lts==${AUDIOOP_LTS_VERSION}; python_version>='3.13'"
  install_edge_tts_retry_wrapper
  run_as_install_user mkdir -p "${ESP32_USER_BIN}"
  run_as_install_user ln -sfn "${ESP32_TOOLS_VENV}/bin/pio" "${ESP32_USER_BIN}/pio"
  run_as_install_user ln -sfn "${ESP32_TOOLS_VENV}/bin/platformio" "${ESP32_USER_BIN}/platformio"
  run_as_install_user ln -sfn "${ESP32_TOOLS_VENV}/bin/edge-tts" "${ESP32_USER_BIN}/edge-tts"
}

ensure_ffmpeg() {
  command -v ffmpeg >/dev/null 2>&1 && return 0
  [[ "${CHECK_ONLY}" == "1" ]] && return 1
  install_enabled || return 1
  if [[ "$(id -u)" == "0" ]]; then
    runner=(env DEBIAN_FRONTEND=noninteractive apt-get)
  else
    runner=(sudo env DEBIAN_FRONTEND=noninteractive apt-get)
  fi
  "${runner[@]}" -o Acquire::Retries=3 update
  "${runner[@]}" -o Acquire::Retries=3 install -y ffmpeg
}

if [[ "${CHECK_ONLY}" != "1" ]] && install_enabled; then
  install_python_tools || true
fi

missing=0
echo "== KoalaByte Blue ESP32 tool setup =="
echo "Install user: ${INSTALL_USER}"
echo "PlatformIO venv: ${ESP32_TOOLS_VENV}"
echo "Persistent temp: ${ESP32_TMPDIR}"
if [[ -x "${ESP32_TOOLS_VENV}/bin/pio" ]]; then
  actual_pio="$("${ESP32_TOOLS_VENV}/bin/python" -c 'import importlib.metadata; print(importlib.metadata.version("platformio"))' 2>/dev/null || true)"
  echo "PlatformIO Core: ${actual_pio:-unknown}"
  [[ "${actual_pio}" == "${PLATFORMIO_VERSION}" ]] || { echo "PlatformIO version mismatch" >&2; missing=1; }
else
  echo "PlatformIO/pio: MISSING" >&2; missing=1
fi
if [[ -x "${ESP32_TOOLS_VENV}/bin/edge-tts" && -x "${ESP32_TOOLS_VENV}/bin/edge-tts-real" ]] && \
   grep -Fq 'KOALABYTE_EDGE_TTS_RETRY_WRAPPER' "${ESP32_TOOLS_VENV}/bin/edge-tts"; then
  actual_edge="$("${ESP32_TOOLS_VENV}/bin/python" -c 'import importlib.metadata; print(importlib.metadata.version("edge-tts"))' 2>/dev/null || true)"
  echo "edge-tts: ${actual_edge:-unknown}, retry wrapper: ready"
  [[ "${actual_edge}" == "${EDGE_TTS_VERSION}" ]] || { echo "edge-tts version mismatch" >&2; missing=1; }
else
  echo "edge-tts retry wrapper: MISSING" >&2; missing=1
fi
if [[ -x "${ESP32_TOOLS_VENV}/bin/python" ]] && \
   "${ESP32_TOOLS_VENV}/bin/python" -W ignore::DeprecationWarning -c 'import audioop' >/dev/null 2>&1; then
  echo "audioop compatibility: ready"
else
  echo "audioop compatibility: MISSING" >&2; missing=1
fi
if [[ -x "${ESP32_TOOLS_VENV}/bin/python" ]] && \
   "${ESP32_TOOLS_VENV}/bin/python" -c 'import rich_click, intelhex, serial' >/dev/null 2>&1; then
  echo "esptool Python dependencies: ready"
else
  echo "esptool Python dependencies: MISSING" >&2; missing=1
fi
if ensure_ffmpeg; then echo "ffmpeg: $(command -v ffmpeg)"
else echo "ffmpeg: MISSING" >&2; missing=1
fi

if [[ "${missing}" == "1" ]] && strict_enabled; then exit 1; fi
[[ "${missing}" == "0" ]] || exit 1
echo "ESP32 tool setup/check complete."
