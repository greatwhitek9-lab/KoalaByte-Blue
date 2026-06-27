#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

ESP32_PORT="${ESP32_PORT:-}"
NO_MONITOR="${NO_MONITOR:-1}"
FLASH_T114_ON_PLUG="${FLASH_T114_ON_PLUG:-auto}"
STRICT_T114_PLUG_FLASH="${STRICT_T114_PLUG_FLASH:-1}"
T114_PLUG_FLASH_PROFILE="${T114_PLUG_FLASH_PROFILE:-combined-safe}"
INSTALL_INNOMAKER_CAN="${INSTALL_INNOMAKER_CAN:-optional}"
STRICT_INNOMAKER_CAN="${STRICT_INNOMAKER_CAN:-0}"
INSTALL_BLE_NODE_MANAGER_SERVICE="${INSTALL_BLE_NODE_MANAGER_SERVICE:-auto}"
STRICT_BLE_NODE_MANAGER_SERVICE="${STRICT_BLE_NODE_MANAGER_SERVICE:-0}"
STRICT_T114_STATUS_DASHBOARD="${STRICT_T114_STATUS_DASHBOARD:-0}"
STRICT_FULL_RUNTIME_DEPENDENCIES="${STRICT_FULL_RUNTIME_DEPENDENCIES:-0}"
INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE="${INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE:-auto}"
STRICT_DUALEYE_VOICE_BRIDGE_SERVICE="${STRICT_DUALEYE_VOICE_BRIDGE_SERVICE:-0}"
STRICT_FACE_MOUTH_SYNC="${STRICT_FACE_MOUTH_SYNC:-0}"
STRICT_KILLERKOALA_AI="${STRICT_KILLERKOALA_AI:-0}"
STATUS_PATH="${KOALABYTE_ONE_SHOT_STATUS_PATH:-logs/one_shot_install_status.json}"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/pi-companion/.venv/bin/python}"

