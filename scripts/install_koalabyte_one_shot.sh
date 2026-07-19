#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

CHECK_ONLY=0
ESP32_PORT="${ESP32_PORT:-}"
FLASH_ESP32="${FLASH_ESP32:-0}"
NO_MONITOR="${NO_MONITOR:-1}"
FLASH_T114_ON_PLUG="${FLASH_T114_ON_PLUG:-auto}"
STRICT_T114_PLUG_FLASH="${STRICT_T114_PLUG_FLASH:-1}"
T114_PLUG_FLASH_PROFILE="${T114_PLUG_FLASH_PROFILE:-combined-safe}"
HELTEC_UF2_FIRST="${HELTEC_UF2_FIRST:-0}"
INSTALL_INNOMAKER_CAN="${INSTALL_INNOMAKER_CAN:-optional}"
STRICT_INNOMAKER_CAN="${STRICT_INNOMAKER_CAN:-0}"
INSTALL_CAN0_SERVICE="${INSTALL_CAN0_SERVICE:-auto}"
STRICT_CAN0_SERVICE="${STRICT_CAN0_SERVICE:-0}"
INSTALL_BLE_NODE_MANAGER_SERVICE="${INSTALL_BLE_NODE_MANAGER_SERVICE:-auto}"
STRICT_BLE_NODE_MANAGER_SERVICE="${STRICT_BLE_NODE_MANAGER_SERVICE:-0}"
INSTALL_UDEV_RULES="${INSTALL_UDEV_RULES:-auto}"
STRICT_UDEV_RULES="${STRICT_UDEV_RULES:-0}"
INSTALL_BOOT_SERVICES="${INSTALL_BOOT_SERVICES:-auto}"
STRICT_BOOT_SERVICES="${STRICT_BOOT_SERVICES:-0}"
STRICT_T114_STATUS_DASHBOARD="${STRICT_T114_STATUS_DASHBOARD:-0}"
STRICT_FULL_RUNTIME_DEPENDENCIES="${STRICT_FULL_RUNTIME_DEPENDENCIES:-0}"
STRICT_MENU_DISPLAY_SYNC="${STRICT_MENU_DISPLAY_SYNC:-0}"
INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE="${INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE:-auto}"
STRICT_DUALEYE_VOICE_BRIDGE_SERVICE="${STRICT_DUALEYE_VOICE_BRIDGE_SERVICE:-0}"
STRICT_FACE_MOUTH_SYNC="${STRICT_FACE_MOUTH_SYNC:-0}"
STRICT_KILLERKOALA_AI="${STRICT_KILLERKOALA_AI:-0}"
KOALABYTE_LAB_PROFILE="${KOALABYTE_LAB_PROFILE:-owned-lab}"
KOALABYTE_CAN_TRANSMIT_MODE="${KOALABYTE_CAN_TRANSMIT_MODE:-gated-bench}"
KOALABYTE_RF_BLE_TRANSMIT_MODE="${KOALABYTE_RF_BLE_TRANSMIT_MODE:-disabled-during-install}"
STRICT_LAB_TRANSMIT_POLICY="${STRICT_LAB_TRANSMIT_POLICY:-1}"
STATUS_PATH="${KOALABYTE_ONE_SHOT_STATUS_PATH:-logs/one_shot_install_status.json}"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/pi-companion/.venv/bin/python}"

