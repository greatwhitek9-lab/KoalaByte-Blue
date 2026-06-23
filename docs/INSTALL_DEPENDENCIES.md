# KoalaByte Blue Heltec T114 Install Dependencies

This document is the dependency checklist for `koalabyte_blue_v2_heltec_edition`.

This branch targets the **Heltec Mesh Node T114 v2 onboard nRF52840**. It does not use the old separate Nordic USB accessory build path as the active branch target.

## System packages

Helper:

```bash
bash scripts/setup_system_packages.sh
```

Strict mode:

```bash
STRICT_SYSTEM_PACKAGES=1 bash scripts/setup_system_packages.sh
```

Covered package groups:

```text
Python: python3, python3-venv, python3-pip, python3-dev
Build: build-essential, pkg-config, cmake, ninja-build, gperf, ccache, device-tree-compiler, make, gcc, g++
Archives/downloads: wget, curl, xz-utils, file, unzip
USB: usbutils, udev, libusb-1.0-0, libusb-1.0-0-dev
Display/UI: libsdl2-2.0-0
Bluetooth/BlueZ: bluetooth, bluez, bluez-tools, rfkill
CAN: iproute2, can-utils
Packet review: tshark, wireshark-common
Storage/report support: sqlite3
GPIO buttons: python3-gpiozero, python3-lgpio, gpiod, libgpiod2
```

Skip apt package installation with:

```bash
INSTALL_SYSTEM_PACKAGES=0 bash scripts/setup_system_packages.sh
```

## Pi companion Python dependencies

Installed from:

```text
pi-companion/requirements.txt
pi-companion/requirements-heltec-v2-extra.txt
```

The Pi venv is created with `--system-site-packages` by default so apt-provided Raspberry Pi GPIO backends such as `python3-lgpio` remain visible inside the venv.

## ESP32 / PlatformIO dependencies

Helper:

```bash
bash scripts/setup_esp32_tools.sh
```

Strict mode:

```bash
STRICT_ESP32_TOOLS=1 bash scripts/setup_esp32_tools.sh
```

The ESP32 helper is used before programming `firmware/esp32-dualeye/`.

## Heltec T114 PlatformIO dependencies

The normal Heltec mouth/BLE/GNSS firmware uses:

```text
firmware/heltec-mouth/
```

Normal helper:

```bash
KOALABYTE_HELTEC_USB_PORT=/dev/ttyACM0 bash scripts/flash_heltec_mouth.sh
```

## Heltec T114 Koala Konnect / Zephyr dependencies

Koala Konnect T114 uses the Heltec T114 onboard nRF52840 and the Zephyr board target:

```text
heltec_t114_v2/nrf52840
```

Full nRF Connect SDK / Zephyr helper:

```bash
bash scripts/setup_nrf_connect_sdk_toolchain.sh
```

Strict mode:

```bash
STRICT_NCS_TOOLCHAIN=1 bash scripts/setup_nrf_connect_sdk_toolchain.sh
```

Build-only Koala Konnect T114 check:

```bash
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/build_koala_konnect_t114.sh
```

The helper prepares:

```text
nRF Connect SDK west workspace
Zephyr checkout
NCS Python virtual environment
Zephyr and nRF Python requirements
Zephyr SDK ARM toolchain when available for the host architecture
source-able environment file: logs/nrf_connect_sdk_env.sh
status file: logs/nrf_connect_sdk_status.json
```

Manual build environment:

```bash
source logs/nrf_connect_sdk_env.sh
T114_BOARD=heltec_t114_v2/nrf52840 bash scripts/build_koala_konnect_t114.sh
```

## Install flow integration

`install_pi.sh` and `flash_all_components.sh --install-firmware` coordinate the Pi companion, ESP32-S3 DualEye, Heltec T114 normal firmware, optional Koala Konnect T114 profile, Greatwhite support checks, and CAN bench checks.
