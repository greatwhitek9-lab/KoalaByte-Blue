#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

ESP32_PORT="${ESP32_PORT:-}"
NO_MONITOR="${NO_MONITOR:-1}"
FLASH_T114_ON_PLUG="${FLASH_T114_ON_PLUG:-auto}"
STRICT_T114_PLUG_FLASH="${STRICT_T114_PLUG_FLASH:-1}"
T114_PLUG_FLASH_PROFILE="${T114_PLUG_FLASH_PROFILE:-color-mouth}"
INSTALL_INNOMAKER_CAN="${INSTALL_INNOMAKER_CAN:-optional}"
STRICT_INNOMAKER_CAN="${STRICT_INNOMAKER_CAN:-0}"
INSTALL_BLE_NODE_MANAGER_SERVICE="${INSTALL_BLE_NODE_MANAGER_SERVICE:-auto}"
STRICT_BLE_NODE_MANAGER_SERVICE="${STRICT_BLE_NODE_MANAGER_SERVICE:-0}"
STRICT_FACE_MOUTH_SYNC="${STRICT_FACE_MOUTH_SYNC:-0}"
STATUS_PATH="${KOALABYTE_ONE_SHOT_STATUS_PATH:-logs/one_shot_install_status.json}"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/pi-companion/.venv/bin/python}"

usage() {
  cat <<'EOF'
KoalaByte Blue V2 Heltec Edition full one-shot installer

Plug in the Pi, ESP32-S3 DualEye, Heltec T114, and optional InnoMaker CAN kit, then run:

  bash scripts/install_koalabyte_one_shot.sh

Required/default actions:
  - prepare Raspberry Pi companion environment
  - generate protocol and antenna readiness artifacts
  - wait for and flash the Heltec T114 selected profile
  - flash the ESP32-S3 DualEye firmware
  - validate ESP32 eyes and Heltec mouth face-state sync
  - validate all menus, submenu routes, button mappings, controls, command helpers, and antenna paths
  - install/start the BLE node manager service
  - validate the Didgeridoo/menu action manifest
  - prepare AntEater passive-readiness status

Optional:
  - InnoMaker CAN kit checks are optional and non-failing by default

Useful env:
  ESP32_PORT=/dev/ttyUSB0
  KOALABYTE_HELTEC_USB_PORT=/dev/koalabyte-heltec
  T114_PLUG_FLASH_PROFILE=color-mouth|hci-usb
  FLASH_T114_ON_PLUG=auto|1|0
  STRICT_T114_PLUG_FLASH=1|0
  STRICT_FACE_MOUTH_SYNC=1
  INSTALL_INNOMAKER_CAN=optional|0|1
  STRICT_INNOMAKER_CAN=1
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

mkdir -p "$(dirname "${STATUS_PATH}")" logs/anteater logs/menu_actions logs/can logs/killerkoala_face logs/one_shot

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

run_optional_can() {
  case "${INSTALL_INNOMAKER_CAN}" in
    0|false|False|no|NO|skip|SKIP)
      echo
      echo "== Optional InnoMaker CAN kit =="
      echo "Skipped by INSTALL_INNOMAKER_CAN=${INSTALL_INNOMAKER_CAN}."
      write_status "ok" "optional_innomaker_can" "optional CAN skipped"
      return 0
      ;;
    optional|auto|AUTO|1|true|True|yes|YES)
      ;;
    *)
      echo "Unknown INSTALL_INNOMAKER_CAN=${INSTALL_INNOMAKER_CAN}. Use optional, 1, or 0." >&2
      exit 2
      ;;
  esac

  echo
  echo "== Optional InnoMaker CAN kit readiness =="
  set +e
  CAN_INTERFACE="${CAN_INTERFACE:-can0}" CAN_BITRATE="${CAN_BITRATE:-500000}" STRICT_CAN_SETUP=0 \
    bash scripts/setup_can0.sh --interface "${CAN_INTERFACE:-can0}" --bitrate "${CAN_BITRATE:-500000}"
  setup_rc=$?
  PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest --interface "${CAN_INTERFACE:-can0}"
  manifest_rc=$?
  PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py inventory --interface "${CAN_INTERFACE:-can0}"
  inventory_rc=$?
  PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py status --interface "${CAN_INTERFACE:-can0}"
  status_rc=$?
  set -e

  cat > logs/can/innomaker_optional_status.json <<JSON
{
  "status": "OPTIONAL_CAN_CHECK_RECORDED",
  "required": false,
  "setup_rc": ${setup_rc},
  "manifest_rc": ${manifest_rc},
  "inventory_rc": ${inventory_rc},
  "status_rc": ${status_rc},
  "note": "InnoMaker CAN kit is optional for the one-shot install and must not fail firmware deployment when absent.",
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
  write_status "ok" "optional_innomaker_can" "optional CAN check completed or was non-failing"
}