usage() {
  cat <<'EOF'
KoalaByte Blue V2 Heltec Edition full one-shot installer

Run from the repo root after plugging in the Raspberry Pi, ESP32-S3 DualEye,
Heltec T114, and optional InnoMaker CAN kit:

  bash scripts/install_koalabyte_one_shot.sh
  bash scripts/install_koalabyte_one_shot.sh --check-only

Heltec UF2-first full install:

  1. Plug the Heltec T114 into the Pi with a USB-C data cable.
  2. Press RST twice quickly until the HT-n5262 UF2 bootloader volume appears.
  3. Run:

     bash scripts/install_koalabyte_one_shot.sh --heltec-uf2-first

The --heltec-uf2-first mode forces combined-safe T114 flashing through the HT-n5262
UF2 volume and disables serial/west fallback for the Heltec flash step.

This installer validates the repo, prepares the Pi companion environment, checks
KillerKoala AI/voice, flashes ESP32/T114 firmware paths, checks menu/button/touch
controls, validates menu display sync to Heltec and ESP32-S3 DualEye, checks the
jungle/eucalyptus menu theme and text-fit guard, checks menu-managed prompt UI
controls so shell exports are not needed for normal menu actions, checks the
30-second AI face idle return, verifies action-complete AI face return, checks
field readiness helpers, records the owned-lab RF/BLE/CAN transmit policy,
runs KoalaByte Doctor, installs udev/boot-service hooks when available, checks
version/status dashboard helpers, and keeps optional CAN non-fatal unless
STRICT_INNOMAKER_CAN=1 is set.

Lab transmit policy:
  The one-shot installer does not transmit RF, BLE, or CAN traffic during install.
  It records the configured policy in logs/one_shot/lab_transmit_policy.json.
  CAN transmit is limited to the existing gated synthetic bench-simulator path.
  RF/BLE transmit/replay is not performed by the installer and remains disabled
  during setup unless a separate authorized backend implements a bounded action.

Useful env:
  ESP32_PORT=/dev/ttyUSB0
  FLASH_ESP32=0|1   # default 0 preserves the already-flashed DualEye firmware
  KOALABYTE_ESP32_MIC_PORT=/dev/koalabyte-esp32-dualeye
  KOALABYTE_HELTEC_USB_PORT=/dev/koalabyte-heltec
  KOALABYTE_MENU_SYNC=auto|0
  HELTEC_UF2_FIRST=1
  T114_REQUIRE_UF2=1
  T114_FLASH_METHOD=uf2
  T114_PLUG_FLASH_PROFILE=combined-safe|color-mouth|hci-usb
  FLASH_T114_ON_PLUG=auto|1|0
  STRICT_T114_PLUG_FLASH=1|0
  STRICT_T114_STATUS_DASHBOARD=1
  STRICT_FULL_RUNTIME_DEPENDENCIES=1
  STRICT_MENU_DISPLAY_SYNC=1
  STRICT_FACE_MOUTH_SYNC=1
  STRICT_KILLERKOALA_AI=1
  INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE=auto|1|0
  STRICT_DUALEYE_VOICE_BRIDGE_SERVICE=1
  INSTALL_INNOMAKER_CAN=optional|auto|0|1
  STRICT_INNOMAKER_CAN=1
  INSTALL_CAN0_SERVICE=auto|1|0
  STRICT_CAN0_SERVICE=1|0
  KOALABYTE_LAB_PROFILE=owned-lab|authorized-owned-lab|bench-only
  KOALABYTE_CAN_TRANSMIT_MODE=gated-bench|listen-only|disabled
  KOALABYTE_RF_BLE_TRANSMIT_MODE=disabled-during-install|passive-only
  STRICT_LAB_TRANSMIT_POLICY=1|0
  INSTALL_UDEV_RULES=auto|1|0
  STRICT_UDEV_RULES=1
  INSTALL_BOOT_SERVICES=auto|1|0
  STRICT_BOOT_SERVICES=1
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only|--dry-run)
      CHECK_ONLY=1
      ;;
    --heltec-uf2-first|--t114-uf2-first)
      HELTEC_UF2_FIRST=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [[ "${HELTEC_UF2_FIRST}" == "1" ]]; then
  FLASH_T114_ON_PLUG=1
  STRICT_T114_PLUG_FLASH=1
  T114_PLUG_FLASH_PROFILE=combined-safe
  export T114_REQUIRE_UF2=1
  export T114_FLASH_METHOD=uf2
fi

mkdir -p "$(dirname "${STATUS_PATH}")" logs/anteater logs/menu_actions logs/menu_sync logs/can logs/killerkoala logs/killerkoala_face logs/one_shot logs/doctor logs/version exports logs/menu_prompts

python_for_checks() {
  if [[ -x "${PYTHON_BIN}" ]]; then
    printf '%s\n' "${PYTHON_BIN}"
  else
    printf '%s\n' "python3"
  fi
}

