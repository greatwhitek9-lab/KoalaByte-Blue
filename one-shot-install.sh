#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT}"

CHECK_ONLY=0
SKIP_PACKAGES=0
SKIP_AUDIO=0
SKIP_CAN=0
SKIP_AI=0
SKIP_MUSIC=0
SKIP_FIRMWARE=0
FIRMWARE_BUILD_ONLY=0
USE_EXISTING_FIRMWARE_BUNDLE=0
CLEANUP_FIRMWARE_BUILD_TOOLS="${CLEANUP_FIRMWARE_BUILD_TOOLS:-1}"
SERVICE_USER="${KOALABYTE_SERVICE_USER:-${SUDO_USER:-${USER:-pi}}}"
STATUS_PATH="${KOALABYTE_ONE_SHOT_STATUS_PATH:-logs/one_shot/final_install_status.json}"
PYTHON_BIN="${ROOT}/pi-companion/.venv/bin/python"
INSTALL_INNOMAKER_CAN="${INSTALL_INNOMAKER_CAN:-auto}"
KOALABYTE_TMPDIR="${KOALABYTE_TMPDIR:-${HOME}/.cache/koalabyte/tmp}"
RUNTIME_HEALTH_TIMEOUT="${KOALABYTE_RUNTIME_HEALTH_TIMEOUT:-45}"

mkdir -p "${KOALABYTE_TMPDIR}"
export TMPDIR="${KOALABYTE_TMPDIR}"
export TMP="${KOALABYTE_TMPDIR}"
export TEMP="${KOALABYTE_TMPDIR}"

usage() {
  cat <<'EOF'
KoalaByte Blue complete whole-system one-shot deployment

Usage:
  bash one-shot-install.sh
  bash one-shot-install.sh --check-only

Options:
  --check-only                   Validate the complete source/deployment contract
  --skip-packages                Reuse existing Pi packages and Python environment
  --skip-audio                   Do not select an external Pi audio sink
  --skip-can                     Do not configure optional SocketCAN
  --skip-ai                      Do not install the local TinyLlama model
  --skip-music                   Do not install the Mopidy music engine
  --skip-firmware                Provision only the Pi; do not build or flash peripherals
  --firmware-build-only          Build/checksum firmware but do not flash it
  --use-existing-firmware-bundle Flash releases/koalabyte-blue-current without rebuilding
  --keep-build-tools             Retain NCS, Zephyr SDK, west, and PlatformIO after success

Run as the normal SSH/login user, not with `sudo bash`; privileged stages request
sudo internally. The default transaction verifies runtime service stability and
exclusive ESP32/Heltec serial ownership before cleanup or success is reported.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only|--dry-run) CHECK_ONLY=1 ;;
    --skip-packages) SKIP_PACKAGES=1 ;;
    --skip-audio) SKIP_AUDIO=1 ;;
    --skip-can) SKIP_CAN=1 ;;
    --skip-ai) SKIP_AI=1 ;;
    --skip-music) SKIP_MUSIC=1 ;;
    --skip-firmware) SKIP_FIRMWARE=1 ;;
    --firmware-build-only) FIRMWARE_BUILD_ONLY=1 ;;
    --use-existing-firmware-bundle) USE_EXISTING_FIRMWARE_BUNDLE=1 ;;
    --keep-build-tools) CLEANUP_FIRMWARE_BUILD_TOOLS=0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

mkdir -p logs/one_shot logs/deployment logs/preflight logs/pi_hardware \
  logs/gpio_buttons logs/runtime logs/killerkoala logs/ble_nodes logs/music_player

enabled() {
  case "$1" in 1|true|True|yes|YES|on|ON|auto|AUTO) return 0 ;; *) return 1 ;; esac
}