usage() {
  cat <<'EOF'
KoalaByte Blue V2 Heltec Edition full one-shot installer

Plug in the Pi, ESP32-S3 DualEye, Heltec T114, and optional InnoMaker CAN kit, then run:

  bash scripts/install_koalabyte_one_shot.sh

Required/default actions:
  - prepare Raspberry Pi companion environment
  - install/check KillerKoala AI dependencies, phrase engine, optional TinyLlama/Ollama model path, and voice-command routing
  - install/start the ESP32-S3 DualEye built-in mic voice bridge service when systemd is available
  - generate protocol and antenna readiness artifacts
  - wait for and flash the Heltec T114 combined-safe profile
  - flash the ESP32-S3 DualEye firmware
  - validate ESP32 eyes and Heltec mouth face-state sync
  - validate all menus, submenu routes, button mappings, controls, command helpers, and antenna paths
  - validate Python/runtime imports, project modules, board helper files, and optional board command availability
  - install/start the BLE node manager service with Heltec T114 as primary and ESP32/Pi as secondary nodes
  - validate live T114 dashboard status phrases for Heltec Link, Radio/GPS, and Lab Beacon TX
  - validate the Didgeridoo/menu action manifest
  - prepare AntEater passive-readiness status

Optional:
  - InnoMaker CAN kit setup is optional by default
  - if the adapter is present, the installer sets it up and records status
  - if the adapter is absent, the installer writes a skipped status and continues

Useful env:
  ESP32_PORT=/dev/ttyUSB0
  KOALABYTE_ESP32_MIC_PORT=/dev/koalabyte-esp32-dualeye
  KOALABYTE_HELTEC_USB_PORT=/dev/koalabyte-heltec
  T114_PLUG_FLASH_PROFILE=combined-safe|color-mouth|hci-usb
  FLASH_T114_ON_PLUG=auto|1|0
  STRICT_T114_PLUG_FLASH=1|0
  STRICT_T114_STATUS_DASHBOARD=1
  STRICT_FULL_RUNTIME_DEPENDENCIES=1
  STRICT_FACE_MOUTH_SYNC=1
  STRICT_KILLERKOALA_AI=1
  INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE=auto|1|0
  STRICT_DUALEYE_VOICE_BRIDGE_SERVICE=1
  INSTALL_INNOMAKER_CAN=optional|auto|0|1
  STRICT_INNOMAKER_CAN=1
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

mkdir -p "$(dirname "${STATUS_PATH}")" logs/anteater logs/menu_actions logs/can logs/killerkoala logs/killerkoala_face logs/one_shot

write_status() {
  local status="$1"
  local step="$2"
  local reason="$3"
  python3 - <<'PY' "${STATUS_PATH}" "${status}" "${step}" "${reason}" "${T114_PLUG_FLASH_PROFILE}" "${INSTALL_INNOMAKER_CAN}"
import json, sys, time
path, status, step, reason, profile, can_mode = sys.argv[1:]
payload = {
    "status": status,
    "step": step,
    "reason": reason,
    "heltec_profile": profile,
    "innomaker_can_mode": can_mode,
    "innomaker_can_required": False,
    "updated_at": time.time(),
}
open(path, "w", encoding="utf-8").write(json.dumps(payload, indent=2, sort_keys=True))
PY
}

run_required() {
  local step="$1"
  shift
  echo
  echo "== ${step} =="
  write_status "running" "${step}" "required step started"
  "$@"
  write_status "ok" "${step}" "required step completed"
}

detect_innomaker_can() {
  local interface="${CAN_INTERFACE:-can0}"
  if [[ -d "/sys/class/net/${interface}" ]]; then
    return 0
  fi
  if compgen -G "/sys/class/net/can*" >/dev/null; then
    return 0
  fi
  if command -v lsusb >/dev/null 2>&1; then
    if lsusb | grep -Eiq 'innomaker|usb.?can|canable|candle|gs[_ -]?usb|slcan|lawicel'; then
      return 0
    fi
  fi
  if [[ "${INSTALL_INNOMAKER_CAN}" == "1" || "${STRICT_INNOMAKER_CAN}" == "1" ]]; then
    return 0
  fi
  return 1
}

write_innomaker_can_skipped_status() {
  local interface="${CAN_INTERFACE:-can0}"
  local can_interfaces=""
  can_interfaces="$(find /sys/class/net -maxdepth 1 -type l -name 'can*' -printf '%f ' 2>/dev/null || true)"
  python3 - <<'PY' "logs/can/innomaker_optional_status.json" "${interface}" "${can_interfaces}"
import json, sys, time
path, interface, can_interfaces = sys.argv[1:]
payload = {
    "status": "OPTIONAL_CAN_SKIPPED_NOT_PRESENT",
    "required": False,
    "detected": False,
    "interface": interface,
    "can_interfaces": [item for item in can_interfaces.split() if item],
    "setup_rc": None,
    "manifest_rc": None,
    "inventory_rc": None,
    "status_rc": None,
    "note": "InnoMaker CAN kit is optional. Adapter was not detected, so setup was skipped and the one-shot installer continued.",
    "updated_at": time.time(),
}
open(path, "w", encoding="utf-8").write(json.dumps(payload, indent=2, sort_keys=True))
print(json.dumps(payload, sort_keys=True))
PY
}

run_optional_can() {
  case "${INSTALL_INNOMAKER_CAN}" in
    0|false|False|no|NO|skip|SKIP)
      echo
      echo "== Optional InnoMaker CAN kit =="
      echo "Skipped by INSTALL_INNOMAKER_CAN=${INSTALL_INNOMAKER_CAN}."
      write_innomaker_can_skipped_status >/dev/null
      write_status "ok" "optional_innomaker_can" "optional CAN skipped by configuration"
      return 0
      ;;
    optional|auto|AUTO|1|true|True|yes|YES)
      ;;
    *)
      echo "Unknown INSTALL_INNOMAKER_CAN=${INSTALL_INNOMAKER_CAN}. Use optional, auto, 1, or 0." >&2
      exit 2
      ;;
  esac

  echo
  echo "== Optional InnoMaker CAN kit readiness =="

  if ! detect_innomaker_can; then
    echo "InnoMaker CAN kit not detected; skipping optional CAN setup."
    write_innomaker_can_skipped_status >/dev/null
    write_status "ok" "optional_innomaker_can" "optional CAN not detected; skipped and continued"
    return 0
  fi

  echo "InnoMaker CAN kit or CAN interface detected; running optional setup/checks."
  set +e
  CAN_INTERFACE="${CAN_INTERFACE:-can0}" CAN_BITRATE="${CAN_BITRATE:-500000}" STRICT_CAN_SETUP=0 \
    bash scripts/setup_can0.sh --interface "${CAN_INTERFACE:-can0}" --bitrate "${CAN_BITRATE:-500000}"
  setup_rc=$?
  PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/run_koala_kan_kommander.py manifest --interface "${CAN_INTERFACE:-can0}"
  manifest_rc=$?
  PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/run_koala_kan_kommander.py inventory --interface "${CAN_INTERFACE:-can0}"
  inventory_rc=$?
  PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/run_koala_kan_kommander.py status --interface "${CAN_INTERFACE:-can0}"
  status_rc=$?
  set -e

  cat > logs/can/innomaker_optional_status.json <<JSON
{
  "status": "OPTIONAL_CAN_CHECK_RECORDED",
  "required": false,
  "detected": true,
  "interface": "${CAN_INTERFACE:-can0}",
  "setup_rc": ${setup_rc},
  "manifest_rc": ${manifest_rc},
  "inventory_rc": ${inventory_rc},
  "status_rc": ${status_rc},
  "note": "InnoMaker CAN kit is optional for the one-shot install. It was detected, so setup and status checks were attempted.",
  "updated_at": $(date +%s)
}
JSON

  if [[ "${STRICT_INNOMAKER_CAN}" == "1" ]]; then
    if [[ "${setup_rc}" != "0" || "${manifest_rc}" != "0" || "${inventory_rc}" != "0" || "${status_rc}" != "0" ]]; then
      echo "STRICT_INNOMAKER_CAN=1 is set and the optional CAN checks failed." >&2
      exit 1
    fi
  fi
  echo "Optional InnoMaker CAN status written to logs/can/innomaker_optional_status.json"
  write_status "ok" "optional_innomaker_can" "optional CAN detected; setup/checks completed or were non-failing"
}