write_status() {
  local status="$1"
  local step="$2"
  local reason="$3"
  python3 - <<'PY' "${STATUS_PATH}" "${status}" "${step}" "${reason}" "${T114_PLUG_FLASH_PROFILE}" "${INSTALL_INNOMAKER_CAN}" "${CHECK_ONLY}" "${HELTEC_UF2_FIRST}" "${KOALABYTE_LAB_PROFILE}" "${KOALABYTE_CAN_TRANSMIT_MODE}" "${KOALABYTE_RF_BLE_TRANSMIT_MODE}"
import json, sys, time
path, status, step, reason, profile, can_mode, check_only, heltec_uf2_first, lab_profile, can_tx_mode, rf_ble_tx_mode = sys.argv[1:]
payload = {
    "status": status,
    "step": step,
    "reason": reason,
    "heltec_profile": profile,
    "heltec_uf2_first": heltec_uf2_first == "1",
    "innomaker_can_mode": can_mode,
    "innomaker_can_required": False,
    "check_only": check_only == "1",
    "lab_profile": lab_profile,
    "can_transmit_mode": can_tx_mode,
    "rf_ble_transmit_mode": rf_ble_tx_mode,
    "installer_transmits_during_setup": False,
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
  if [[ -d "/sys/class/net/${interface}" ]] || compgen -G "/sys/class/net/can*" >/dev/null; then
    return 0
  fi
  if command -v lsusb >/dev/null 2>&1 && lsusb | grep -Eiq 'innomaker|usb.?can|canable|candle|gs[_ -]?usb|slcan|lawicel'; then
    return 0
  fi
  [[ "${INSTALL_INNOMAKER_CAN}" == "1" || "${STRICT_INNOMAKER_CAN}" == "1" ]]
}

write_innomaker_can_status() {
  local status="$1"
  local detected="$2"
  local note="$3"
  local setup_rc="${4:-null}"
  local manifest_rc="${5:-null}"
  local inventory_rc="${6:-null}"
  local status_rc="${7:-null}"
  local service_rc="${8:-null}"
  local interface="${CAN_INTERFACE:-can0}"
  local can_interfaces=""
  can_interfaces="$(find /sys/class/net -maxdepth 1 -type l -name 'can*' -printf '%f ' 2>/dev/null || true)"
  python3 - <<'PY' "logs/can/innomaker_optional_status.json" "${status}" "${detected}" "${interface}" "${can_interfaces}" "${setup_rc}" "${manifest_rc}" "${inventory_rc}" "${status_rc}" "${service_rc}" "${note}"
import json, sys, time
path, status, detected, interface, can_interfaces, setup_rc, manifest_rc, inventory_rc, status_rc, service_rc, note = sys.argv[1:]
def rc(value):
    return None if value == "null" else int(value)
payload = {
    "status": status,
    "required": False,
    "detected": detected == "true",
    "interface": interface,
    "can_interfaces": [item for item in can_interfaces.split() if item],
    "setup_rc": rc(setup_rc),
    "manifest_rc": rc(manifest_rc),
    "inventory_rc": rc(inventory_rc),
    "status_rc": rc(status_rc),
    "service_rc": rc(service_rc),
    "persistent_service": "koalabyte-can0.service",
    "note": note,
    "updated_at": time.time(),
}
open(path, "w", encoding="utf-8").write(json.dumps(payload, indent=2, sort_keys=True))
print(json.dumps(payload, sort_keys=True))
PY
}

run_optional_can() {
  case "${INSTALL_INNOMAKER_CAN}" in
    0|false|False|no|NO|skip|SKIP)
      write_innomaker_can_status "OPTIONAL_CAN_SKIPPED_BY_CONFIG" "false" "InnoMaker CAN kit is optional and was skipped by configuration." >/dev/null
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

  if [[ "${CHECK_ONLY}" == "1" ]]; then
    bash -n scripts/setup_can0.sh
    bash -n scripts/run_can0_service.sh
    bash -n scripts/install_can0_service.sh
    write_innomaker_can_status "OPTIONAL_CAN_CHECK_ONLY" "false" "InnoMaker CAN kit is optional. Dry-run validated SocketCAN setup and persistent service scripts without changing the host." >/dev/null
    write_status "ok" "optional_innomaker_can" "optional CAN check-only policy and service scripts validated"
    return 0
  fi

  echo
  echo "== Optional InnoMaker CAN kit readiness =="
  if ! detect_innomaker_can; then
    echo "InnoMaker CAN kit not detected; skipping optional CAN setup."
    write_innomaker_can_status "OPTIONAL_CAN_SKIPPED_NOT_PRESENT" "false" "InnoMaker CAN kit is optional. Adapter was not detected, so setup was skipped and the one-shot installer continued." >/dev/null
    write_status "ok" "optional_innomaker_can" "optional CAN not detected; skipped and continued"
    return 0
  fi

  set +e
  CAN_INTERFACE="${CAN_INTERFACE:-can0}" CAN_BITRATE="${CAN_BITRATE:-500000}" STRICT_CAN_SETUP=0 bash scripts/setup_can0.sh --interface "${CAN_INTERFACE:-can0}" --bitrate "${CAN_BITRATE:-500000}"
  setup_rc=$?
  PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/run_koala_kan_kommander.py manifest --interface "${CAN_INTERFACE:-can0}"
  manifest_rc=$?
  PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/run_koala_kan_kommander.py inventory --interface "${CAN_INTERFACE:-can0}"
  inventory_rc=$?
  PYTHONPATH=pi-companion "${PYTHON_BIN}" scripts/run_koala_kan_kommander.py status --interface "${CAN_INTERFACE:-can0}"
  status_rc=$?
  INSTALL_CAN0_SERVICE="${INSTALL_CAN0_SERVICE}" \
  STRICT_CAN0_SERVICE="${STRICT_CAN0_SERVICE}" \
  CAN_INTERFACE="${CAN_INTERFACE:-can0}" \
  CAN_BITRATE="${CAN_BITRATE:-500000}" \
    bash scripts/install_can0_service.sh
  service_rc=$?
  set -e

  write_innomaker_can_status "OPTIONAL_CAN_READY" "true" "InnoMaker was detected; SocketCAN setup, manifest, inventory, status, and persistent hot-plug service installation were attempted without flashing adapter firmware." "${setup_rc}" "${manifest_rc}" "${inventory_rc}" "${status_rc}" "${service_rc}" >/dev/null
  if [[ "${STRICT_INNOMAKER_CAN}" == "1" && ( "${setup_rc}" != "0" || "${manifest_rc}" != "0" || "${inventory_rc}" != "0" || "${status_rc}" != "0" || "${service_rc}" != "0" ) ]]; then
    echo "STRICT_INNOMAKER_CAN=1 is set and the optional CAN checks failed." >&2
    exit 1
  fi
  write_status "ok" "optional_innomaker_can" "optional CAN detected; SocketCAN setup/checks and persistent service completed or were non-failing"
}

