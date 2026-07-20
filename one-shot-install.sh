#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${REPO_ROOT}"

CHECK_ONLY=0
SKIP_PACKAGES=0
SKIP_AUDIO=0
SKIP_CAN=0
SKIP_AI=0
SERVICE_USER="${KOALABYTE_SERVICE_USER:-${SUDO_USER:-${USER:-pi}}}"
STATUS_PATH="${KOALABYTE_ONE_SHOT_STATUS_PATH:-logs/one_shot/final_install_status.json}"
PYTHON_BIN="${REPO_ROOT}/pi-companion/.venv/bin/python"
INSTALL_INNOMAKER_CAN="${INSTALL_INNOMAKER_CAN:-auto}"

usage() {
  cat <<'EOF'
KoalaByte Blue final Raspberry Pi one-shot installer

Usage:
  bash one-shot-install.sh
  bash one-shot-install.sh --check-only
  bash one-shot-install.sh --skip-packages
  bash one-shot-install.sh --skip-audio
  bash one-shot-install.sh --skip-can
  bash one-shot-install.sh --skip-ai

This installer owns Raspberry Pi provisioning:
  - system packages and Python virtual environment
  - headless K1-K8 menu, action, and live display-sync controller for Raspberry Pi OS Lite
  - hold protection and restricted power permissions for K7 safe shutdown and K8 reboot
  - Heltec T114 and ESP32-S3 stable USB aliases
  - Waveshare local wake/basic vocabulary with automatic TinyLlama fallback
  - local Ollama/TinyLlama conversational KillerKoala model
  - optional web research for accurate current answers when internet is available
  - male Australian William TTS backend while the persona remains KillerKoala
  - tone/subject-synchronized DualEye expressions and Heltec mouth animation
  - BLE-node, voice-bridge, and doctor services
  - external audio selection
  - optional stock-firmware InnoMaker SocketCAN setup when hardware is present
  - final device discovery, controls, menu, voice, AI, and hardware reports

This Pi installer does not flash ESP32-S3, Heltec T114, or InnoMaker firmware
and never transmits CAN frames. Firmware source builds remain separate from Pi
installation and the working peripheral firmware is preserved.

Environment:
  KOALABYTE_SERVICE_USER=<linux-user>
  INSTALL_INNOMAKER_CAN=auto|1|0
  INSTALL_KILLERKOALA_OLLAMA=auto|1|0
  STRICT_KILLERKOALA_OLLAMA=0|1
  KILLERKOALA_LLM_MODEL=killerkoala-tinyllama:latest
  KILLERKOALA_WEB_SEARCH=auto|always|off
  BRAVE_SEARCH_API_KEY=<optional private key>
  CAN_INTERFACE=can0
  CAN_BITRATE=500000
  KOALABYTE_AUDIO_SINK_PATTERN='JBL|USB|speaker|audio'
  STRICT_GPIO_BUTTONS=0|1
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only|--dry-run) CHECK_ONLY=1 ;;
    --skip-packages) SKIP_PACKAGES=1 ;;
    --skip-audio) SKIP_AUDIO=1 ;;
    --skip-can) SKIP_CAN=1 ;;
    --skip-ai) SKIP_AI=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

mkdir -p "$(dirname "${STATUS_PATH}")" logs/preflight logs/pi_hardware logs/gpio_buttons logs/runtime logs/killerkoala

write_status() {
  local status="$1" step="$2" reason="$3"
  python3 - "${STATUS_PATH}" "${status}" "${step}" "${reason}" "${CHECK_ONLY}" "${SERVICE_USER}" "${SKIP_AI}" <<'PY'
import json, sys, time
from pathlib import Path
path, status, step, reason, check_only, service_user, skip_ai = sys.argv[1:]
payload = {
    "status": status,
    "step": step,
    "reason": reason,
    "check_only": check_only == "1",
    "service_user": service_user,
    "runtime_mode": "headless_pi_os_lite",
    "response_routing": "waveshare_saved_vocabulary_then_tinyllama",
    "local_ai_model": "killerkoala-tinyllama:latest",
    "web_research": "auto_when_internet_available",
    "tts_voice": "en-AU-WilliamNeural",
    "tone_synced_displays": True,
    "ai_setup_skipped": skip_ai == "1",
    "firmware_flashing": False,
    "can_transmit_during_install": False,
    "esp32_preserved": True,
    "heltec_preserved": True,
    "innomaker_stock_firmware_preserved": True,
    "updated_at": time.time(),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

run_step() {
  local name="$1"
  shift
  echo
  echo "== ${name} =="
  write_status "running" "${name}" "step started"
  "$@"
  write_status "ok" "${name}" "step completed"
}

python_for_runtime() {
  if [[ -x "${PYTHON_BIN}" ]]; then
    printf '%s\n' "${PYTHON_BIN}"
  else
    printf '%s\n' python3
  fi
}

can_hardware_present() {
  compgen -G '/sys/class/net/can*' >/dev/null && return 0
  command -v lsusb >/dev/null 2>&1 || return 1
  lsusb | grep -Eiq 'innomaker|usb.?can|candle|canable|gs[_ -]?usb'
}

can_enabled() {
  [[ "${SKIP_CAN}" == "1" ]] && return 1
  case "${INSTALL_INNOMAKER_CAN}" in
    0|false|False|no|NO|skip|SKIP) return 1 ;;
    1|true|True|yes|YES) return 0 ;;
    auto|AUTO|optional) can_hardware_present ;;
    *) echo "Invalid INSTALL_INNOMAKER_CAN=${INSTALL_INNOMAKER_CAN}" >&2; exit 2 ;;
  esac
}