prepare_anteater_status() {
  PYTHONPATH=pi-companion "${PYTHON_BIN}" - <<'PY'
import json
import time
from pathlib import Path
from koalablue.anteater import ACTION_NAME, DEFAULT_NODE_LOG_PATH, DEFAULT_STATUS_PATH
Path("logs/anteater").mkdir(parents=True, exist_ok=True)
status = {
    "status": "ANTEATER_READY",
    "action_name": ACTION_NAME,
    "updated_at": time.time(),
    "one_shot_installer_check": True,
    "live_scan_started": False,
    "node_log": str(DEFAULT_NODE_LOG_PATH),
    "source": "one-shot-installer-readiness",
    "safety": {
        "advertisement_only": True,
        "no_pairing": True,
        "no_connections": True,
        "no_writes": True,
        "no_live_scan_during_flash": True
    }
}
Path(DEFAULT_STATUS_PATH).write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(status, sort_keys=True))
PY
  PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/run_anteater.py status >/dev/null
}

run_face_mouth_sync() {
  local sync_args=(--emit-test)
  if [[ "${STRICT_FACE_MOUTH_SYNC}" == "1" ]]; then
    sync_args+=(--strict-ports)
  fi
  KOALABYTE_ESP32_FACE_PORT="${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-}}" \
  KOALABYTE_HELTEC_USB_PORT="${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-${HELTEC_PORT:-/dev/koalabyte-heltec}}}" \
  PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_killerkoala_face_mouth_sync.py "${sync_args[@]}"
}

run_killerkoala_ai_readiness() {
  local ai_args=()
  if [[ "${STRICT_KILLERKOALA_AI}" == "1" ]]; then
    ai_args+=(--strict)
  fi
  PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_killerkoala_ai.py "${ai_args[@]}"
}

run_t114_status_dashboard_readiness() {
  local dashboard_args=()
  if [[ "${STRICT_T114_STATUS_DASHBOARD}" == "1" ]]; then
    dashboard_args+=(--strict-connected)
  fi
  KOALABYTE_HELTEC_USB_PORT="${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-${HELTEC_PORT:-/dev/koalabyte-heltec}}}" \
  PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_t114_status_dashboard.py "${dashboard_args[@]}"
}

