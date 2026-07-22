#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OLLAMA_INSTALL_MODE="${INSTALL_KILLERKOALA_OLLAMA:-auto}"
STRICT_KILLERKOALA_OLLAMA="${STRICT_KILLERKOALA_OLLAMA:-0}"
KILLERKOALA_BASE_MODEL="${KILLERKOALA_BASE_MODEL:-tinyllama:1.1b}"
KILLERKOALA_LLM_MODEL="${KILLERKOALA_LLM_MODEL:-killerkoala-tinyllama:latest}"
KILLERKOALA_OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
KILLERKOALA_OLLAMA_TIMEOUT="${KILLERKOALA_OLLAMA_TIMEOUT:-180}"
MODEFILE_PATH="${KILLERKOALA_MODELFILE_PATH:-${REPO_ROOT}/training/killerkoala_lora/Modelfile.killerkoala-tinyllama}"
STATUS_PATH="${KILLERKOALA_OLLAMA_STATUS_PATH:-${REPO_ROOT}/logs/killerkoala/ollama_setup_status.json}"
CHECK_ONLY=0
SKIP_SMOKE_TEST="${KILLERKOALA_OLLAMA_SKIP_SMOKE_TEST:-0}"
OLLAMA_CONTEXT_LENGTH="${OLLAMA_CONTEXT_LENGTH:-768}"
OLLAMA_NUM_PARALLEL="${OLLAMA_NUM_PARALLEL:-1}"
OLLAMA_MAX_LOADED_MODELS="${OLLAMA_MAX_LOADED_MODELS:-1}"
OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:-60s}"
OLLAMA_PULL_ATTEMPTS="${OLLAMA_PULL_ATTEMPTS:-3}"
SMOKE_PATH="${TMPDIR:-${HOME}/.cache/koalabyte/tmp}/killerkoala_ollama_smoke.txt"

usage() {
  cat <<'EOF'
KoalaByte Blue KillerKoala Ollama/TinyLlama setup helper

Installs Ollama, pulls TinyLlama, creates the KillerKoala alias, and performs a
short smoke test. Pi 3B+ defaults allow one model and one request at a time,
use a 768-token server context default, and unload the model after 60 seconds.
EOF
}

for arg in "$@"; do
  case "${arg}" in
    -h|--help) usage; exit 0 ;;
    --check-only) CHECK_ONLY=1 ;;
    --skip-smoke-test) SKIP_SMOKE_TEST=1 ;;
    *) echo "Unknown argument: ${arg}" >&2; usage >&2; exit 2 ;;
  esac
done
mkdir -p "$(dirname "${STATUS_PATH}")" "$(dirname "${SMOKE_PATH}")"

if [[ "${EUID}" -eq 0 ]]; then sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then sudo_cmd=(sudo)
else sudo_cmd=()
fi

write_status() {
  local status="$1" step="$2" reason="$3" ollama_version="" model_list=""
  if command -v ollama >/dev/null 2>&1; then
    ollama_version="$(ollama --version 2>/dev/null || true)"
    model_list="$(ollama list 2>/dev/null | sed 's/[[:space:]]\+/ /g' | head -n 20 || true)"
  fi
  python3 - "${STATUS_PATH}" "${status}" "${step}" "${reason}" \
    "${KILLERKOALA_BASE_MODEL}" "${KILLERKOALA_LLM_MODEL}" "${KILLERKOALA_OLLAMA_HOST}" \
    "${ollama_version}" "${model_list}" "${OLLAMA_CONTEXT_LENGTH}" \
    "${OLLAMA_NUM_PARALLEL}" "${OLLAMA_MAX_LOADED_MODELS}" <<'PY'
import json, sys, time
(path, status, step, reason, base_model, llm_model, host, version,
 model_list, context, parallel, loaded) = sys.argv[1:]
payload = {
    "status": status, "step": step, "reason": reason,
    "base_model": base_model, "killerkoala_model": llm_model,
    "ollama_host": host, "ollama_version": version,
    "ollama_models_sample": model_list.splitlines(),
    "server_context_default": int(context),
    "parallel_requests": int(parallel),
    "max_loaded_models": int(loaded),
    "updated_at": time.time(),
}
open(path, "w", encoding="utf-8").write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY
}

non_strict_continue() {
  local step="$1" reason="$2"
  write_status warning "${step}" "${reason}"
  if [[ "${STRICT_KILLERKOALA_OLLAMA}" == "1" ]]; then
    echo "STRICT_KILLERKOALA_OLLAMA=1: ${step} failed: ${reason}" >&2
    exit 1
  fi
  echo "Continuing without local TinyLlama: ${reason}" >&2
  exit 0
}

