#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

CHECK_ONLY=0
INSTALL_PACKAGES=1
INSTALL_VENV=1
INSTALL_RUNTIME_SERVICES=0
INSTALL_CAN_SERVICE=1
CONFIGURE_AUDIO=1
CAN_INTERFACE="${CAN_INTERFACE:-can0}"
CAN_BITRATE="${CAN_BITRATE:-500000}"
SERVICE_USER="${KOALABYTE_SERVICE_USER:-${SUDO_USER:-${USER:-pi}}}"
PYTHON_BIN="${ROOT}/pi-companion/.venv/bin/python"

usage() {
  cat <<'EOF'
KoalaByte Raspberry Pi staged hardware setup

This stage prepares the Pi, K1-K8 button board, InnoMaker SocketCAN adapter,
audio runtime, stable USB rules, and diagnostic tooling. It does not flash the
ESP32-S3 or Heltec and does not run the final one-shot installer.

Usage:
  bash scripts/setup_pi_hardware_stage.sh
  bash scripts/setup_pi_hardware_stage.sh --check-only
  bash scripts/setup_pi_hardware_stage.sh --install-runtime-services
  bash scripts/setup_pi_hardware_stage.sh --can-interface can0 --can-bitrate 500000

Options:
  --check-only                 Validate scripts and inventory the host only
  --skip-packages              Do not run apt package setup
  --skip-venv                  Do not create/update pi-companion/.venv
  --skip-can-service           Do not install koalabyte-can0.service
  --skip-audio                 Do not select an external Pi audio sink
  --install-runtime-services   Install/enable menu, sync, doctor, BLE, and voice services
  --can-interface NAME         SocketCAN interface; default can0
  --can-bitrate RATE           SocketCAN bitrate; default 500000
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only|--dry-run) CHECK_ONLY=1 ;;
    --skip-packages) INSTALL_PACKAGES=0 ;;
    --skip-venv) INSTALL_VENV=0 ;;
    --skip-can-service) INSTALL_CAN_SERVICE=0 ;;
    --skip-audio) CONFIGURE_AUDIO=0 ;;
    --install-runtime-services) INSTALL_RUNTIME_SERVICES=1 ;;
    --can-interface) CAN_INTERFACE="${2:-}"; shift ;;
    --can-bitrate) CAN_BITRATE="${2:-}"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [[ ! "${CAN_BITRATE}" =~ ^[0-9]+$ || "${CAN_BITRATE}" == "0" ]]; then
  echo "Invalid CAN bitrate: ${CAN_BITRATE}" >&2
  exit 2
fi

mkdir -p logs/pi_hardware logs/preflight logs/koala_kan_kommander

echo "== KoalaByte Raspberry Pi staged hardware setup =="
echo "Root: ${ROOT}"
echo "Service user: ${SERVICE_USER}"
echo "CAN: ${CAN_INTERFACE} @ ${CAN_BITRATE}"
echo "Check only: ${CHECK_ONLY}"
echo "Firmware flashing: disabled in this stage"

validate_sources() {
  bash -n scripts/setup_pi_hardware_stage.sh
  bash -n scripts/setup_system_packages.sh
  bash -n scripts/setup_can0.sh
  bash -n scripts/run_can0_service.sh
  bash -n scripts/install_can0_service.sh
  bash -n scripts/configure_pi_audio_output.sh
  python3 -m py_compile scripts/pi_hardware_doctor.py scripts/test_gpio_buttons.py
  PYTHONPATH=pi-companion python3 -m py_compile pi-companion/koalablue/gpio_buttons.py
}

validate_sources

if [[ "${CHECK_ONLY}" == "1" ]]; then
  python3 scripts/pi_hardware_doctor.py --can-interface "${CAN_INTERFACE}" || true
  echo "Check-only stage complete. No packages, groups, services, audio defaults, or firmware were changed."
  exit 0
fi

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This hardware stage must run on the Raspberry Pi Linux host." >&2
  exit 1
fi

if [[ "${EUID}" -eq 0 ]]; then
  sudo_cmd=()
elif command -v sudo >/dev/null 2>&1; then
  sudo_cmd=(sudo)
else
  echo "sudo or root is required for package, group, udev, and service setup." >&2
  exit 1
