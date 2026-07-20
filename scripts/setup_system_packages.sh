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

The helper supports Raspberry Pi OS Bookworm and Trixie. Package names are
resolved against the active apt repositories so one renamed optional package
does not abort the complete dependency installation.

GreatWhite Reef packet-review support is provided by tshark and wireshark.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) CHECK_ONLY=1; INSTALL_SYSTEM_PACKAGES=0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
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

base_packages=(
  git python3 python3-venv python3-pip python3-dev python3-gpiozero python3-lgpio
  python3-serial python3-dbus python3-gi python3-httpx
  python3-pocketsphinx pocketsphinx-en-us
  build-essential pkg-config cmake ninja-build gperf ccache device-tree-compiler
  wget curl xz-utils file make gcc g++ libffi-dev libssl-dev usbutils udev kmod
  util-linux parted dosfstools exfatprogs libusb-1.0-0 libusb-1.0-0-dev
  libsdl2-2.0-0 libdrm2 libgbm1 libegl1 libgl1 libgl1-mesa-dri mesa-utils
  fontconfig fonts-dejavu-core fonts-liberation
  network-manager wpasupplicant wireless-tools iw dhcpcd-base
  dnsutils iputils-ping bluetooth bluez bluez-tools rfkill sqlite3 iproute2
  picocom minicom screen can-utils python3-can gpiod
  espeak-ng espeak alsa-utils libasound2-plugins pulseaudio-utils
  portaudio19-dev python3-pyaudio tshark wireshark
)

# Debian 12/Bookworm uses libgpiod2. Debian 13/Trixie transitioned to
# libgpiod3. Select whichever package exists instead of failing the whole apt
# transaction on an obsolete package name.
variant_groups=(
  "libgpiod3 libgpiod2"
  "libasound2t64 libasound2"
)

package_exists() {
  apt-cache show "$1" >/dev/null 2>&1
}

packages=()
missing=()
for package in "${base_packages[@]}"; do
  if package_exists "${package}"; then
    packages+=("${package}")
  else
    missing+=("${package}")
  fi
done

for group in "${variant_groups[@]}"; do
  selected=""
  for package in ${group}; do
    if package_exists "${package}"; then
      selected="${package}"
      packages+=("${package}")
      break
    fi
  done
  if [[ -z "${selected}" ]]; then
    missing+=("${group}")
  else
    echo "Selected compatibility package: ${selected}"
  fi
done

if (( ${#missing[@]} > 0 )); then
  echo "warning: unavailable optional package(s) on this OS: ${missing[*]}" >&2
  if [[ "${STRICT_SYSTEM_PACKAGES}" == "1" ]]; then
    echo "STRICT_SYSTEM_PACKAGES=1 is set; unavailable packages are fatal." >&2
    exit 1
  fi
fi

if (( ${#packages[@]} == 0 )); then
  echo "No compatible packages were resolved from apt metadata." >&2
  [[ "${STRICT_SYSTEM_PACKAGES}" == "1" ]] && exit 1
  exit 0
fi

echo "Installing/checking Raspberry Pi system packages..."
"${apt_runner[@]}" update
"${apt_runner[@]}" install -y "${packages[@]}"

echo "System package setup complete."
for command in cmake ninja espeak-ng pocketsphinx_continuous fc-list lsusb udevadm bluetoothctl tshark wireshark aplay glxinfo cansend modprobe; do
  if command -v "${command}" >/dev/null 2>&1; then
    echo "  ${command}: $(command -v "${command}")"
  fi
done

if ! command -v cmake >/dev/null 2>&1 || ! command -v ninja >/dev/null 2>&1; then
  echo "warning: CMake and/or Ninja remain unavailable after package setup" >&2
  [[ "${STRICT_SYSTEM_PACKAGES}" == "1" ]] && exit 1
fi