prepare_anteater_status() {
  local py
  py="$(python_for_checks)"
  PYTHONPATH=pi-companion "${py}" - <<'PY'
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
    "safety": {"advertisement_only": True, "no_pairing": True, "no_connections": True, "no_writes": True, "no_live_scan_during_flash": True},
}
Path(DEFAULT_STATUS_PATH).write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(status, sort_keys=True))
PY
  PYTHONPATH=pi-companion "${py}" scripts/run_anteater.py status >/dev/null
}

run_face_mouth_sync() {
  local sync_args=()
  local py
  py="$(python_for_checks)"
  sync_args=(--emit-test)
  if [[ "${STRICT_FACE_MOUTH_SYNC}" == "1" ]]; then
    sync_args+=(--strict-ports)
  fi
  KOALABYTE_ESP32_FACE_PORT="${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-}}" \
  KOALABYTE_HELTEC_USB_PORT="${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-${HELTEC_PORT:-/dev/koalabyte-heltec}}}" \
  PYTHONPATH=pi-companion "${py}" scripts/check_killerkoala_face_mouth_sync.py "${sync_args[@]}"
}

run_killerkoala_ai_readiness() {
  local ai_args=()
  local py
  py="$(python_for_checks)"
  if [[ "${STRICT_KILLERKOALA_AI}" == "1" ]]; then
    ai_args+=(--strict)
  fi
  PYTHONPATH=pi-companion "${py}" scripts/check_killerkoala_ai.py "${ai_args[@]}"
}

run_t114_status_dashboard_readiness() {
  local dashboard_args=()
  local py
  py="$(python_for_checks)"
  if [[ "${STRICT_T114_STATUS_DASHBOARD}" == "1" ]]; then
    dashboard_args+=(--strict-connected)
  fi
  KOALABYTE_HELTEC_USB_PORT="${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-${HELTEC_PORT:-/dev/koalabyte-heltec}}}" \
  PYTHONPATH=pi-companion "${py}" scripts/check_t114_status_dashboard.py "${dashboard_args[@]}"
}

