#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_SYSTEM_PACKAGES="${INSTALL_SYSTEM_PACKAGES:-auto}"
STRICT_SYSTEM_PACKAGES="${STRICT_SYSTEM_PACKAGES:-1}"
APT_RETRIES="${APT_RETRIES:-3}"
CHECK_ONLY=0

usage() {
  cat <<'EOF'
KoalaByte Blue Raspberry Pi system package setup helper

Usage:
  bash scripts/setup_system_packages.sh
  STRICT_SYSTEM_PACKAGES=0 bash scripts/setup_system_packages.sh
  INSTALL_SYSTEM_PACKAGES=0 bash scripts/setup_system_packages.sh
  bash scripts/setup_system_packages.sh --check-only

The helper refreshes APT metadata before resolving Bookworm/Trixie package
variants, fails early when core runtime/build packages are unavailable, accepts
an available gpiozero backend instead of requiring one distro-specific package,
requires Raspberry Pi power-state tooling for strict preflight, treats
packet-review/CAN/terminal utilities and distro PocketSphinx packages as
optional, retries APT, and passes DEBIAN_FRONTEND through sudo explicitly.
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
echo "== KoalaByte Blue Raspberry Pi system package setup =="
echo "INSTALL_SYSTEM_PACKAGES=${INSTALL_SYSTEM_PACKAGES} STRICT_SYSTEM_PACKAGES=${STRICT_SYSTEM_PACKAGES}"

if [[ "${CHECK_ONLY}" == "1" || "${INSTALL_SYSTEM_PACKAGES}" == "0" ]]; then
  echo "Package installation not attempted."
  exit 0
fi
if ! command -v apt-get >/dev/null 2>&1; then
  echo "apt-get not found; system package setup requires Raspberry Pi OS/Debian." >&2
  [[ "${STRICT_SYSTEM_PACKAGES}" == "1" ]] && exit 1
  exit 0
fi
if [[ "${EUID}" -eq 0 ]]; then
  apt_runner=(env DEBIAN_FRONTEND=noninteractive apt-get)
elif command -v sudo >/dev/null 2>&1; then
  apt_runner=(sudo env DEBIAN_FRONTEND=noninteractive apt-get)
else
  echo "apt-get is available, but root/sudo is unavailable." >&2
  [[ "${STRICT_SYSTEM_PACKAGES}" == "1" ]] && exit 1
  exit 0
fi

apt_retry() {
  local attempt rc=1
  for ((attempt=1; attempt<=APT_RETRIES; attempt++)); do
    set +e
    "${apt_runner[@]}" -o Acquire::Retries=3 \
      -o Dpkg::Options::=--force-confold "$@"
    rc=$?
    set -e
    [[ ${rc} -eq 0 ]] && return 0
    echo "APT attempt ${attempt}/${APT_RETRIES} failed with exit ${rc}; retrying..." >&2
    sleep $((attempt * 10))
  done
  return "${rc}"
}

# Resolve against current repository metadata, not the possibly stale cache from
# the Raspberry Pi OS image.
apt_retry update

required_packages=(
  git ca-certificates python3 python3-venv python3-pip python3-dev
  python3-gpiozero python3-serial python3-dbus python3-gi python3-httpx
  build-essential pkg-config cmake ninja-build gperf ccache device-tree-compiler
  wget curl xz-utils file make gcc g++ libffi-dev libssl-dev usbutils udev kmod
  util-linux raspi-utils libusb-1.0-0 libusb-1.0-0-dev
  libsdl2-2.0-0 fontconfig fonts-dejavu-core fonts-liberation
  network-manager wpasupplicant iw dhcpcd-base dnsutils iputils-ping
  bluetooth bluez rfkill sqlite3 iproute2 gpiod
  espeak-ng ffmpeg alsa-utils libasound2-plugins portaudio19-dev
)
optional_packages=(
  parted dosfstools exfatprogs
  libdrm2 libgbm1 libegl1 libgl1 libgl1-mesa-dri mesa-utils
  wireless-tools bluez-tools
  picocom minicom screen can-utils python3-can
  espeak pulseaudio-utils python3-pyaudio
  tshark wireshark
  python3-pocketsphinx pocketsphinx-en-us
  python3-libgpiod
)
required_variant_groups=(
  "python3-lgpio python3-rpi.gpio"
  "libgpiod3 libgpiod2"
  "libasound2t64 libasound2"
)

package_exists() { apt-cache show "$1" >/dev/null 2>&1; }
packages=()
missing_required=()
missing_optional=()
for package in "${required_packages[@]}"; do
  if package_exists "${package}"; then packages+=("${package}"); else missing_required+=("${package}"); fi
done
for package in "${optional_packages[@]}"; do
  if package_exists "${package}"; then packages+=("${package}"); else missing_optional+=("${package}"); fi
done
for group in "${required_variant_groups[@]}"; do
  selected=""
  for package in ${group}; do
    if package_exists "${package}"; then selected="${package}"; packages+=("${package}"); break; fi
  done
  if [[ -z "${selected}" ]]; then
    missing_required+=("${group}")
  else
    echo "Selected compatibility package: ${selected}"
  fi
done

if (( ${#missing_optional[@]} > 0 )); then
  echo "warning: unavailable optional package(s): ${missing_optional[*]}" >&2
fi
if (( ${#missing_required[@]} > 0 )); then
  echo "error: unavailable required package(s): ${missing_required[*]}" >&2
  if [[ "${STRICT_SYSTEM_PACKAGES}" == "1" ]]; then
    echo "Required package resolution failed before installation." >&2
    exit 1
  fi
fi
(( ${#packages[@]} > 0 )) || { echo "No compatible packages resolved." >&2; exit 1; }

if command -v debconf-set-selections >/dev/null 2>&1; then
  if [[ "${EUID}" -eq 0 ]]; then
    printf '%s\n' 'wireshark-common wireshark-common/install-setuid boolean false' | debconf-set-selections || true
  else
    printf '%s\n' 'wireshark-common wireshark-common/install-setuid boolean false' | sudo debconf-set-selections || true
  fi
fi

apt_retry install -y "${packages[@]}"

echo "System package setup complete."
for command in cmake ninja espeak-ng ffmpeg fc-list lsusb udevadm bluetoothctl aplay vcgencmd; do
  if command -v "${command}" >/dev/null 2>&1; then
    echo "  ${command}: $(command -v "${command}")"
  else
    echo "required command remains unavailable after APT: ${command}" >&2
    exit 1
  fi
done
for command in edge-tts tshark wireshark glxinfo cansend modprobe; do
  command -v "${command}" >/dev/null 2>&1 && echo "  optional ${command}: $(command -v "${command}")"
done
