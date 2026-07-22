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
OLLAMA_CREATE_ATTEMPTS="${OLLAMA_CREATE_ATTEMPTS:-3}"
SMOKE_PATH="${TMPDIR:-${HOME}/.cache/koalabyte/tmp}/killerkoala_ollama_smoke.txt"

usage() {
  cat <<'EOF'
KoalaByte Blue KillerKoala Ollama/TinyLlama setup helper

Installs Ollama, pulls TinyLlama, creates the KillerKoala alias, and performs a
short smoke test. Pi 3B+ defaults allow one model and one request at a time,
use a 768-token context, and unload the model after 60 seconds.
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
    "status": status,
    "step": step,
    "reason": reason,
    "base_model": base_model,
    "killerkoala_model": llm_model,
    "ollama_host": host,
    "ollama_version": version,
    "ollama_models_sample": model_list.splitlines(),
    "server_context_default": int(context),
    "parallel_requests": int(parallel),
    "max_loaded_models": int(loaded),
    "systemd_service_required": True,
    "updated_at": time.time(),
}
open(path, "w", encoding="utf-8").write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY
}

fail_setup() {
  local step="$1" reason="$2"
  write_status failed "${step}" "${reason}"
  echo "KillerKoala Ollama setup failed at ${step}: ${reason}" >&2
  if [[ "${STRICT_KILLERKOALA_OLLAMA}" == "1" ]]; then
    exit 1
  fi
  # The complete one-shot health gate requires Ollama whenever AI was not skipped.
  # Return non-zero here as well so the failure is reported at its actual source.
  return 1
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
  command -v systemctl >/dev/null 2>&1 || return 1
  (( ${#sudo_cmd[@]} > 0 || EUID == 0 )) || return 1
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
  install_low_memory_dropin || return 1
  "${sudo_cmd[@]}" systemctl reset-failed ollama.service >/dev/null 2>&1 || true
  "${sudo_cmd[@]}" systemctl enable ollama.service >/dev/null 2>&1 || return 1
  "${sudo_cmd[@]}" systemctl restart ollama.service >/dev/null 2>&1 || return 1
  wait_for_ollama
}

retry_command() {
  local attempts="$1" description="$2"; shift 2
  local attempt rc=1
  for ((attempt=1; attempt<=attempts; attempt++)); do
    set +e
    "$@"
    rc=$?
    set -e
    [[ ${rc} -eq 0 ]] && return 0
    echo "${description} attempt ${attempt}/${attempts} failed; retrying..." >&2
    (( attempt < attempts )) && sleep $((attempt * 15))
  done
  return "${rc}"
}

model_present() {
  ollama list 2>/dev/null | awk 'NR > 1 {print $1}' | grep -Fxq "$1"
}

case "${OLLAMA_INSTALL_MODE}" in
  0|false|False|no|NO|skip|SKIP)
    write_status skipped killerkoala_ollama "disabled by INSTALL_KILLERKOALA_OLLAMA"
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES) ;;
  *) echo "Unknown INSTALL_KILLERKOALA_OLLAMA=${OLLAMA_INSTALL_MODE}." >&2; exit 2 ;;
esac

[[ -f "${MODEFILE_PATH}" ]] || { fail_setup modelfile "missing Modelfile: ${MODEFILE_PATH}"; exit 1; }
if [[ "${CHECK_ONLY}" == "1" ]]; then
  bash -n "$0"
  grep -Fq 'PARAMETER num_ctx 768' "${MODEFILE_PATH}" || {
    write_status failed check_only "Modelfile is not pinned to the Pi-safe 768-token context"
    exit 1
  }
  if command -v ollama >/dev/null 2>&1; then
    write_status ok check_only "ollama command is present and model contract is Pi-safe"
  else
    write_status warning check_only "ollama command is not installed; source contract is valid"
  fi
  exit 0
fi

command -v systemctl >/dev/null 2>&1 || { fail_setup ollama_service "systemd is required"; exit 1; }
(( ${#sudo_cmd[@]} > 0 || EUID == 0 )) || { fail_setup ollama_service "root or sudo is required"; exit 1; }

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama not found; installing from the official Ollama Linux installer."
  command -v curl >/dev/null 2>&1 || { fail_setup ollama_install "curl is unavailable"; exit 1; }
  tmp_install="$(mktemp)"
  if ! curl -fsSL --retry 5 --retry-all-errors --connect-timeout 20 \
      https://ollama.com/install.sh -o "${tmp_install}"; then
    rm -f "${tmp_install}"
    fail_setup ollama_install "failed to download official Ollama installer"
    exit 1
  fi
  if ! sh "${tmp_install}"; then
    rm -f "${tmp_install}"
    fail_setup ollama_install "official installer returned non-zero"
    exit 1
  fi
  rm -f "${tmp_install}"
fi

command -v ollama >/dev/null 2>&1 || { fail_setup ollama_install "ollama is unavailable after install"; exit 1; }
start_ollama_service || { fail_setup ollama_service "systemd service/API did not become ready"; exit 1; }

write_status running pull_base_model "pulling ${KILLERKOALA_BASE_MODEL}"
retry_command "${OLLAMA_PULL_ATTEMPTS}" "TinyLlama pull" \
  ollama pull "${KILLERKOALA_BASE_MODEL}" || {
    fail_setup pull_base_model "failed to pull ${KILLERKOALA_BASE_MODEL}"
    exit 1
  }

write_status running create_killerkoala_model "creating ${KILLERKOALA_LLM_MODEL}"
retry_command "${OLLAMA_CREATE_ATTEMPTS}" "KillerKoala model creation" \
  ollama create "${KILLERKOALA_LLM_MODEL}" -f "${MODEFILE_PATH}" || {
    fail_setup create_killerkoala_model "failed to create ${KILLERKOALA_LLM_MODEL}"
    exit 1
  }
model_present "${KILLERKOALA_LLM_MODEL}" || {
  fail_setup verify_killerkoala_model "created model is absent from ollama list"
  exit 1
}

if [[ "${SKIP_SMOKE_TEST}" != "1" ]]; then
  write_status running smoke_test "running short local model smoke test"
  rm -f "${SMOKE_PATH}"
  if command -v timeout >/dev/null 2>&1; then
    timeout "${KILLERKOALA_OLLAMA_TIMEOUT}" ollama run "${KILLERKOALA_LLM_MODEL}" \
      "Reply in under 12 words as KillerKoala: status check." >"${SMOKE_PATH}" 2>&1 || {
        fail_setup smoke_test "KillerKoala smoke test failed"
        exit 1
      }
  else
    ollama run "${KILLERKOALA_LLM_MODEL}" \
      "Reply in under 12 words as KillerKoala: status check." >"${SMOKE_PATH}" 2>&1 || {
        fail_setup smoke_test "KillerKoala smoke test failed"
        exit 1
      }
  fi
  [[ -s "${SMOKE_PATH}" ]] || {
    fail_setup smoke_test "KillerKoala smoke test returned empty output"
    exit 1
  }
fi

write_status ok killerkoala_ollama "Ollama system service, TinyLlama, and ${KILLERKOALA_LLM_MODEL} are ready"
cat "${STATUS_PATH}"