run_full_runtime_dependency_gate() {
  local dependency_args=()
  local py
  py="$(python_for_checks)"
  if [[ "${STRICT_FULL_RUNTIME_DEPENDENCIES}" == "1" ]]; then
    dependency_args+=(--strict-commands)
  fi
  PYTHONPATH=pi-companion "${py}" scripts/check_full_runtime_dependencies.py "${dependency_args[@]}"
}

run_lab_transmit_policy_gate() {
  local policy_path="logs/one_shot/lab_transmit_policy.json"
  python3 - <<'PY' "${policy_path}" "${KOALABYTE_LAB_PROFILE}" "${KOALABYTE_CAN_TRANSMIT_MODE}" "${KOALABYTE_RF_BLE_TRANSMIT_MODE}" "${STRICT_LAB_TRANSMIT_POLICY}" "${CHECK_ONLY}"
import json, sys, time
from pathlib import Path
path, lab_profile, can_mode, rf_ble_mode, strict, check_only = sys.argv[1:]
allowed_lab = {"owned-lab", "authorized-owned-lab", "bench-only"}
allowed_can = {"gated-bench", "listen-only", "disabled"}
allowed_rf_ble = {"disabled-during-install", "passive-only"}
errors = []
if lab_profile not in allowed_lab:
    errors.append(f"Unsupported KOALABYTE_LAB_PROFILE={lab_profile!r}")
if can_mode not in allowed_can:
    errors.append(f"Unsupported KOALABYTE_CAN_TRANSMIT_MODE={can_mode!r}")
if rf_ble_mode not in allowed_rf_ble:
    errors.append(f"Unsupported KOALABYTE_RF_BLE_TRANSMIT_MODE={rf_ble_mode!r}")
payload = {
    "status": "LAB_TRANSMIT_POLICY_OK" if not errors else "LAB_TRANSMIT_POLICY_ERROR",
    "lab_profile": lab_profile,
    "can_transmit_mode": can_mode,
    "rf_ble_transmit_mode": rf_ble_mode,
    "check_only": check_only == "1",
    "installer_transmits_during_setup": False,
    "can_policy": {
        "mode": can_mode,
        "allowed_path": "isolated SocketCAN bench simulator only when backend requires explicit bench simulator and confirmation gates",
        "no_automatic_vehicle_writes": True,
        "no_dtc_clear_or_ecu_coding": True,
        "no_captured_traffic_replay": True,
    },
    "rf_ble_policy": {
        "mode": rf_ble_mode,
        "installer_live_transmit": False,
        "no_pairing_or_writes_during_install": True,
        "no_replay_during_install": True,
    },
    "errors": errors,
    "updated_at": time.time(),
}
Path(path).parent.mkdir(parents=True, exist_ok=True)
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(payload, sort_keys=True))
if errors and strict == "1":
    raise SystemExit(1)
PY
}

run_menu_display_sync_gate() {
  local py
  py="$(python_for_checks)"
  KOALABYTE_MENU_SYNC=0 PYTHONPATH=pi-companion "${py}" scripts/check_menu_display_sync.py
}

run_menu_theme_fit_gate() {
  local py
  py="$(python_for_checks)"
  PYTHONPATH=pi-companion "${py}" scripts/check_menu_theme_fit.py
}

run_menu_prompt_ui_gate() {
  local py
  py="$(python_for_checks)"
  PYTHONPATH=pi-companion "${py}" scripts/check_menu_prompt_ui.py
}

run_field_readiness() {
  local py
  py="$(python_for_checks)"
  PYTHONPATH=pi-companion "${py}" scripts/check_field_readiness.py
}

run_version_handshake() {
  local py
  py="$(python_for_checks)"
  PYTHONPATH=pi-companion "${py}" scripts/check_koalabyte_version_handshake.py
}

run_status_dashboard_json() {
  local py
  py="$(python_for_checks)"
  PYTHONPATH=pi-companion "${py}" scripts/run_koalabyte_status_server.py --json >/dev/null
}

run_doctor_quick() {
  bash scripts/koalabyte_doctor.sh --quick
}

run_release_log_helper_checks() {
  bash -n scripts/export_koalabyte_logs.sh
  bash -n scripts/build_koalabyte_release_package.sh
}

run_udev_install_or_check() {
  if [[ "${CHECK_ONLY}" == "1" ]]; then
    bash scripts/install_koalabyte_udev_rules.sh --check-only
  else
    INSTALL_UDEV_RULES="${INSTALL_UDEV_RULES}" STRICT_UDEV_RULES="${STRICT_UDEV_RULES}" bash scripts/install_koalabyte_udev_rules.sh
  fi
}

