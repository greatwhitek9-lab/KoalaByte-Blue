#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OLLAMA_INSTALL_MODE="${INSTALL_KILLERKOALA_OLLAMA:-auto}"
STRICT_KILLERKOALA_OLLAMA="${STRICT_KILLERKOALA_OLLAMA:-0}"
KILLERKOALA_BASE_MODEL="${KILLERKOALA_BASE_MODEL:-tinyllama:1.1b}"
KILLERKOALA_LLM_MODEL="${KILLERKOALA_LLM_MODEL:-killerkoala-tinyllama:latest}"
KILLERKOALA_OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
KILLERKOALA_OLLAMA_TIMEOUT="${KILLERKOALA_OLLAMA_TIMEOUT:-45}"
MODEFILE_PATH="${KILLERKOALA_MODELFILE_PATH:-${REPO_ROOT}/training/killerkoala_lora/Modelfile.killerkoala-tinyllama}"
STATUS_PATH="${KILLERKOALA_OLLAMA_STATUS_PATH:-${REPO_ROOT}/logs/killerkoala/ollama_setup_status.json}"
CHECK_ONLY=0
SKIP_SMOKE_TEST="${KILLERKOALA_OLLAMA_SKIP_SMOKE_TEST:-0}"

usage() {
  cat <<'EOF'
KoalaByte Blue KillerKoala Ollama/TinyLlama setup helper

Installs/checks Ollama, pulls TinyLlama, builds the KillerKoala model alias,
and runs a short local smoke test for the companion fallback/flexible banter path.

Default one-shot behavior:
  INSTALL_KILLERKOALA_OLLAMA=auto
  STRICT_KILLERKOALA_OLLAMA=0
  KILLERKOALA_BASE_MODEL=tinyllama:1.1b
  KILLERKOALA_LLM_MODEL=killerkoala-tinyllama:latest

Useful commands:
  bash scripts/setup_killerkoala_ollama.sh
  bash scripts/setup_killerkoala_ollama.sh --check-only

Useful env:
  INSTALL_KILLERKOALA_OLLAMA=auto|1|0
  STRICT_KILLERKOALA_OLLAMA=1
  KILLERKOALA_BASE_MODEL=tinyllama:1.1b
  KILLERKOALA_LLM_MODEL=killerkoala-tinyllama:latest
  KILLERKOALA_OLLAMA_SKIP_SMOKE_TEST=1
EOF
}

for arg in "$@"; do
  case "${arg}" in
    -h|--help)
      usage
      exit 0
      ;;
    --check-only)
      CHECK_ONLY=1
      ;;
    --skip-smoke-test)
      SKIP_SMOKE_TEST=1
      ;;
    *)
      echo "Unknown argument: ${arg}" >&2
      usage >&2
      exit 2
      ;;
  esac
done

mkdir -p "$(dirname "${STATUS_PATH}")"

json_escape() {
  python3 -c 'import json, sys; print(json.dumps(sys.stdin.read()))'
}

write_status() {
  local status="$1"
  local step="$2"
  local reason="$3"
  local ollama_version=""
  local model_list=""
  if command -v ollama >/dev/null 2>&1; then
    ollama_version="$(ollama --version 2>/dev/null || true)"
    model_list="$(ollama list 2>/dev/null | sed 's/[[:space:]]\+/ /g' | head -n 20 || true)"
  fi
  python3 - <<'PY' "${STATUS_PATH}" "${status}" "${step}" "${reason}" "${KILLERKOALA_BASE_MODEL}" "${KILLERKOALA_LLM_MODEL}" "${KILLERKOALA_OLLAMA_HOST}" "${ollama_version}" "${model_list}"
import json, sys, time
path, status, step, reason, base_model, llm_model, host, version, model_list = sys.argv[1:]
payload = {
    "status": status,
    "step": step,
    "reason": reason,
    "base_model": base_model,
    "killerkoala_model": llm_model,
    "ollama_host": host,
    "ollama_version": version,
    "ollama_models_sample": model_list.splitlines(),
    "updated_at": time.time(),
}
open(path, "w", encoding="utf-8").write(json.dumps(payload, indent=2, sort_keys=True))
PY
}

non_strict_continue() {
  local step="$1"
  local reason="$2"
  write_status "warning" "${step}" "${reason}"
  if [[ "${STRICT_KILLERKOALA_OLLAMA}" == "1" ]]; then
    echo "STRICT_KILLERKOALA_OLLAMA=1 is set; failing because ${step} failed: ${reason}" >&2
    exit 1
  fi
  echo "Continuing because STRICT_KILLERKOALA_OLLAMA is not enabled: ${reason}" >&2
  exit 0
}

