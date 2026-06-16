# KoalaByte Blue Install and Flash Dependencies

This document is the dependency checklist for the Raspberry Pi install and firmware flashing process.

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
Archives/downloads: wget, curl, xz-utils, file
USB: usbutils, udev, libusb-1.0-0, libusb-1.0-0-dev
Display/UI: libsdl2-2.0-0
Bluetooth/BlueZ: bluetooth, bluez, bluez-tools, rfkill
CAN: iproute2, can-utils
Storage/report support: sqlite3
GPIO buttons: python3-gpiozero, python3-lgpio, gpiod, libgpiod2
```

The helper attempts apt installation on apt-based systems when root or sudo is available. It can be skipped with:

```bash
INSTALL_SYSTEM_PACKAGES=0 bash scripts/setup_system_packages.sh
```

## Pi companion Python dependencies

Installed from:

```text
pi-companion/requirements.txt
```

Current Python packages:

```text
bleak
pyserial
rich
pydantic
fastapi
uvicorn
requests
gpiozero
pygame
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

The ESP32 flash script calls this automatically before using `pio`:

```bash
bash scripts/flash_esp32.sh
```

## nRF52840 / Zephyr / Nordic DFU dependencies

Basic helper:

```bash
bash scripts/setup_nrf_tools.sh
```

Strict mode:

```bash
STRICT_NRF_TOOLS=1 bash scripts/setup_nrf_tools.sh
```

The nRF helper checks:

```text
west      Zephyr / nRF Connect SDK build tool
nrfutil   Nordic DFU package and USB serial flashing tool
```

Build-only nRF flows need `west`. DFU package/flash/cache flows need both `west` and `nrfutil`.

## Full nRF Connect SDK / Zephyr toolchain

Full helper:

```bash
bash scripts/setup_nrf_connect_sdk_toolchain.sh
```

Strict mode:

```bash
STRICT_NCS_TOOLCHAIN=1 bash scripts/setup_nrf_connect_sdk_toolchain.sh
```

Validate a real KoalaByte Lab Zephyr build after setup:

```bash
VALIDATE_BUILD=1 STRICT_NCS_TOOLCHAIN=1 bash scripts/setup_nrf_connect_sdk_toolchain.sh
```

Defaults:

```text
NCS_WORKSPACE=$HOME/ncs
NCS_REVISION=v2.9.0
ZEPHYR_SDK_VERSION=0.17.0
ZEPHYR_SDK_INSTALL_DIR=$HOME/zephyr-sdk-0.17.0
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
west build -b nrf52840dongle_nrf52840 firmware/nrf52840-dongle-ear-tag-tx-lab -d build/nrf52840-dongle-lab
```

## Install flow integration

`install_pi.sh` now runs dependency setup in this order:

```text
1. setup_system_packages.sh
2. create/update Pi companion venv with system site packages enabled
3. pip install pi-companion/requirements.txt
4. setup_esp32_tools.sh
5. repo readiness check
6. setup_nrf_tools.sh
7. setup_nrf_connect_sdk_toolchain.sh
8. prepare cached nRF52840 DFU ZIPs when tools are available
```

Strong install path:

```bash
STRICT_SYSTEM_PACKAGES=1 STRICT_ESP32_TOOLS=1 STRICT_DONGLE_CACHE=1 STRICT_NCS_TOOLCHAIN=1 bash scripts/install_pi.sh
```

## All-component flash flow integration

`flash_all_components.sh` now checks dependencies before the relevant selected action:

```text
System package helper -> Pi/ESP32/nRF/CAN selections
PlatformIO helper -> ESP32 selections
west/nrfutil helper -> nRF selections
full NCS/Zephyr helper -> nRF selections
```

Full run:

```bash
bash scripts/flash_all_components.sh --all
```

Strict full run:

```bash
STRICT_SYSTEM_PACKAGES=1 STRICT_ESP32_TOOLS=1 STRICT_NRF_TOOLS=1 STRICT_NCS_TOOLCHAIN=1 bash scripts/flash_all_components.sh --all
```

## Offline dongle firmware cache

Prepare both cached nRF52840 DFU ZIPs on the Pi:

```bash
bash scripts/prepare_dongle_firmware_cache.sh
```

That helper now checks/prepares `west`, `nrfutil`, and the full nRF Connect SDK/Zephyr toolchain first, then builds/packages:

```text
build/nrf52840-dongle-lab/koalabyte-blue-nrf52840-dongle-dfu.zip
build/nrf52840-dongle-koala-konnect/koala-konnect-nrf52840-dongle-dfu.zip
```