prepare_anteater_status() {
  PYTHONPATH=pi-companion python3 - <<'PY'
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
  PYTHONPATH=pi-companion python3 scripts/run_anteater.py status >/dev/null
}

run_face_mouth_sync() {
  local sync_args=(--emit-test)
  if [[ "${STRICT_FACE_MOUTH_SYNC}" == "1" ]]; then
    sync_args+=(--strict-ports)
  fi
  KOALABYTE_ESP32_FACE_PORT="${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-}}" \
  KOALABYTE_HELTEC_USB_PORT="${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-${HELTEC_PORT:-/dev/koalabyte-heltec}}}" \
  PYTHONPATH=pi-companion python3 scripts/check_killerkoala_face_mouth_sync.py "${sync_args[@]}"
}

trap 'write_status "failed" "one_shot_install" "one-shot installer exited before completion"' ERR

run_required "Repo readiness" python3 scripts/check_repo_readiness.py

run_required "Raspberry Pi companion + Heltec plug-in flash" \
  env FLASH_T114_ON_PLUG="${FLASH_T114_ON_PLUG}" \
      STRICT_T114_PLUG_FLASH="${STRICT_T114_PLUG_FLASH}" \
      T114_PLUG_FLASH_PROFILE="${T114_PLUG_FLASH_PROFILE}" \
      bash scripts/install_pi.sh

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
run_required "Menus buttons antennas controls and commands" env PYTHONPATH=pi-companion python3 scripts/check_one_shot_controls.py

run_required "BLE node manager service" \
  env KOALABYTE_PRIMARY_BLE_PORT="${KOALABYTE_PRIMARY_BLE_PORT:-${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-/dev/koalabyte-heltec}}}" \
      KOALABYTE_HELTEC_USB_PORT="${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-/dev/koalabyte-heltec}}" \
      KOALABYTE_ESP32_FACE_PORT="${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-}}" \
      KOALABYTE_PI_BLUEZ_NODE="${KOALABYTE_PI_BLUEZ_NODE:-1}" \
      PYTHON_BIN="${PYTHON_BIN}" \
      INSTALL_BLE_NODE_MANAGER_SERVICE="${INSTALL_BLE_NODE_MANAGER_SERVICE}" \
      STRICT_BLE_NODE_MANAGER_SERVICE="${STRICT_BLE_NODE_MANAGER_SERVICE}" \
      bash scripts/install_ble_node_manager_service.sh

run_required "Didgeridoo/menu action readiness" env PYTHONPATH=pi-companion python3 scripts/check_menu_actions.py
run_required "External antenna readiness" bash scripts/configure_koalabyte_external_antennas.sh --check-only
run_required "AntEater passive readiness" prepare_anteater_status
run_optional_can

write_status "complete" "one_shot_install" "Pi, Heltec, ESP32-S3, eyes/mouth sync, controls/commands, services, menu, antenna, and passive-readiness steps complete; InnoMaker CAN optional"
trap - ERR

echo
echo "KoalaByte Blue V2 Heltec Edition one-shot installation complete."
echo "Status: ${STATUS_PATH}"