write_status() {
  local status="$1" step="$2" reason="$3"
  python3 - "${STATUS_PATH}" "${status}" "${step}" "${reason}" \
    "${CHECK_ONLY}" "${SERVICE_USER}" "${SKIP_AI}" "${SKIP_MUSIC}" \
    "${SKIP_FIRMWARE}" "${FIRMWARE_BUILD_ONLY}" "${CLEANUP_FIRMWARE_BUILD_TOOLS}" \
    "${KOALABYTE_TMPDIR}" <<'PY'
import json, sys, time
from pathlib import Path
(path, status, step, reason, check_only, service_user, skip_ai, skip_music,
 skip_firmware, build_only, cleanup_tools, temp_dir) = sys.argv[1:]
firmware_enabled = skip_firmware != "1"
Path(path).write_text(json.dumps({
    "status": status,
    "step": step,
    "reason": reason,
    "check_only": check_only == "1",
    "service_user": service_user,
    "runtime_mode": "headless_pi_os_lite",
    "persistent_temp_dir": temp_dir,
    "firmware_flashing": firmware_enabled and build_only != "1",
    "firmware_build": firmware_enabled,
    "firmware_targets": ["heltec-t114-uf2", "waveshare-esp32-s3-dualeye"],
    "firmware_bundle": "releases/koalabyte-blue-current",
    "build_tool_cleanup_requested": cleanup_tools.lower() in {"1", "true", "yes", "on", "auto"},
    "ai_setup_skipped": skip_ai == "1",
    "music_setup_skipped": skip_music == "1",
    "local_ai_model": "killerkoala-tinyllama:latest",
    "music_engine": "mopidy",
    "ble_roles": "heltec_primary_pi_bluez_preferred_esp32_guarded_fallback",
    "serial_ownership": "esp32_voice_bridge_and_heltec_ble_manager",
    "runtime_health_gate": True,
    "error_lifecycle": "purple_green_alarm_then_heltec_mouth_and_pi_dig",
    "can_transmit_during_install": False,
    "innomaker_stock_firmware_preserved": True,
    "updated_at": time.time(),
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

run_step() {
  local name="$1"; shift
  echo
  echo "== ${name} =="
  write_status running "${name}" "step started"
  "$@"
  write_status ok "${name}" "step completed"
}

python_for_runtime() {
  [[ -x "${PYTHON_BIN}" ]] && printf '%s\n' "${PYTHON_BIN}" || printf '%s\n' python3
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
  local script
  for script in \
    one-shot-install.sh install.sh \
    scripts/setup_pi_hardware_stage.sh scripts/setup_system_packages.sh \
    scripts/setup_killerkoala_ollama.sh scripts/setup_mopidy_player.sh \
    scripts/install_power_controls.sh scripts/install_koalabyte_boot_services.sh \
    scripts/install_ble_node_manager_service.sh scripts/install_esp32_dualeye_voice_bridge_service.sh \
    scripts/install_koalabyte_udev_rules.sh scripts/configure_pi_audio_output.sh \
    scripts/build_whole_system_firmware.sh scripts/deploy_whole_system_firmware.sh \
    scripts/flash_t114_current_uf2.sh scripts/flash_esp32_dualeye_current.sh \
    scripts/enter_t114_uf2_bootloader.sh scripts/preflight_firmware_host.sh \
    scripts/ensure_build_swap.sh scripts/cleanup_firmware_build_tools.sh; do
    bash -n "${script}"
  done
  python3 -m py_compile \
    scripts/run_headless_menu.py scripts/run_esp32_dualeye_voice_bridge.py \
    scripts/run_ble_node_manager.py scripts/setup_gpio_buttons.py scripts/test_gpio_buttons.py \
    scripts/pi_hardware_doctor.py scripts/discover_koalabyte_ports.py \
    scripts/check_serial_command_bus.py scripts/check_one_shot_controls.py \
    scripts/check_whole_system_deployment.py scripts/check_killerkoala_ai.py \
    scripts/check_ble_role_failover.py scripts/check_killerkoala_error_sequence.py \
    scripts/check_music_player.py scripts/check_full_runtime_dependencies.py \
    pi-companion/koalablue/gpio_buttons.py pi-companion/koalablue/ble_role_coordinator.py \
    pi-companion/koalablue/ble_node_manager.py pi-companion/koalablue/dualeye_tts.py \
    pi-companion/koalablue/serial_command_bus.py \
    pi-companion/koalablue/runtime_serial_ownership.py \
    pi-companion/koalablue/killerkoala_expression.py \
    pi-companion/koalablue/killerkoala_hybrid_companion.py \
    pi-companion/koalablue/killerkoala_voice_control.py \
    pi-companion/koalablue/esp32_dualeye_speech_synced_bridge.py \
    pi-companion/koalablue/mopidy_player.py pi-companion/koalablue/music_player.py \
    pi-companion/koalablue/music_speech_duck.py
  PYTHONPATH=pi-companion python3 scripts/check_serial_command_bus.py >/dev/null
}

run_discovery() {
  PYTHONPATH=pi-companion "$(python_for_runtime)" scripts/discover_koalabyte_ports.py \
    --profile heltec --output-dir logs/preflight
}
run_button_probe() {
  PYTHONPATH=pi-companion STRICT_GPIO_BUTTONS="${STRICT_GPIO_BUTTONS:-0}" \
    "$(python_for_runtime)" scripts/setup_gpio_buttons.py --probe
}
run_runtime_checks() {
  local py
  py="$(python_for_runtime)"
  PYTHONPATH=pi-companion "${py}" scripts/check_serial_command_bus.py
  PYTHONPATH=pi-companion "${py}" scripts/check_one_shot_controls.py
  PYTHONPATH=pi-companion "${py}" scripts/check_killerkoala_ai.py
  PYTHONPATH=pi-companion KOALABYTE_MENU_SYNC=0 "${py}" scripts/check_menu_display_sync.py
  PYTHONPATH=pi-companion "${py}" scripts/check_menu_actions.py
  PYTHONPATH=pi-companion "${py}" scripts/check_killerkoala_face_mouth_sync.py
  PYTHONPATH=pi-companion "${py}" scripts/check_ble_role_failover.py
  PYTHONPATH=pi-companion "${py}" scripts/check_killerkoala_error_sequence.py
  PYTHONPATH=pi-companion "${py}" scripts/check_music_player.py
  INSTALL_INNOMAKER_CAN="${INSTALL_INNOMAKER_CAN}" \
    PYTHONPATH=pi-companion "${py}" scripts/check_full_runtime_dependencies.py
}

restart_services() {
  command -v systemctl >/dev/null 2>&1 || return 0
  local sudo_cmd=() service
  [[ "${EUID}" -ne 0 ]] && sudo_cmd=(sudo)
  "${sudo_cmd[@]}" systemctl daemon-reload
  for service in ollama.service mopidy.service koalabyte-menu.service \
    koalabyte-doctor.service koalabyte-ble-node-manager.service \
    koalabyte-dualeye-voice-bridge.service koalabyte-swap.service; do
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

verify_runtime_services() {
  command -v systemctl >/dev/null 2>&1 || {
    echo "systemctl is required for runtime health verification." >&2
    return 1
  }
  local sudo_cmd=() deadline now service failed=0
  [[ "${EUID}" -ne 0 ]] && sudo_cmd=(sudo)
  required=(
    koalabyte-menu.service
    koalabyte-doctor.service
  )
  if [[ "${SKIP_FIRMWARE}" != "1" && "${FIRMWARE_BUILD_ONLY}" != "1" ]]; then
    required+=(koalabyte-ble-node-manager.service koalabyte-dualeye-voice-bridge.service)
  fi
  [[ "${SKIP_AI}" == "1" ]] || required+=(ollama.service)
  [[ "${SKIP_MUSIC}" == "1" ]] || required+=(mopidy.service)
  can_enabled && required+=(koalabyte-can0.service)

  deadline=$(( $(date +%s) + RUNTIME_HEALTH_TIMEOUT ))
  while (( $(date +%s) < deadline )); do
    failed=0
    for service in "${required[@]}"; do
      "${sudo_cmd[@]}" systemctl is-active --quiet "${service}" || failed=1
    done
    if [[ "${SKIP_FIRMWARE}" != "1" && "${FIRMWARE_BUILD_ONLY}" != "1" ]]; then
      [[ -S logs/runtime/serial_bus/esp32.sock ]] || failed=1
      [[ -S logs/runtime/serial_bus/heltec.sock ]] || failed=1
    fi
    [[ "${failed}" == "0" ]] && break
    sleep 1
  done

  failed=0
  for service in "${required[@]}"; do
    if ! "${sudo_cmd[@]}" systemctl is-active --quiet "${service}"; then
      echo "Runtime service is not active: ${service}" >&2
      "${sudo_cmd[@]}" systemctl --no-pager --full status "${service}" >&2 || true
      "${sudo_cmd[@]}" journalctl -u "${service}" -n 40 --no-pager >&2 || true
      failed=1
    fi
  done
  if [[ "${SKIP_FIRMWARE}" != "1" && "${FIRMWARE_BUILD_ONLY}" != "1" ]]; then
    for target in esp32 heltec; do
      if [[ ! -S "logs/runtime/serial_bus/${target}.sock" ]]; then
        echo "Serial owner socket did not become ready: logs/runtime/serial_bus/${target}.sock" >&2
        failed=1
      fi
    done
  fi
  [[ "${failed}" == "0" ]]
}

run_final_doctor() {
  set +e
  INSTALL_INNOMAKER_CAN="${INSTALL_INNOMAKER_CAN}" \
    "$(python_for_runtime)" scripts/pi_hardware_doctor.py \
    --can-interface "${CAN_INTERFACE:-can0}" --gpio-live
  local rc=$?
  set -e
  [[ "${rc}" -eq 0 ]] || echo "Hardware doctor recorded optional/disconnected hardware warnings."
  return 0
}

run_cleanup() {
  if [[ "${SKIP_FIRMWARE}" == "1" || "${FIRMWARE_BUILD_ONLY}" == "1" ]]; then
    echo "Build-tool cleanup skipped because no complete firmware flash occurred."
    return 0
  fi
  if ! enabled "${CLEANUP_FIRMWARE_BUILD_TOOLS}"; then
    echo "Firmware build toolchains retained by configuration."
    return 0
  fi
  if ! bash scripts/cleanup_firmware_build_tools.sh; then
    echo "warning: deployment succeeded, but build-tool cleanup was incomplete" >&2
    return 0
  fi
}

trap 'write_status failed final_one_shot "deployment stopped before completion"' ERR
run_step "Source and deployment validation" validate_sources

if [[ "${CHECK_ONLY}" == "1" ]]; then
  run_step "Whole-system firmware deployment contract" bash scripts/deploy_whole_system_firmware.sh --check-only
  run_step "Restricted K7/K8 power permissions" env KOALABYTE_SERVICE_USER="${SERVICE_USER}" bash scripts/install_power_controls.sh --check-only
  run_step "Pi hardware inventory" env INSTALL_INNOMAKER_CAN="${INSTALL_INNOMAKER_CAN}" bash scripts/setup_pi_hardware_stage.sh --check-only
  [[ "${SKIP_AI}" == "1" ]] || run_step "TinyLlama installer contract" bash scripts/setup_killerkoala_ollama.sh --check-only
  [[ "${SKIP_MUSIC}" == "1" ]] || run_step "Mopidy installer contract" bash scripts/setup_mopidy_player.sh --check-only
  run_step "Control, AI, music, BLE, alarm, display, and serial ownership contracts" run_runtime_checks
  run_step "Audio readiness" bash scripts/configure_pi_audio_output.sh --check-only
  write_status complete whole_system_check "Complete source and runtime contracts validated."
  trap - ERR
  echo "KoalaByte whole-system one-shot check passed."
  exit 0
fi

[[ "$(uname -s)" == "Linux" ]] || { echo "Run deployment on the Raspberry Pi Linux host." >&2; exit 1; }
echo "Persistent temporary directory: ${KOALABYTE_TMPDIR}"
df -h "${KOALABYTE_TMPDIR}"

prereq_args=()
[[ "${SKIP_PACKAGES}" == "1" ]] && prereq_args+=(--skip-packages)
[[ "${SKIP_AUDIO}" == "1" ]] && prereq_args+=(--skip-audio)
can_enabled || prereq_args+=(--skip-can-service)
run_step "Raspberry Pi prerequisites and stable device rules" \
  env KOALABYTE_SERVICE_USER="${SERVICE_USER}" \
      CAN_INTERFACE="${CAN_INTERFACE:-can0}" CAN_BITRATE="${CAN_BITRATE:-500000}" \
      bash scripts/setup_pi_hardware_stage.sh "${prereq_args[@]}"

if [[ "${SKIP_FIRMWARE}" != "1" ]]; then
  firmware_args=(--keep-build-tools)
  [[ "${FIRMWARE_BUILD_ONLY}" == "1" ]] && firmware_args+=(--build-only)
  [[ "${USE_EXISTING_FIRMWARE_BUNDLE}" == "1" ]] && firmware_args+=(--use-existing-bundle)
  run_step "Build and flash current T114 and ESP32 firmware" \
    env KOALABYTE_REQUIRE_ALL_PERIPHERALS="${KOALABYTE_REQUIRE_ALL_PERIPHERALS:-1}" \
        KOALABYTE_DEFER_SERVICE_RESTART=1 CLEANUP_FIRMWARE_BUILD_TOOLS=0 \
        bash scripts/deploy_whole_system_firmware.sh "${firmware_args[@]}"
fi

[[ "${SKIP_AI}" == "1" ]] || run_step "Local KillerKoala TinyLlama model" \
  env INSTALL_KILLERKOALA_OLLAMA="${INSTALL_KILLERKOALA_OLLAMA:-auto}" \
      STRICT_KILLERKOALA_OLLAMA="${STRICT_KILLERKOALA_OLLAMA:-0}" \
      KILLERKOALA_LLM_MODEL="${KILLERKOALA_LLM_MODEL:-killerkoala-tinyllama:latest}" \
      bash scripts/setup_killerkoala_ollama.sh

[[ "${SKIP_MUSIC}" == "1" ]] || run_step "Pi-owned Mopidy music player" \
  env INSTALL_MOPIDY_PLAYER="${INSTALL_MOPIDY_PLAYER:-auto}" \
      STRICT_MOPIDY_PLAYER="${STRICT_MOPIDY_PLAYER:-0}" \
      bash scripts/setup_mopidy_player.sh

run_step "Restricted K7/K8 power permissions" \
  env KOALABYTE_SERVICE_USER="${SERVICE_USER}" bash scripts/install_power_controls.sh

service_args=(--skip-packages --skip-venv --skip-audio --install-runtime-services)
can_enabled || service_args+=(--skip-can-service)
run_step "Install final runtime services" \
  env KOALABYTE_SERVICE_USER="${SERVICE_USER}" \
      CAN_INTERFACE="${CAN_INTERFACE:-can0}" CAN_BITRATE="${CAN_BITRATE:-500000}" \
      bash scripts/setup_pi_hardware_stage.sh "${service_args[@]}"

run_step "Post-deployment device discovery" run_discovery
run_step "K1-K8 GPIO initialization" run_button_probe
run_step "Control, AI, music, BLE, alarm, and display verification" run_runtime_checks
run_step "Runtime service activation" restart_services
run_step "Runtime service health and serial ownership" verify_runtime_services
[[ "${SKIP_AUDIO}" == "1" ]] || run_step "External audio selection" bash scripts/configure_pi_audio_output.sh
run_step "Final Pi hardware doctor" run_final_doctor
run_step "Remove firmware-only build toolchains" run_cleanup

write_status complete whole_system_deployment "Firmware and Pi runtime deployed, services stable, serial ownership verified, and build tools cleaned according to policy."
trap - ERR

cat <<EOF

KoalaByte Blue whole-system one-shot deployment complete.
Status: ${STATUS_PATH}
Firmware bundle: releases/koalabyte-blue-current/manifest.json
Firmware deployment: logs/deployment/whole_system_deployment_status.json
Build cleanup: logs/deployment/build_tool_cleanup_status.json
Host preflight: logs/preflight/firmware_host_preflight.json
Build swap: logs/preflight/build_swap.json
TinyLlama: logs/killerkoala/ollama_setup_status.json
Music: logs/music_player/mopidy_setup_status.json
BLE roles: logs/ble_nodes/ble_role_election.json
Device map: logs/preflight/koalabyte_ports.json
Serial owners: logs/runtime/serial_bus/esp32.sock and heltec.sock

Reboot once after the first installation so ${SERVICE_USER} receives all hardware group memberships.
EOF