run_boot_services_install_or_check() {
  if [[ "${CHECK_ONLY}" == "1" ]]; then
    bash scripts/install_koalabyte_boot_services.sh --check-only
  else
    INSTALL_BOOT_SERVICES="${INSTALL_BOOT_SERVICES}" STRICT_BOOT_SERVICES="${STRICT_BOOT_SERVICES}" bash scripts/install_koalabyte_boot_services.sh
  fi
}

run_dualeye_voice_bridge_service() {
  if [[ "${CHECK_ONLY}" == "1" ]]; then
    bash -n scripts/install_esp32_dualeye_voice_bridge_service.sh
    return 0
  fi
  INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE="${INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE}" \
  STRICT_DUALEYE_VOICE_BRIDGE_SERVICE="${STRICT_DUALEYE_VOICE_BRIDGE_SERVICE}" \
  KOALABYTE_ESP32_MIC_PORT="${KOALABYTE_ESP32_MIC_PORT:-${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-/dev/koalabyte-esp32-dualeye}}}" \
  PYTHON_BIN="${PYTHON_BIN}" bash scripts/install_esp32_dualeye_voice_bridge_service.sh
}

run_esp32_firmware_step() {
  case "${FLASH_ESP32}" in
    0|false|False|no|NO|skip|SKIP)
      echo "Preserving existing ESP32-S3 DualEye firmware; synchronization services remain enabled."
      return 0
      ;;
    1|true|True|yes|YES)
      STRICT_ESP32_TOOLS="${STRICT_ESP32_TOOLS:-1}" \
        bash scripts/setup_esp32_tools.sh
      if [[ -n "${ESP32_PORT}" ]]; then
        ESP32_PORT="${ESP32_PORT}" NO_MONITOR="${NO_MONITOR}" bash scripts/flash_esp32.sh
      else
        NO_MONITOR="${NO_MONITOR}" bash scripts/flash_esp32.sh
      fi
      ;;
    *)
      echo "Unknown FLASH_ESP32=${FLASH_ESP32}. Use 0 to preserve firmware or 1 for an explicit reflash." >&2
      return 2
      ;;
  esac
}

trap 'write_status "failed" "one_shot_install" "one-shot installer exited before completion"' ERR

if [[ "${CHECK_ONLY}" == "1" ]]; then
  run_required "Repo readiness" python3 scripts/check_repo_readiness.py
  run_required "udev rules readiness" run_udev_install_or_check
  run_required "boot service templates readiness" run_boot_services_install_or_check
  run_required "KillerKoala AI and voice readiness" run_killerkoala_ai_readiness
  run_required "Menu display sync and AI-face controls" run_menu_display_sync_gate
  run_required "Jungle menu theme and text fit" run_menu_theme_fit_gate
  run_required "Menu prompt UI controls" run_menu_prompt_ui_gate
  run_required "Menus buttons antennas controls and commands" env PYTHONPATH=pi-companion "$(python_for_checks)" scripts/check_one_shot_controls.py
  run_required "Full runtime dependencies and board helpers" run_full_runtime_dependency_gate
  run_required "Field readiness helpers" run_field_readiness
  run_required "Owned-lab RF BLE CAN transmit policy" run_lab_transmit_policy_gate
  run_required "Version handshake readiness" run_version_handshake
  run_required "Status dashboard JSON check" run_status_dashboard_json
  run_required "Release and log helper checks" run_release_log_helper_checks
  run_required "KoalaByte Doctor quick check" run_doctor_quick
  run_required "External antenna readiness" bash scripts/configure_koalabyte_external_antennas.sh --check-only
  run_optional_can
  write_status "complete" "one_shot_check_only" "dry-run checks complete; no firmware flashing, RF/BLE/CAN transmit, or service install performed"
  trap - ERR
  echo
  echo "KoalaByte Blue V2 Heltec Edition one-shot check-only complete."
  echo "Status: ${STATUS_PATH}"
  exit 0
fi

if [[ "${HELTEC_UF2_FIRST}" == "1" ]]; then
  echo
  echo "== Heltec UF2-first one-shot mode =="
  echo "This run requires the Heltec T114 HT-n5262 bootloader volume before the T114 flash step."
  echo "If it is not visible yet, press RST twice quickly on the T114 before continuing."
