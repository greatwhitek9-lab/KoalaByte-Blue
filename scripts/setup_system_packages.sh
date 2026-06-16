#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_SYSTEM_PACKAGES="${INSTALL_SYSTEM_PACKAGES:-auto}"
STRICT_SYSTEM_PACKAGES="${STRICT_SYSTEM_PACKAGES:-0}"
CHECK_ONLY=0

APT_PACKAGES=(
  git
  python3
  python3-venv
  python3-pip
  python3-dev
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
  libusb-1.0-0
  libusb-1.0-0-dev
  libsdl2-2.0-0
  bluetooth
  bluez
  bluez-tools
  rfkill
  sqlite3
  iproute2
  can-utils
  python3-lgpio
  gpiod
  libgpiod2
)

usage() {
  cat <<'EOF'
KoalaByte Blue Raspberry Pi system package setup helper

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
  nRF/Zephyr helper build tools, BlueZ tools, CAN tools, SDL2 runtime, SQLite,
  USB utilities, and Raspberry Pi GPIO support.
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
echo "INSTALL_SYSTEM_PACKAGES=${INSTALL_SYSTEM_PACKAGES} STRICT_SYSTEM_PACKAGES=${STRICT_SYSTEM_PACKAGES}"

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

echo "System package setup complete."
