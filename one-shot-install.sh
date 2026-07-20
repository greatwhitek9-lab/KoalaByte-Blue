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
SERVICE_USER="${KOALABYTE_SERVICE_USER:-${SUDO_USER:-${USER:-pi}}}"
STATUS_PATH="${KOALABYTE_ONE_SHOT_STATUS_PATH:-logs/one_shot/final_install_status.json}"
PYTHON_BIN="${ROOT}/pi-companion/.venv/bin/python"
INSTALL_INNOMAKER_CAN="${INSTALL_INNOMAKER_CAN:-auto}"

usage() {
  cat <<'EOF'
KoalaByte Blue complete whole-system one-shot deployment

Usage:
  bash one-shot-install.sh
  bash one-shot-install.sh --check-only

Default deployment:
  1. Prepare Raspberry Pi OS Lite packages, Python, udev, GPIO, audio, and tools.
  2. Build the current Heltec T114 UF2 and complete ESP32-S3 image set.
  3. Flash the T114 and ESP32-S3 in the same installer transaction.
  4. Install TinyLlama, web research, Australian TTS, Mopidy music, BLE failover,
     K1-K8 controls, menu/action services, synchronized displays, and diagnostics.
  5. Rediscover and verify both flashed peripherals before completion.

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

Important environment:
  KOALABYTE_SERVICE_USER=<linux-user>
  KOALABYTE_REQUIRE_ALL_PERIPHERALS=1
  ESP32_PORT=/dev/serial/by-id/<esp32>
  KOALABYTE_HELTEC_USB_PORT=/dev/koalabyte-heltec
  T114_UF2_MOUNT=/media/<user>/HT-n5262
  T114_BOOTLOADER_TIMEOUT_SECONDS=45
  INSTALL_KILLERKOALA_OLLAMA=auto|1|0
  STRICT_KILLERKOALA_OLLAMA=0|1
  KILLERKOALA_LLM_MODEL=killerkoala-tinyllama:latest
  KILLERKOALA_WEB_SEARCH=auto|always|off
  INSTALL_MOPIDY_PLAYER=auto|1|0
  STRICT_MOPIDY_PLAYER=0|1
  INSTALL_INNOMAKER_CAN=auto|1|0
  CAN_INTERFACE=can0
  CAN_BITRATE=500000
  STRICT_GPIO_BUTTONS=0|1

The InnoMaker/SocketCAN adapter remains stock firmware and no CAN frames are
transmitted during installation. The default run requires both the T114 and
ESP32-S3 to be connected. First deployment may require one T114 reset double-tap
if its currently installed firmware predates software UF2 entry.
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
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

mkdir -p logs/one_shot logs/deployment logs/preflight logs/pi_hardware \
  logs/gpio_buttons logs/runtime logs/killerkoala logs/ble_nodes logs/music_player

write_status() {
  local status="$1" step="$2" reason="$3"
  python3 - "${STATUS_PATH}" "${status}" "${step}" "${reason}" \
    "${CHECK_ONLY}" "${SERVICE_USER}" "${SKIP_AI}" "${SKIP_MUSIC}" \
    "${SKIP_FIRMWARE}" "${FIRMWARE_BUILD_ONLY}" <<'PY'
import json, sys, time
from pathlib import Path
(path, status, step, reason, check_only, service_user, skip_ai, skip_music,
 skip_firmware, build_only) = sys.argv[1:]
firmware_enabled = skip_firmware != "1"
Path(path).write_text(json.dumps({
    "status": status,
    "step": step,
    "reason": reason,
    "check_only": check_only == "1",
    "service_user": service_user,
    "runtime_mode": "headless_pi_os_lite",
    "firmware_flashing": firmware_enabled and build_only != "1",
    "firmware_build": firmware_enabled,
    "firmware_targets": ["heltec-t114-uf2", "waveshare-esp32-s3-dualeye"],
    "firmware_bundle": "releases/koalabyte-blue-current",
    "ai_setup_skipped": skip_ai == "1",
    "music_setup_skipped": skip_music == "1",
    "local_ai_model": "killerkoala-tinyllama:latest",
    "music_engine": "mopidy",
    "ble_roles": "heltec_primary_pi_bluez_preferred_esp32_guarded_fallback",
    "error_lifecycle": "purple_green_alarm_then_heltec_mouth_and_pi_dig",
    "can_transmit_during_install": False,
    "innomaker_stock_firmware_preserved": True,
    "updated_at": time.time(),
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
  for script in \
    one-shot-install.sh install.sh \
    scripts/setup_pi_hardware_stage.sh scripts/setup_killerkoala_ollama.sh \
    scripts/setup_mopidy_player.sh scripts/install_power_controls.sh \
    scripts/install_koalabyte_boot_services.sh scripts/install_ble_node_manager_service.sh \
    scripts/install_esp32_dualeye_voice_bridge_service.sh scripts/install_koalabyte_udev_rules.sh \
    scripts/configure_pi_audio_output.sh scripts/build_whole_system_firmware.sh \
    scripts/deploy_whole_system_firmware.sh scripts/flash_t114_current_uf2.sh \
    scripts/flash_esp32_dualeye_current.sh scripts/enter_t114_uf2_bootloader.sh; do
    bash -n "${script}"
  done
  python3 -m py_compile \
    scripts/run_headless_menu.py scripts/setup_gpio_buttons.py scripts/test_gpio_buttons.py \
    scripts/pi_hardware_doctor.py scripts/discover_koalabyte_ports.py \
    scripts/check_one_shot_controls.py scripts/check_whole_system_deployment.py \
    scripts/check_killerkoala_ai.py scripts/check_ble_role_failover.py \
    scripts/check_killerkoala_error_sequence.py scripts/check_music_player.py \
    scripts/check_full_runtime_dependencies.py \
    pi-companion/koalablue/gpio_buttons.py pi-companion/koalablue/ble_role_coordinator.py \
    pi-companion/koalablue/ble_node_manager.py pi-companion/koalablue/dualeye_tts.py \
    pi-companion/koalablue/killerkoala_expression.py \
    pi-companion/koalablue/killerkoala_hybrid_companion.py \
    pi-companion/koalablue/killerkoala_voice_control.py \
    pi-companion/koalablue/esp32_dualeye_speech_synced_bridge.py \
    pi-companion/koalablue/mopidy_player.py pi-companion/koalablue/music_player.py \
    pi-companion/koalablue/music_speech_duck.py
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
  local sudo_cmd=()
  [[ "${EUID}" -ne 0 ]] && sudo_cmd=(sudo)
  "${sudo_cmd[@]}" systemctl daemon-reload
  for service in ollama.service mopidy.service koalabyte-menu.service \
    koalabyte-doctor.service koalabyte-ble-node-manager.service \
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
  set +e
  INSTALL_INNOMAKER_CAN="${INSTALL_INNOMAKER_CAN}" \
    "$(python_for_runtime)" scripts/pi_hardware_doctor.py \
    --can-interface "${CAN_INTERFACE:-can0}" --gpio-live
  local rc=$?
  set -e
  [[ "${rc}" -eq 0 ]] || echo "Hardware doctor recorded optional/disconnected hardware warnings."
  return 0
}

trap 'write_status "failed" "final_one_shot" "deployment stopped before completion"' ERR

run_step "Source and deployment validation" validate_sources

if [[ "${CHECK_ONLY}" == "1" ]]; then
  run_step "Whole-system firmware deployment contract" bash scripts/deploy_whole_system_firmware.sh --check-only
  run_step "Restricted K7/K8 power permissions" env KOALABYTE_SERVICE_USER="${SERVICE_USER}" bash scripts/install_power_controls.sh --check-only
  run_step "Pi hardware inventory" env INSTALL_INNOMAKER_CAN="${INSTALL_INNOMAKER_CAN}" bash scripts/setup_pi_hardware_stage.sh --check-only
  [[ "${SKIP_AI}" == "1" ]] || run_step "TinyLlama installer contract" bash scripts/setup_killerkoala_ollama.sh --check-only
  [[ "${SKIP_MUSIC}" == "1" ]] || run_step "Mopidy music installer contract" bash scripts/setup_mopidy_player.sh --check-only
  run_step "Control, AI, music, BLE, alarm, and display contracts" run_runtime_checks
  run_step "Audio readiness" bash scripts/configure_pi_audio_output.sh --check-only
  write_status "complete" "whole_system_check" "Complete Pi, firmware build/flash, AI, music, BLE, controls, displays, and safety contracts validated."
  trap - ERR
  echo "KoalaByte whole-system one-shot check passed."
  exit 0
fi

[[ "$(uname -s)" == "Linux" ]] || { echo "Run the complete deployment on the Raspberry Pi Linux host." >&2; exit 1; }

# Install prerequisites and udev first, but delay runtime services until both
# peripherals have been rebuilt and flashed.
prereq_args=()
[[ "${SKIP_PACKAGES}" == "1" ]] && prereq_args+=(--skip-packages)
[[ "${SKIP_AUDIO}" == "1" ]] && prereq_args+=(--skip-audio)
can_enabled || prereq_args+=(--skip-can-service)
run_step "Raspberry Pi prerequisites and stable device rules" \
  env KOALABYTE_SERVICE_USER="${SERVICE_USER}" \
      CAN_INTERFACE="${CAN_INTERFACE:-can0}" CAN_BITRATE="${CAN_BITRATE:-500000}" \
      bash scripts/setup_pi_hardware_stage.sh "${prereq_args[@]}"

if [[ "${SKIP_FIRMWARE}" != "1" ]]; then
  firmware_args=()
  [[ "${FIRMWARE_BUILD_ONLY}" == "1" ]] && firmware_args+=(--build-only)
  [[ "${USE_EXISTING_FIRMWARE_BUNDLE}" == "1" ]] && firmware_args+=(--use-existing-bundle)
  run_step "Build and flash current T114 and ESP32 firmware" \
    env KOALABYTE_REQUIRE_ALL_PERIPHERALS="${KOALABYTE_REQUIRE_ALL_PERIPHERALS:-1}" \
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
[[ "${SKIP_AUDIO}" == "1" ]] || run_step "External audio selection" bash scripts/configure_pi_audio_output.sh
run_step "Final Pi hardware doctor" run_final_doctor

write_status "complete" "whole_system_deployment" "Current T114 UF2 and ESP32 complete image set deployed; Pi runtime, TinyLlama, web research, Australian TTS, Mopidy, K1-K8, BLE failover, synchronized displays, alarm/dig lifecycle, audio, and diagnostics installed."
trap - ERR

cat <<EOF

KoalaByte Blue whole-system one-shot deployment complete.
Status: ${STATUS_PATH}
Firmware bundle: releases/koalabyte-blue-current/manifest.json
Firmware deployment: logs/deployment/whole_system_deployment_status.json
T114 flash: logs/deployment/t114_flash_status.json
ESP32 flash: logs/deployment/esp32_flash_status.json
TinyLlama: logs/killerkoala/ollama_setup_status.json
Music: logs/music_player/mopidy_setup_status.json
BLE roles: logs/ble_nodes/ble_role_election.json
Device map: logs/preflight/koalabyte_ports.json

Reboot once after the first installation so ${SERVICE_USER} receives all hardware group memberships.
EOF