fi

if [[ "${INSTALL_PACKAGES}" == "1" ]]; then
  bash scripts/setup_system_packages.sh
fi

if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
  echo "Service user does not exist: ${SERVICE_USER}" >&2
  exit 1
fi

available_groups=()
for group in gpio dialout audio video render plugdev; do
  if getent group "${group}" >/dev/null 2>&1; then
    available_groups+=("${group}")
  fi
done
if (( ${#available_groups[@]} > 0 )); then
  group_csv="$(IFS=,; echo "${available_groups[*]}")"
  "${sudo_cmd[@]}" usermod -aG "${group_csv}" "${SERVICE_USER}"
  echo "Added ${SERVICE_USER} to hardware groups: ${available_groups[*]}"
fi

if [[ "${INSTALL_VENV}" == "1" ]]; then
  if [[ ! -d pi-companion/.venv ]]; then
    python3 -m venv --system-site-packages pi-companion/.venv
  fi
  "${PYTHON_BIN}" -m pip install --upgrade pip setuptools wheel
  "${PYTHON_BIN}" -m pip install -r pi-companion/requirements.txt
fi

if [[ -f scripts/install_koalabyte_udev_rules.sh ]]; then
  INSTALL_UDEV_RULES=1 STRICT_UDEV_RULES=1 bash scripts/install_koalabyte_udev_rules.sh
fi

if [[ "${INSTALL_CAN_SERVICE}" == "1" ]]; then
  CAN_INTERFACE="${CAN_INTERFACE}" \
  CAN_BITRATE="${CAN_BITRATE}" \
  CAN_WAIT_SECONDS="${CAN_WAIT_SECONDS:-30}" \
  INSTALL_CAN0_SERVICE=1 \
  STRICT_CAN0_SERVICE=0 \
    bash scripts/install_can0_service.sh

  CAN_INTERFACE="${CAN_INTERFACE}" \
  CAN_BITRATE="${CAN_BITRATE}" \
  CAN_WAIT_SECONDS="${CAN_WAIT_SECONDS:-30}" \
  STRICT_CAN_SETUP=0 \
    bash scripts/setup_can0.sh --interface "${CAN_INTERFACE}" --bitrate "${CAN_BITRATE}"
fi

if [[ "${CONFIGURE_AUDIO}" == "1" ]]; then
  bash scripts/configure_pi_audio_output.sh || true
fi

if [[ "${INSTALL_RUNTIME_SERVICES}" == "1" ]]; then
  KOALABYTE_SERVICE_USER="${SERVICE_USER}" INSTALL_BOOT_SERVICES=1 STRICT_BOOT_SERVICES=1 \
    bash scripts/install_koalabyte_boot_services.sh

  if [[ -f scripts/install_ble_node_manager_service.sh ]]; then
    INSTALL_BLE_NODE_MANAGER_SERVICE=1 bash scripts/install_ble_node_manager_service.sh
  fi
  if [[ -f scripts/install_esp32_dualeye_voice_bridge_service.sh ]]; then
    INSTALL_DUALEYE_VOICE_BRIDGE_SERVICE=1 bash scripts/install_esp32_dualeye_voice_bridge_service.sh
  fi
fi

doctor_python="${PYTHON_BIN}"
if [[ ! -x "${doctor_python}" ]]; then
  doctor_python=python3
fi
"${doctor_python}" scripts/pi_hardware_doctor.py --can-interface "${CAN_INTERFACE}" --gpio-live || true

cat <<EOF

Pi hardware stage complete.

Next hardware validation:
  1. Reboot or log out/in so ${SERVICE_USER} receives new hardware groups.
  2. Run: ${doctor_python} scripts/test_gpio_buttons.py
  3. Plug in the InnoMaker and run:
       CAN_INTERFACE=${CAN_INTERFACE} CAN_BITRATE=${CAN_BITRATE} bash scripts/setup_can0.sh
  4. Inspect:
       ip -details -statistics link show ${CAN_INTERFACE}
       candump ${CAN_INTERFACE}
  5. Re-run:
       ${doctor_python} scripts/pi_hardware_doctor.py --can-interface ${CAN_INTERFACE} --gpio-live

No CAN traffic was transmitted and no firmware was flashed.
EOF
