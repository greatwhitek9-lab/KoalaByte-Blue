#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${REPO_ROOT}"

CHECK_ONLY=0
case "${1:-}" in
  --check-only|--dry-run) CHECK_ONLY=1; shift ;;
  "") ;;
  -h|--help)
    cat <<'EOF'
KoalaByte Blue complete one-shot installer

Usage:
  bash one-shot-install.sh
  bash one-shot-install.sh --check-only

Default hardware policy:
  - installs/updates all Raspberry Pi software and services
  - validates K1-K8 and external-keyboard control paths
  - configures a connected JBL/USB Pi audio output when detected
  - verifies bundled peripheral images before use
  - flashes ESP32-S3 DualEye v0.9.8 when the release image and port are present
  - flashes T114 only when the HT-n5262 UF2 bootloader volume is present
  - configures InnoMaker as stock-firmware Linux SocketCAN can0

Useful overrides:
  FLASH_ESP32=auto|1|0
  FORCE_ESP32_FLASH=1
  FLASH_T114_ON_PLUG=auto|1|0
  FORCE_T114_FLASH=1
  ESP32_PORT=/dev/koalabyte-esp32-dualeye
  T114_UF2_MOUNT=/media/pi/HT-n5262
  KOALABYTE_AUDIO_SINK_PATTERN='JBL|USB|speaker|audio'
  STRICT_PI_AUDIO_OUTPUT=1
  INSTALL_INNOMAKER_CAN=auto|1|0
EOF
    exit 0
    ;;
  *) echo "Unknown argument: ${1}" >&2; exit 2 ;;
esac

STATUS_PATH="${KOALABYTE_COMPLETE_INSTALL_STATUS:-logs/one_shot/complete_install_status.json}"
mkdir -p "$(dirname "${STATUS_PATH}")"

write_status() {
  local status="$1" step="$2" reason="$3"
  python3 - <<'PY' "${STATUS_PATH}" "${status}" "${step}" "${reason}" "${CHECK_ONLY}"
import json, sys, time
from pathlib import Path
path, status, step, reason, check_only = sys.argv[1:]
payload = {
    "status": status,
    "step": step,
    "reason": reason,
    "check_only": check_only == "1",
    "wake_session_timeout_ms": 10000,
    "voice_wake_phrase_required_while_sleeping": True,
    "trusted_k1_k8_keyboard_activity_wakes_or_refreshes": True,
    "t114_flash_requires_uf2_volume": True,
    "innomaker_firmware_flash": False,
    "updated_at": time.time(),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
PY
}

run_step() {
  local name="$1"; shift
  echo
  echo "== ${name} =="
  write_status "running" "${name}" "step started"
  "$@"
  write_status "ok" "${name}" "step completed"
}

trap 'write_status "failed" "complete_one_shot" "installer stopped before completion"' ERR

run_step "DualEye strict wake-session policy" python3 scripts/check_dualeye_wake_session.py
run_step "Bundled firmware manifest" python3 scripts/verify_prebuilt_firmware_bundle.py
run_step "Pi audio output readiness" bash scripts/configure_pi_audio_output.sh $([[ "${CHECK_ONLY}" == "1" ]] && echo --check-only)

if [[ "${CHECK_ONLY}" == "1" ]]; then
  run_step "Existing Pi one-shot readiness" env FLASH_ESP32=0 FLASH_T114_ON_PLUG=0 bash scripts/install_koalabyte_one_shot.sh --check-only
  run_step "Prebuilt ESP32 flasher syntax" bash -n scripts/flash_prebuilt_esp32_dualeye.sh
  run_step "Prebuilt T114 flasher syntax" bash -n scripts/flash_prebuilt_t114_uf2.sh
  write_status "complete" "complete_one_shot_check" "all source, policy, installer, audio, button/keyboard, and firmware bundle checks completed without flashing"
  trap - ERR
  echo
  echo "KoalaByte Blue complete one-shot check-only passed."
  echo "Status: ${STATUS_PATH}"
  exit 0
fi

# The legacy one-shot remains the comprehensive Pi provisioning engine. Firmware
# replacement is disabled there so this wrapper can use only pinned prebuilt
# images and avoid building NCS/PlatformIO firmware on the Raspberry Pi.
run_step "Raspberry Pi software and services" env \
  FLASH_ESP32=0 \
  FLASH_T114_ON_PLUG=0 \
  INSTALL_INNOMAKER_CAN="${INSTALL_INNOMAKER_CAN:-auto}" \
  INSTALL_CAN0_SERVICE="${INSTALL_CAN0_SERVICE:-auto}" \
  INSTALL_GPIO_BUTTONS="${INSTALL_GPIO_BUTTONS:-auto}" \
  bash scripts/install_koalabyte_one_shot.sh

# Re-evaluate after PipeWire/PulseAudio packages and user services are installed.
run_step "Select JBL or external Pi speaker" bash scripts/configure_pi_audio_output.sh

run_step "Flash or preserve ESP32-S3 DualEye" env \
  FLASH_ESP32="${FLASH_ESP32:-auto}" \
  FORCE_ESP32_FLASH="${FORCE_ESP32_FLASH:-0}" \
  PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/pi-companion/.venv/bin/python}" \
  bash scripts/flash_prebuilt_esp32_dualeye.sh

run_step "Flash or preserve Heltec T114" env \
  FLASH_T114_ON_PLUG="${FLASH_T114_ON_PLUG:-auto}" \
  FORCE_T114_FLASH="${FORCE_T114_FLASH:-0}" \
  STRICT_T114_PLUG_FLASH="${STRICT_T114_PLUG_FLASH:-0}" \
  bash scripts/flash_prebuilt_t114_uf2.sh

if command -v systemctl >/dev/null 2>&1; then
  for service in \
      koalabyte-dualeye-voice-bridge.service \
      koalabyte-menu.service \
      koalabyte-menu-sync.service \
      koalabyte-can0.service; do
    if systemctl list-unit-files "${service}" >/dev/null 2>&1; then
      sudo systemctl restart "${service}" || true
    fi
  done
fi

run_step "Final wake-session policy" python3 scripts/check_dualeye_wake_session.py
run_step "Final controls and button map" env PYTHONPATH=pi-companion "${PYTHON_BIN:-${REPO_ROOT}/pi-companion/.venv/bin/python}" scripts/check_one_shot_controls.py
run_step "Final firmware bundle status" python3 scripts/verify_prebuilt_firmware_bundle.py

write_status "complete" "complete_one_shot" "Pi software, services, K1-K8, keyboard input, JBL/external audio selection, ESP32 wake-session firmware path, T114 UF2 path, and InnoMaker SocketCAN setup completed"
trap - ERR

echo
echo "KoalaByte Blue complete one-shot installation finished."
echo "Status: ${STATUS_PATH}"
echo "ESP32 status: logs/one_shot/esp32_prebuilt_flash_status.json"
echo "T114 status: logs/one_shot/t114_prebuilt_flash_status.json"
echo "Audio status: logs/one_shot/pi_audio_output_status.json"
echo "CAN status: logs/can/innomaker_optional_status.json"