validate_sources() {
  bash -n one-shot-install.sh
  bash -n install.sh
  bash -n scripts/setup_pi_hardware_stage.sh
  bash -n scripts/setup_killerkoala_ollama.sh
  bash -n scripts/install_power_controls.sh
  bash -n scripts/install_koalabyte_boot_services.sh
  bash -n scripts/install_ble_node_manager_service.sh
  bash -n scripts/install_esp32_dualeye_voice_bridge_service.sh
  bash -n scripts/install_koalabyte_udev_rules.sh
  bash -n scripts/configure_pi_audio_output.sh
  python3 -m py_compile \
    scripts/run_headless_menu.py \
    scripts/setup_gpio_buttons.py \
    scripts/test_gpio_buttons.py \
    scripts/pi_hardware_doctor.py \
    scripts/discover_koalabyte_ports.py \
    scripts/check_one_shot_controls.py \
    scripts/check_killerkoala_ai.py \
    scripts/check_full_runtime_dependencies.py \
    pi-companion/koalablue/gpio_buttons.py \
    pi-companion/koalablue/dualeye_tts.py \
    pi-companion/koalablue/killerkoala_expression.py \
    pi-companion/koalablue/killerkoala_web_research.py \
    pi-companion/koalablue/killerkoala_hybrid_companion.py \
    pi-companion/koalablue/killerkoala_voice_control.py \
    pi-companion/koalablue/esp32_dualeye_speech_synced_bridge.py
}

run_discovery() {
  local py
  py="$(python_for_runtime)"
  PYTHONPATH=pi-companion "${py}" scripts/discover_koalabyte_ports.py \
    --profile heltec --output-dir logs/preflight
}

run_button_probe() {
  local py
  py="$(python_for_runtime)"
  PYTHONPATH=pi-companion STRICT_GPIO_BUTTONS="${STRICT_GPIO_BUTTONS:-0}" \
    "${py}" scripts/setup_gpio_buttons.py --probe
}

run_controls_gate() {
  local py
  py="$(python_for_runtime)"
  PYTHONPATH=pi-companion "${py}" scripts/check_one_shot_controls.py
}

run_runtime_checks() {
  local py
  py="$(python_for_runtime)"
  PYTHONPATH=pi-companion "${py}" scripts/check_killerkoala_ai.py
  PYTHONPATH=pi-companion KOALABYTE_MENU_SYNC=0 "${py}" scripts/check_menu_display_sync.py
  PYTHONPATH=pi-companion "${py}" scripts/check_menu_actions.py
  PYTHONPATH=pi-companion "${py}" scripts/check_killerkoala_face_mouth_sync.py
  INSTALL_INNOMAKER_CAN="${INSTALL_INNOMAKER_CAN}" \
    PYTHONPATH=pi-companion "${py}" scripts/check_full_runtime_dependencies.py
}

restart_services() {
  command -v systemctl >/dev/null 2>&1 || return 0
  local sudo_cmd=()
  if [[ "${EUID}" -ne 0 ]]; then
    sudo_cmd=(sudo)
  fi
  "${sudo_cmd[@]}" systemctl daemon-reload
  for service in \
    ollama.service \
    koalabyte-menu.service \
    koalabyte-doctor.service \
    koalabyte-ble-node-manager.service \
    koalabyte-dualeye-voice-bridge.service; do
    if "${sudo_cmd[@]}" systemctl list-unit-files "${service}" >/dev/null 2>&1; then
      "${sudo_cmd[@]}" systemctl enable "${service}" >/dev/null 2>&1 || true
      "${sudo_cmd[@]}" systemctl restart "${service}" || true
    fi
  done
  if can_enabled && "${sudo_cmd[@]}" systemctl list-unit-files koalabyte-can0.service >/dev/null 2>&1; then
    "${sudo_cmd[@]}" systemctl enable koalabyte-can0.service >/dev/null 2>&1 || true
    "${sudo_cmd[@]}" systemctl restart koalabyte-can0.service || true
  fi
}

