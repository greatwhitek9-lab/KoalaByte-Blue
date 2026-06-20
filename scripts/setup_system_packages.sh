#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_SYSTEM_PACKAGES="${INSTALL_SYSTEM_PACKAGES:-auto}"
STRICT_SYSTEM_PACKAGES="${STRICT_SYSTEM_PACKAGES:-0}"
ENABLE_PI_SPI="${ENABLE_PI_SPI:-auto}"
CHECK_ONLY=0

APT_PACKAGES=(
  git
  python3
  python3-venv
  python3-pip
  python3-dev
  python3-gpiozero
  python3-lgpio
  python3-spidev
  build-essential
  pkg-config
  cmake
  ninja-build
  gperf
  ccache
  device-tree-compiler
  wget
  curl
  xz-utils
  file
  make
  gcc
  g++
  libffi-dev
  libssl-dev
  usbutils
  udev
  util-linux
  parted
  dosfstools
  exfatprogs
  libusb-1.0-0
  libusb-1.0-0-dev
  libsdl2-2.0-0
  network-manager
  wpasupplicant
  wireless-tools
  iw
  dhcpcd-base
  dnsutils
  iputils-ping
  bluetooth
  bluez
  bluez-tools
  rfkill
  sqlite3
  iproute2
  can-utils
  gpiod
  libgpiod2
  espeak-ng
  espeak
  alsa-utils
  libasound2
  libasound2-plugins
  pulseaudio-utils
  portaudio19-dev
  python3-pyaudio
)

usage() {
  cat <<'EOF'
KoalaByte Blue Raspberry Pi system package setup helper

Usage:
  bash scripts/setup_system_packages.sh
  STRICT_SYSTEM_PACKAGES=1 bash scripts/setup_system_packages.sh
  INSTALL_SYSTEM_PACKAGES=0 bash scripts/setup_system_packages.sh
  ENABLE_PI_SPI=0 bash scripts/setup_system_packages.sh
  bash scripts/setup_system_packages.sh --check-only

Environment:
  INSTALL_SYSTEM_PACKAGES  auto/1/0. Default: auto. Attempts apt install on apt-based systems.
  STRICT_SYSTEM_PACKAGES   1 fails if packages cannot be checked/installed. Default: 0.
  ENABLE_PI_SPI            auto/1/0. Default: auto. Enables Raspberry Pi SPI with raspi-config when available.

Packages covered:
  Python venv/pip/dev headers, build tools, PlatformIO/USB runtime dependencies,
  nRF/Zephyr helper build tools, WiFi/NetworkManager/wpa_supplicant, BlueZ tools,
  SD card formatter tools, CAN tools, SDL2 runtime, SQLite, USB utilities,
  Raspberry Pi GPIO/SPI support, Didgeridoo LoRa setup support, and AI voice/TTS audio support.

AI voice/TTS packages:
  espeak-ng, espeak, ALSA utilities/plugins, PulseAudio CLI utilities,
  PortAudio dev files, and python3-pyaudio. macOS 'say' is not installed here;
  it remains an automatic fallback only on systems where Apple already provides it.
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

install_enabled() {
  case "${INSTALL_SYSTEM_PACKAGES}" in
    1|true|True|yes|YES|auto|AUTO) return 0 ;;
    *) return 1 ;;
  esac
}

strict_enabled() {
  [[ "${STRICT_SYSTEM_PACKAGES}" == "1" ]]
}

spi_enable_enabled() {
  case "${ENABLE_PI_SPI}" in
    0|false|False|no|NO|skip|SKIP) return 1 ;;
    *) return 0 ;;
  esac
}

apt_runner=()
if command -v apt-get >/dev/null 2>&1; then
  if [[ "${EUID}" -eq 0 ]]; then
    apt_runner=(apt-get)
  elif command -v sudo >/dev/null 2>&1; then
    apt_runner=(sudo apt-get)
  fi
fi

echo "== KoalaByte Blue system package setup =="
echo "Repository root: ${REPO_ROOT}"
echo "INSTALL_SYSTEM_PACKAGES=${INSTALL_SYSTEM_PACKAGES} STRICT_SYSTEM_PACKAGES=${STRICT_SYSTEM_PACKAGES} ENABLE_PI_SPI=${ENABLE_PI_SPI}"

if ! command -v apt-get >/dev/null 2>&1; then
  echo "apt-get not found; skipping system package setup on this OS." >&2
  if strict_enabled; then
    exit 1
  fi
  exit 0
fi

if [[ "${CHECK_ONLY}" == "1" ]]; then
  echo "Check-only mode: apt-based system detected. Package installation not attempted."
  exit 0
fi

if ! install_enabled; then
  echo "System package install disabled by INSTALL_SYSTEM_PACKAGES=${INSTALL_SYSTEM_PACKAGES}."
  exit 0
fi

if [[ "${#apt_runner[@]}" -eq 0 ]]; then
  echo "apt-get is available, but this user is not root and sudo was not found." >&2
  echo "Install manually: sudo apt update && sudo apt install -y ${APT_PACKAGES[*]}" >&2
  if strict_enabled; then
    exit 1
  fi
  exit 0
fi

echo "Installing/checking Raspberry Pi system packages..."
"${apt_runner[@]}" update
"${apt_runner[@]}" install -y "${APT_PACKAGES[@]}"

enable_pi_spi_if_possible() {
  if ! spi_enable_enabled; then
    echo "Raspberry Pi SPI enablement disabled by ENABLE_PI_SPI=${ENABLE_PI_SPI}."
    return 0
  fi
  if ! command -v raspi-config >/dev/null 2>&1; then
    echo "raspi-config not found; skipping automatic SPI enablement. Enable SPI manually if using Didgeridoo/SX1262." >&2
    return 0
  fi
  echo "Checking/enabling Raspberry Pi SPI interface for Didgeridoo SX1262 LoRa setup..."
  if [[ "${EUID}" -eq 0 ]]; then
    raspi-config nonint do_spi 0 || true
  elif command -v sudo >/dev/null 2>&1; then
    sudo raspi-config nonint do_spi 0 || true
  else
    echo "sudo not found; enable SPI manually with raspi-config." >&2
  fi
}

enable_pi_spi_if_possible

echo "System package setup complete."
echo "AI voice/TTS check:"
if command -v espeak-ng >/dev/null 2>&1; then
  echo "  espeak-ng: $(command -v espeak-ng)"
elif command -v espeak >/dev/null 2>&1; then
  echo "  espeak: $(command -v espeak)"
else
  echo "  warning: no espeak-ng/espeak command found after install attempt" >&2
  if strict_enabled; then
    exit 1
  fi
fi
if command -v aplay >/dev/null 2>&1; then
  echo "  ALSA aplay: $(command -v aplay)"
fi
if [[ -e /dev/spidev0.0 ]]; then
  echo "  SPI: /dev/spidev0.0 present"
else
  echo "  SPI: /dev/spidev0.0 not present yet; reboot after first enablement if Didgeridoo will use the SX1262 SPI board" >&2
fi
