#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_SYSTEM_PACKAGES="${INSTALL_SYSTEM_PACKAGES:-auto}"
STRICT_SYSTEM_PACKAGES="${STRICT_SYSTEM_PACKAGES:-0}"
CHECK_ONLY=0

usage() {
  cat <<'EOF'
KoalaByte Blue V2 Heltec Edition Raspberry Pi system package setup helper

Usage:
  bash scripts/setup_system_packages.sh
  STRICT_SYSTEM_PACKAGES=1 bash scripts/setup_system_packages.sh
  INSTALL_SYSTEM_PACKAGES=0 bash scripts/setup_system_packages.sh
  bash scripts/setup_system_packages.sh --check-only

Environment:
  INSTALL_SYSTEM_PACKAGES  auto/1/0. Default: auto. Attempts apt install on apt-based systems.
  STRICT_SYSTEM_PACKAGES   1 fails if packages cannot be checked/installed. Default: 0.

Packages covered:
  Python venv/pip/dev headers, build tools, PlatformIO/USB runtime dependencies,
  Heltec T114 USB serial/udev/BlueZ runtime dependencies, nRF/Zephyr helper build
  tools for optional T114 firmware work, WiFi/NetworkManager/wpa_supplicant,
  SD card formatter tools, CAN tools, python-can, kmod/modprobe, SDL2/KMSDRM
  graphics runtime for Pi OS Lite, SQLite, Raspberry Pi GPIO support, AI voice/TTS
  audio support, and GreatWhite Reef TigerShark/Great Wire Shark PCAP review tools.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only)
      CHECK_ONLY=1
      INSTALL_SYSTEM_PACKAGES=0
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

cd "${REPO_ROOT}"

echo "== KoalaByte Blue V2 Heltec Edition system package setup =="
echo "Repository root: ${REPO_ROOT}"
echo "INSTALL_SYSTEM_PACKAGES=${INSTALL_SYSTEM_PACKAGES} STRICT_SYSTEM_PACKAGES=${STRICT_SYSTEM_PACKAGES}"

if [[ "${CHECK_ONLY}" == "1" || "${INSTALL_SYSTEM_PACKAGES}" == "0" ]]; then
  echo "Package installation not attempted."
  exit 0
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "apt-get not found; skipping system package setup on this OS." >&2
  [[ "${STRICT_SYSTEM_PACKAGES}" == "1" ]] && exit 1
  exit 0
fi

if [[ "${EUID}" -eq 0 ]]; then
  apt_runner=(apt-get)
elif command -v sudo >/dev/null 2>&1; then
  apt_runner=(sudo apt-get)
else
  echo "apt-get is available, but this user is not root and sudo was not found." >&2
  [[ "${STRICT_SYSTEM_PACKAGES}" == "1" ]] && exit 1
  exit 0
fi

packages=(
  git python3 python3-venv python3-pip python3-dev python3-gpiozero python3-lgpio
  python3-serial python3-dbus python3-gi python3-httpx
  build-essential pkg-config cmake ninja-build gperf ccache device-tree-compiler
  wget curl xz-utils file make gcc g++ libffi-dev libssl-dev usbutils udev kmod
  util-linux parted dosfstools exfatprogs libusb-1.0-0 libusb-1.0-0-dev
  libsdl2-2.0-0 libdrm2 libgbm1 libegl1 libgl1 libgl1-mesa-dri mesa-utils fonts-dejavu-core
  network-manager wpasupplicant wireless-tools iw dhcpcd-base
  dnsutils iputils-ping bluetooth bluez bluez-tools rfkill sqlite3 iproute2
  picocom minicom screen
  can-utils python3-can gpiod libgpiod2 espeak-ng espeak alsa-utils
  libasound2-plugins pulseaudio-utils portaudio19-dev python3-pyaudio
  tshark wireshark
)

if apt-cache show libasound2t64 >/dev/null 2>&1; then
  packages+=(libasound2t64)
elif apt-cache show libasound2 >/dev/null 2>&1; then
  packages+=(libasound2)
else
  echo "warning: neither libasound2t64 nor libasound2 has an apt candidate on this host" >&2
fi

echo "Installing/checking Raspberry Pi system packages..."
"${apt_runner[@]}" update
"${apt_runner[@]}" install -y "${packages[@]}"

echo "System package setup complete."
if command -v espeak-ng >/dev/null 2>&1; then
  echo "  espeak-ng: $(command -v espeak-ng)"
elif command -v espeak >/dev/null 2>&1; then
  echo "  espeak: $(command -v espeak)"
else
  echo "  warning: no espeak-ng/espeak command found after install attempt" >&2
  [[ "${STRICT_SYSTEM_PACKAGES}" == "1" ]] && exit 1
fi
if command -v lsusb >/dev/null 2>&1; then
  echo "  USB utility lsusb: $(command -v lsusb)"
fi
if command -v udevadm >/dev/null 2>&1; then
  echo "  udevadm: $(command -v udevadm)"
fi
if command -v bluetoothctl >/dev/null 2>&1; then
  echo "  BlueZ bluetoothctl: $(command -v bluetoothctl)"
fi
if command -v tshark >/dev/null 2>&1; then
  echo "  GreatWhite Reef TigerShark/tshark: $(command -v tshark)"
fi
if command -v wireshark >/dev/null 2>&1; then
  echo "  GreatWhite Reef Great Wire Shark/wireshark: $(command -v wireshark)"
fi
if command -v aplay >/dev/null 2>&1; then
  echo "  ALSA aplay: $(command -v aplay)"
fi
if command -v glxinfo >/dev/null 2>&1; then
  echo "  Mesa/OpenGL tools: $(command -v glxinfo)"
fi
if command -v cansend >/dev/null 2>&1; then
  echo "  can-utils cansend: $(command -v cansend)"
fi
if command -v modprobe >/dev/null 2>&1; then
  echo "  kmod modprobe: $(command -v modprobe)"
fi