run_final_doctor() {
  local rc=0
  set +e
  INSTALL_INNOMAKER_CAN="${INSTALL_INNOMAKER_CAN}" \
    "$(python_for_runtime)" scripts/pi_hardware_doctor.py \
    --can-interface "${CAN_INTERFACE:-can0}" --gpio-live
  rc=$?
  set -e
  if [[ "${rc}" -ne 0 ]]; then
    echo "Hardware doctor recorded items needing attention; installation remains complete because disconnected or optional hardware is non-fatal."
  fi
  return 0
}

trap 'write_status "failed" "final_one_shot" "installer stopped before completion"' ERR

run_step "Source and installer validation" validate_sources

if [[ "${CHECK_ONLY}" == "1" ]]; then
  run_step "Restricted K7/K8 power permissions" env KOALABYTE_SERVICE_USER="${SERVICE_USER}" bash scripts/install_power_controls.sh --check-only
  run_step "Pi hardware inventory" env INSTALL_INNOMAKER_CAN="${INSTALL_INNOMAKER_CAN}" bash scripts/setup_pi_hardware_stage.sh --check-only
  run_step "K1-K8 control contract" run_controls_gate
  if [[ "${SKIP_AI}" != "1" ]]; then
    run_step "TinyLlama installer contract" bash scripts/setup_killerkoala_ollama.sh --check-only
  fi
  run_step "Audio readiness" bash scripts/configure_pi_audio_output.sh --check-only
  write_status "complete" "final_one_shot_check" "Pi installer, local vocabulary routing, TinyLlama/web/TTS contract, synchronized displays, headless controls, restricted power, services, devices, and no-flash policies validated"
  trap - ERR
  echo
  echo "KoalaByte final one-shot check-only passed."
  echo "Status: ${STATUS_PATH}"
  exit 0
fi

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "The final one-shot installer must run on the Raspberry Pi Linux host." >&2
  exit 1
fi

stage_args=(--install-runtime-services)
[[ "${SKIP_PACKAGES}" == "1" ]] && stage_args+=(--skip-packages)
[[ "${SKIP_AUDIO}" == "1" ]] && stage_args+=(--skip-audio)
if ! can_enabled; then
  stage_args+=(--skip-can-service)
fi

run_step "Raspberry Pi hardware and runtime services" \
  env KOALABYTE_SERVICE_USER="${SERVICE_USER}" \
      CAN_INTERFACE="${CAN_INTERFACE:-can0}" \
      CAN_BITRATE="${CAN_BITRATE:-500000}" \
      bash scripts/setup_pi_hardware_stage.sh "${stage_args[@]}"

if [[ "${SKIP_AI}" != "1" ]]; then
  run_step "Local KillerKoala TinyLlama model" \
    env INSTALL_KILLERKOALA_OLLAMA="${INSTALL_KILLERKOALA_OLLAMA:-auto}" \
        STRICT_KILLERKOALA_OLLAMA="${STRICT_KILLERKOALA_OLLAMA:-0}" \
        KILLERKOALA_LLM_MODEL="${KILLERKOALA_LLM_MODEL:-killerkoala-tinyllama:latest}" \
        bash scripts/setup_killerkoala_ollama.sh
fi

run_step "Restricted K7/K8 power permissions" \
  env KOALABYTE_SERVICE_USER="${SERVICE_USER}" bash scripts/install_power_controls.sh
run_step "Stable device discovery" run_discovery
run_step "K1-K8 GPIO initialization" run_button_probe
run_step "Pi controls and menu contract" run_controls_gate
run_step "Voice, TinyLlama, web research, and display synchronization checks" run_runtime_checks
run_step "Runtime service activation" restart_services

if [[ "${SKIP_AUDIO}" != "1" ]]; then
  run_step "External audio selection" bash scripts/configure_pi_audio_output.sh
fi

run_step "Final Pi hardware doctor" run_final_doctor

write_status "complete" "final_one_shot" "Pi packages, headless K1-K8 controls, restricted power permissions, USB aliases, Waveshare local vocabulary, TinyLlama fallback, optional web research, Australian TTS, tone-synchronized displays, audio, menu, BLE, voice, live display sync, diagnostics, and optional SocketCAN responsibilities installed without firmware flashing"
trap - ERR

echo
echo "KoalaByte Blue final Raspberry Pi one-shot installation complete."
echo "Status: ${STATUS_PATH}"
echo "TinyLlama status: logs/killerkoala/ollama_setup_status.json"
echo "Last AI response: logs/killerkoala/killerkoala_last_companion_response.json"
echo "Web research: logs/killerkoala/web_research/latest.json"
echo "Device map: logs/preflight/koalabyte_ports.json"
echo "GPIO status: logs/gpio_buttons/gpio_button_status.json"
echo "Headless runtime: logs/runtime/headless_menu_status.json"
echo "Hardware report: logs/pi_hardware/pi_hardware_doctor.json"
echo
echo "Reboot once after the first install so ${SERVICE_USER} receives all hardware group memberships."