wait_for_ollama() {
  local deadline=$((SECONDS + KILLERKOALA_OLLAMA_TIMEOUT))
  while (( SECONDS < deadline )); do
    if command -v curl >/dev/null 2>&1; then
      if curl -fsS "${KILLERKOALA_OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
        return 0
      fi
    elif ollama list >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

start_ollama_service() {
  if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl enable --now ollama >/dev/null 2>&1 || systemctl --user enable --now ollama >/dev/null 2>&1 || true
  fi
  if wait_for_ollama; then
    return 0
  fi
  if command -v pgrep >/dev/null 2>&1 && pgrep -x ollama >/dev/null 2>&1; then
    wait_for_ollama && return 0
  fi
  if command -v nohup >/dev/null 2>&1; then
    mkdir -p "${REPO_ROOT}/logs/killerkoala"
    nohup ollama serve >"${REPO_ROOT}/logs/killerkoala/ollama_serve.log" 2>&1 &
    disown || true
    wait_for_ollama && return 0
  fi
  return 1
}

case "${OLLAMA_INSTALL_MODE}" in
  0|false|False|no|NO|skip|SKIP)
    echo "Skipping KillerKoala Ollama/TinyLlama setup by INSTALL_KILLERKOALA_OLLAMA=${OLLAMA_INSTALL_MODE}."
    write_status "skipped" "killerkoala_ollama" "disabled by INSTALL_KILLERKOALA_OLLAMA"
    exit 0
    ;;
  auto|AUTO|1|true|True|yes|YES)
    ;;
  *)
    echo "Unknown INSTALL_KILLERKOALA_OLLAMA=${OLLAMA_INSTALL_MODE}. Use auto, 1, or 0." >&2
    exit 2
    ;;
esac

if [[ ! -f "${MODEFILE_PATH}" ]]; then
  non_strict_continue "modelfile" "missing KillerKoala Modelfile: ${MODEFILE_PATH}"
fi

if [[ "${CHECK_ONLY}" == "1" ]]; then
  if command -v ollama >/dev/null 2>&1; then
    write_status "ok" "check_only" "ollama command is present"
  else
    write_status "warning" "check_only" "ollama command is not installed"
  fi
  bash -n "$0"
  exit 0
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama not found; installing from the official Ollama Linux installer."
  if ! command -v curl >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update
      sudo apt-get install -y curl ca-certificates
    else
      non_strict_continue "ollama_install" "curl is missing and apt-get is unavailable"
    fi
  fi
  tmp_install="$(mktemp)"
  curl -fsSL https://ollama.com/install.sh -o "${tmp_install}" || non_strict_continue "ollama_install" "failed to download Ollama installer"
  sh "${tmp_install}" || non_strict_continue "ollama_install" "official Ollama installer returned a non-zero exit code"
  rm -f "${tmp_install}"
fi

command -v ollama >/dev/null 2>&1 || non_strict_continue "ollama_install" "ollama command is still unavailable after install"
start_ollama_service || non_strict_continue "ollama_service" "Ollama service/API did not become ready at ${KILLERKOALA_OLLAMA_HOST}"

write_status "running" "pull_base_model" "pulling ${KILLERKOALA_BASE_MODEL}"
ollama pull "${KILLERKOALA_BASE_MODEL}" || non_strict_continue "pull_base_model" "failed to pull ${KILLERKOALA_BASE_MODEL}"

write_status "running" "create_killerkoala_model" "creating ${KILLERKOALA_LLM_MODEL} from ${MODEFILE_PATH}"
ollama create "${KILLERKOALA_LLM_MODEL}" -f "${MODEFILE_PATH}" || non_strict_continue "create_killerkoala_model" "failed to create ${KILLERKOALA_LLM_MODEL}"

if [[ "${SKIP_SMOKE_TEST}" != "1" ]]; then
  write_status "running" "smoke_test" "running short KillerKoala local model smoke test"
  if command -v timeout >/dev/null 2>&1; then
    timeout "${KILLERKOALA_OLLAMA_TIMEOUT}" ollama run "${KILLERKOALA_LLM_MODEL}" "Reply in under 12 words as KillerKoala: status check." >/tmp/killerkoala_ollama_smoke.txt 2>&1 || non_strict_continue "smoke_test" "KillerKoala model smoke test failed"
  else
    ollama run "${KILLERKOALA_LLM_MODEL}" "Reply in under 12 words as KillerKoala: status check." >/tmp/killerkoala_ollama_smoke.txt 2>&1 || non_strict_continue "smoke_test" "KillerKoala model smoke test failed"
  fi
fi

write_status "ok" "killerkoala_ollama" "Ollama, TinyLlama, and ${KILLERKOALA_LLM_MODEL} are ready"
cat "${STATUS_PATH}"