run_full_runtime_dependency_gate() {
  local dependency_args=()
  if [[ "${STRICT_FULL_RUNTIME_DEPENDENCIES}" == "1" ]]; then
    dependency_args+=(--strict-commands)
  fi
  PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_full_runtime_dependencies.py "${dependency_args[@]}"
}

run_dualeye_voice_bridge_service() {
  INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE="${INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE}" \
  STRICT_DUALEYE_VOICE_BRIDGE_SERVICE="${STRICT_DUALEYE_VOICE_BRIDGE_SERVICE}" \
  KOALABYTE_ESP32_MIC_PORT="${KOALABYTE_ESP32_MIC_PORT:-${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-/dev/koalabyte-esp32-dualeye}}}" \
  PYTHON_BIN="${PYTHON_BIN}" \
    bash scripts/install_esp32_dualeye_voice_bridge_service.sh
}

trap 'write_status "failed" "one_shot_install" "one-shot installer exited before completion"' ERR

run_required "Repo readiness" python3 scripts/check_repo_readiness.py

run_required "Raspberry Pi companion + Heltec combined-safe flash" \
  env FLASH_T114_ON_PLUG="${FLASH_T114_ON_PLUG}" \
      STRICT_T114_PLUG_FLASH="${STRICT_T114_PLUG_FLASH}" \
      T114_PLUG_FLASH_PROFILE="${T114_PLUG_FLASH_PROFILE}" \
      bash scripts/install_pi.sh

run_required "KillerKoala AI and voice readiness" run_killerkoala_ai_readiness
run_required "ESP32-S3 DualEye mic voice bridge service" run_dualeye_voice_bridge_service

run_required "ESP32-S3 DualEye firmware flash" \
  env ESP32_PORT="${ESP32_PORT}" NO_MONITOR="${NO_MONITOR}" STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS:-1}" \
  bash -c '
    STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS}" bash scripts/setup_esp32_tools.sh
    if [[ -n "${ESP32_PORT}" ]]; then
      ESP32_PORT="${ESP32_PORT}" NO_MONITOR="${NO_MONITOR}" bash scripts/flash_esp32.sh
    else
      NO_MONITOR="${NO_MONITOR}" bash scripts/flash_esp32.sh
    fi
  '

run_required "KillerKoala eyes and mouth sync" run_face_mouth_sync
run_required "Menus buttons antennas controls and commands" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_one_shot_controls.py
run_required "Full runtime dependencies and board helpers" run_full_runtime_dependency_gate

run_required "BLE node manager service" \
  env KOALABYTE_PRIMARY_BLE_PORT="${KOALABYTE_PRIMARY_BLE_PORT:-${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-/dev/koalabyte-heltec}}}" \
      KOALABYTE_HELTEC_USB_PORT="${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-/dev/koalabyte-heltec}}" \
      KOALABYTE_ESP32_FACE_PORT="${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-}}" \
      KOALABYTE_PI_BLUEZ_NODE="${KOALABYTE_PI_BLUEZ_NODE:-1}" \
      PYTHON_BIN="${PYTHON_BIN}" \
      INSTALL_BLE_NODE_MANAGER_SERVICE="${INSTALL_BLE_NODE_MANAGER_SERVICE}" \
      STRICT_BLE_NODE_MANAGER_SERVICE="${STRICT_BLE_NODE_MANAGER_SERVICE}" \
      bash scripts/install_ble_node_manager_service.sh

run_required "T114 live dashboard status phrases" run_t114_status_dashboard_readiness
run_required "Didgeridoo/menu action readiness" env PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/check_menu_actions.py
run_required "External antenna readiness" bash scripts/configure_koalabyte_external_antennas.sh --check-only
run_required "AntEater passive readiness" prepare_anteater_status
run_optional_can

write_status "complete" "one_shot_install" "Pi, Heltec combined-safe primary BLE/mouth profile, ESP32-S3, DualEye mic voice bridge, KillerKoala AI/voice, eyes/mouth sync, full runtime dependency gate, live T114 dashboard phrases, controls/commands, services, menu, antenna, passive-readiness, and optional CAN handling complete"
trap - ERR

echo
echo "KoalaByte Blue V2 Heltec Edition one-shot installation complete."
echo "Status: ${STATUS_PATH}"