wait_for_ollama() {
  local deadline=$((SECONDS + KILLERKOALA_OLLAMA_TIMEOUT))
  while (( SECONDS < deadline )); do
    if command -v curl >/dev/null 2>&1 && curl -fsS --max-time 5 \
      "${KILLERKOALA_OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

install_low_memory_dropin() {
  command -v systemctl >/dev/null 2>&1 || return 0
  (( ${#sudo_cmd[@]} > 0 || EUID == 0 )) || return 0
  local dir="/etc/systemd/system/ollama.service.d" temp
  temp="$(mktemp)"
  cat >"${temp}" <<EOF
[Service]
Environment="OLLAMA_CONTEXT_LENGTH=${OLLAMA_CONTEXT_LENGTH}"
Environment="OLLAMA_NUM_PARALLEL=${OLLAMA_NUM_PARALLEL}"
Environment="OLLAMA_MAX_LOADED_MODELS=${OLLAMA_MAX_LOADED_MODELS}"
Environment="OLLAMA_KEEP_ALIVE=${OLLAMA_KEEP_ALIVE}"
EOF
  "${sudo_cmd[@]}" install -d -m 0755 "${dir}"
  "${sudo_cmd[@]}" install -m 0644 "${temp}" "${dir}/10-koalabyte-pi3.conf"
  rm -f "${temp}"
  "${sudo_cmd[@]}" systemctl daemon-reload
}

start_ollama_service() {
  install_low_memory_dropin
  if command -v systemctl >/dev/null 2>&1; then
    "${sudo_cmd[@]}" systemctl enable --now ollama >/dev/null 2>&1 || \
      systemctl --user enable --now ollama >/dev/null 2>&1 || true
  fi
  wait_for_ollama && return 0
  if command -v pgrep >/dev/null 2>&1 && pgrep -x ollama >/dev/null 2>&1; then
    wait_for_ollama && return 0
  fi
  if command -v nohup >/dev/null 2>&1; then
    mkdir -p "${REPO_ROOT}/logs/killerkoala"
    OLLAMA_CONTEXT_LENGTH="${OLLAMA_CONTEXT_LENGTH}" \
    OLLAMA_NUM_PARALLEL="${OLLAMA_NUM_PARALLEL}" \
    OLLAMA_MAX_LOADED_MODELS="${OLLAMA_MAX_LOADED_MODELS}" \
    OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE}" \
      nohup ollama serve >"${REPO_ROOT}/logs/killerkoala/ollama_serve.log" 2>&1 &
    disown || true
    wait_for_ollama && return 0
  fi
  return 1
}

ollama_retry() {
  local description="$1"; shift
  local attempt rc=1
  for ((attempt=1; attempt<=OLLAMA_PULL_ATTEMPTS; attempt++)); do
    set +e
    "$@"
    rc=$?
    set -e
    [[ ${rc} -eq 0 ]] && return 0
    echo "${description} attempt ${attempt}/${OLLAMA_PULL_ATTEMPTS} failed; retrying..." >&2
    sleep $((attempt * 15))
  done
  return "${rc}"
}

case "${OLLAMA_INSTALL_MODE}" in
  0|false|False|no|NO|skip|SKIP)
    write_status skipped killerkoala_ollama "disabled by INSTALL_KILLERKOALA_OLLAMA"
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES) ;;
  *) echo "Unknown INSTALL_KILLERKOALA_OLLAMA=${OLLAMA_INSTALL_MODE}." >&2; exit 2 ;;
esac

[[ -f "${MODEFILE_PATH}" ]] || non_strict_continue modelfile "missing Modelfile: ${MODEFILE_PATH}"
if [[ "${CHECK_ONLY}" == "1" ]]; then
  command -v ollama >/dev/null 2>&1 && write_status ok check_only "ollama command is present" || \
    write_status warning check_only "ollama command is not installed"
  bash -n "$0"
  exit 0
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama not found; installing from the official Ollama Linux installer."
  command -v curl >/dev/null 2>&1 || non_strict_continue ollama_install "curl is unavailable"
  tmp_install="$(mktemp)"
  curl -fsSL --retry 5 --retry-all-errors --connect-timeout 20 \
    https://ollama.com/install.sh -o "${tmp_install}" || \
    non_strict_continue ollama_install "failed to download Ollama installer"
  sh "${tmp_install}" || non_strict_continue ollama_install "official installer returned non-zero"
  rm -f "${tmp_install}"
fi

command -v ollama >/dev/null 2>&1 || non_strict_continue ollama_install "ollama is unavailable after install"
start_ollama_service || non_strict_continue ollama_service "Ollama API did not become ready"

write_status running pull_base_model "pulling ${KILLERKOALA_BASE_MODEL}"
ollama_retry "TinyLlama pull" ollama pull "${KILLERKOALA_BASE_MODEL}" || \
  non_strict_continue pull_base_model "failed to pull ${KILLERKOALA_BASE_MODEL}"

write_status running create_killerkoala_model "creating ${KILLERKOALA_LLM_MODEL}"
ollama create "${KILLERKOALA_LLM_MODEL}" -f "${MODEFILE_PATH}" || \
  non_strict_continue create_killerkoala_model "failed to create ${KILLERKOALA_LLM_MODEL}"

if [[ "${SKIP_SMOKE_TEST}" != "1" ]]; then
  write_status running smoke_test "running short local model smoke test"
  if command -v timeout >/dev/null 2>&1; then
    timeout "${KILLERKOALA_OLLAMA_TIMEOUT}" ollama run "${KILLERKOALA_LLM_MODEL}" \
      "Reply in under 12 words as KillerKoala: status check." >"${SMOKE_PATH}" 2>&1 || \
      non_strict_continue smoke_test "KillerKoala smoke test failed"
  else
    ollama run "${KILLERKOALA_LLM_MODEL}" \
      "Reply in under 12 words as KillerKoala: status check." >"${SMOKE_PATH}" 2>&1 || \
      non_strict_continue smoke_test "KillerKoala smoke test failed"
  fi
fi

write_status ok killerkoala_ollama "Ollama, TinyLlama, and ${KILLERKOALA_LLM_MODEL} are ready"
cat "${STATUS_PATH}"