fi

run_required "Repo readiness" python3 scripts/check_repo_readiness.py
run_required "udev rules install" run_udev_install_or_check
run_required "Raspberry Pi companion + Heltec combined-safe flash" env FLASH_T114_ON_PLUG="${FLASH_T114_ON_PLUG}" STRICT_T114_PLUG_FLASH="${STRICT_T114_PLUG_FLASH}" T114_PLUG_FLASH_PROFILE="${T114_PLUG_FLASH_PROFILE}" T114_REQUIRE_UF2="${T114_REQUIRE_UF2:-0}" T114_FLASH_METHOD="${T114_FLASH_METHOD:-auto}" bash scripts/install_pi.sh
run_required "KillerKoala AI and voice readiness" run_killerkoala_ai_readiness
run_required "ESP32-S3 DualEye mic voice bridge service" run_dualeye_voice_bridge_service
run_required "ESP32-S3 firmware preservation or explicit flash" run_esp32_firmware_step
run_required "KillerKoala eyes and mouth sync" run_face_mouth_sync
run_required "Menu display sync and AI-face controls" run_menu_display_sync_gate
run_required "Jungle menu theme and text fit" run_menu_theme_fit_gate
run_required "Menu prompt UI controls" run_menu_prompt_ui_gate
run_required "Menus buttons antennas controls and commands" env PYTHONPATH=pi-companion "$(python_for_checks)" scripts/check_one_shot_controls.py
run_required "Full runtime dependencies and board helpers" run_full_runtime_dependency_gate
run_required "Field readiness helpers" run_field_readiness
run_required "Owned-lab RF BLE CAN transmit policy" run_lab_transmit_policy_gate
run_required "Version handshake readiness" run_version_handshake
run_required "Status dashboard JSON check" run_status_dashboard_json
run_required "Release and log helper checks" run_release_log_helper_checks
run_required "KoalaByte Doctor quick check" run_doctor_quick
run_required "BLE node manager service" env KOALABYTE_PRIMARY_BLE_PORT="${KOALABYTE_PRIMARY_BLE_PORT:-${KOALABYTE_HELTEC_USB_PORT:-${HELTEC_PORT:-/dev/koalabyte-heltec}}}" KOALABYTE_HELTEC_USB_PORT="${KOALABYTE_HELTEC_USB_PORT:-${KOALABYTE_PRIMARY_BLE_PORT:-/dev/koalabyte-heltec}}" KOALABYTE_ESP32_FACE_PORT="${KOALABYTE_ESP32_FACE_PORT:-${ESP32_PORT:-}}" KOALABYTE_PI_BLUEZ_NODE="${KOALABYTE_PI_BLUEZ_NODE:-1}" PYTHON_BIN="${PYTHON_BIN}" INSTALL_BLE_NODE_MANAGER_SERVICE="${INSTALL_BLE_NODE_MANAGER_SERVICE}" STRICT_BLE_NODE_MANAGER_SERVICE="${STRICT_BLE_NODE_MANAGER_SERVICE}" bash scripts/install_ble_node_manager_service.sh
run_required "boot services install" run_boot_services_install_or_check
run_required "T114 live dashboard status phrases" run_t114_status_dashboard_readiness
run_required "Didgeridoo/menu action readiness" env PYTHONPATH=pi-companion "$(python_for_checks)" scripts/check_menu_actions.py
run_required "External antenna readiness" bash scripts/configure_koalabyte_external_antennas.sh --check-only
run_required "AntEater passive readiness" prepare_anteater_status
run_optional_can

write_status "complete" "one_shot_install" "Pi, Heltec combined-safe primary BLE/mouth profile, preserved ESP32-S3 firmware, DualEye mic voice bridge, KillerKoala AI/voice, eyes/mouth sync, menu display sync, jungle/eucalyptus menu theme fit, menu-managed prompt UI controls, AI-face idle/action-complete return, udev rules, boot services, version handshake, status dashboard check, release/log helper checks, field readiness helpers, doctor quick check, full runtime dependency gate, live T114 dashboard phrases, controls/commands, services, menu, antenna, passive-readiness, owned-lab RF/BLE/CAN transmit policy, and optional CAN handling complete"
trap - ERR

echo
echo "KoalaByte Blue V2 Heltec Edition one-shot installation complete."
echo "Status: ${STATUS_PATH}"
