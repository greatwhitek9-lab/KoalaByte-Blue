#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_ESP32_TOOLS="${INSTALL_ESP32_TOOLS:-auto}"
STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS:-0}"
PLATFORMIO_VERSION="${PLATFORMIO_VERSION:-6.1.19}"
EDGE_TTS_VERSION="${EDGE_TTS_VERSION:-7.2.8}"
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

usage() {
  cat <<'EOF'
KoalaByte Blue ESP32/PlatformIO setup helper

The isolated environment pins PlatformIO Core 6.1.19 and edge-tts 7.2.8.
Python package downloads and individual Edge TTS synthesis calls retry transient
network failures without modifying the Pi runtime virtual environment.
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
    sudo -u "${INSTALL_USER}" -H env HOME="${INSTALL_HOME}" "$@"
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
  [[ -x "${wrapper}" ]] || return 1
  run_as_install_user mv -f "${wrapper}" "${real}"
  temp_wrapper="$(mktemp)"
  cat >"${temp_wrapper}" <<EOF
#!/usr/bin/env bash
set -u
real="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)/edge-tts-real"
attempts="${EDGE_TTS_ATTEMPTS}"
rc=1
for ((attempt=1; attempt<=attempts; attempt++)); do
  "\${real}" "\$@" && exit 0
  rc=\$?
  echo "edge-tts synthesis attempt \${attempt}/\${attempts} failed" >&2
  (( attempt < attempts )) && sleep \$((attempt * 2))
done
exit "\${rc}"
EOF
  run_as_install_user install -m 0755 "${temp_wrapper}" "${wrapper}"
  rm -f "${temp_wrapper}"
}

install_python_tools() {
  ensure_venv || return 1
  pip_install_retry --upgrade pip wheel setuptools
  pip_install_retry --upgrade "platformio==${PLATFORMIO_VERSION}" "edge-tts==${EDGE_TTS_VERSION}"
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
  if [[ "$(id -u)" == "0" ]]; then runner=(apt-get); else runner=(sudo apt-get); fi
  DEBIAN_FRONTEND=noninteractive "${runner[@]}" -o Acquire::Retries=3 update
  DEBIAN_FRONTEND=noninteractive "${runner[@]}" -o Acquire::Retries=3 install -y ffmpeg
}

if [[ "${CHECK_ONLY}" != "1" ]] && install_enabled; then
  install_python_tools || true
fi

missing=0
echo "== KoalaByte Blue ESP32 tool setup =="
echo "Install user: ${INSTALL_USER}"
echo "PlatformIO venv: ${ESP32_TOOLS_VENV}"
if [[ -x "${ESP32_TOOLS_VENV}/bin/pio" ]]; then
  actual_pio="$("${ESP32_TOOLS_VENV}/bin/python" -c 'import importlib.metadata; print(importlib.metadata.version("platformio"))' 2>/dev/null || true)"
  echo "PlatformIO Core: ${actual_pio:-unknown}"
  [[ "${actual_pio}" == "${PLATFORMIO_VERSION}" ]] || { echo "PlatformIO version mismatch" >&2; missing=1; }
else
  echo "PlatformIO/pio: MISSING" >&2; missing=1
fi
if [[ -x "${ESP32_TOOLS_VENV}/bin/edge-tts" && -x "${ESP32_TOOLS_VENV}/bin/edge-tts-real" ]]; then
  actual_edge="$("${ESP32_TOOLS_VENV}/bin/python" -c 'import importlib.metadata; print(importlib.metadata.version("edge-tts"))' 2>/dev/null || true)"
  echo "edge-tts: ${actual_edge:-unknown}, retry wrapper: ready"
  [[ "${actual_edge}" == "${EDGE_TTS_VERSION}" ]] || { echo "edge-tts version mismatch" >&2; missing=1; }
else
  echo "edge-tts retry wrapper: MISSING" >&2; missing=1
fi
if ensure_ffmpeg; then echo "ffmpeg: $(command -v ffmpeg)"
else echo "ffmpeg: MISSING" >&2; missing=1
fi

if [[ "${missing}" == "1" ]] && strict_enabled; then exit 1; fi
echo "ESP32 tool setup/check complete."
