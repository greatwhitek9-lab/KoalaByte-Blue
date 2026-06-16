# KoalaByte Blue / killerkoala AI Companion Firmware RevA25

KoalaByte Blue is the dongle-only Raspberry Pi 3B+ / ESP32-S3 DualEye / Nordic nRF52840 Dongle build for the killerkoala companion, safe BlueZ helper deck, KoalaByte Lab dongle firmware, Koala Konnect, and optional Koala Kan Kommander CAN bench path.

## Start here

### First-time Raspberry Pi base OS install

On a blank microSD card, install a normal Raspberry Pi operating system first. KoalaByte Blue does not replace the Pi operating system; the KoalaByte scripts install the companion software, firmware tools, SDK/toolchain, cached DFU packages, boot splash, menu, and mode selector after the Pi can boot Linux.

Recommended base OS:

```text
Raspberry Pi OS Lite 64-bit
```

Recommended Raspberry Pi Imager options before first boot:

```text
Enable SSH
Set username and password
Set WiFi SSID/password if available
Set WiFi country, locale, and timezone
```

First boot flow:

```text
1. Flash Raspberry Pi OS Lite 64-bit to the microSD card.
2. Boot the Raspberry Pi and log in locally or over SSH.
3. Make sure the Pi has internet access by Ethernet, preconfigured WiFi, or the first-boot WiFi helper.
4. Clone or copy this KoalaByte-Blue repo onto the Pi.
5. Run scripts/install_pi.sh from the repo root.
6. Prepare the cached nRF52840 Dongle DFU ZIPs.
7. Use the Pi as the flashing computer for the ESP32-S3 DualEye and nRF52840 Dongle.
```

Minimal first-boot commands after Pi OS is running:

```bash
sudo apt update
sudo apt install -y git

git clone https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
```

If the repo is private, clone with your GitHub SSH key or authenticated token.

Run the readiness check:

```bash
python3 scripts/check_repo_readiness.py
```

Install the Pi companion. During install, the script checks first-boot WiFi/internet, installs system packages, creates the Python environment, prepares ESP32 tools, prepares west/nrfutil, prepares the full nRF Connect SDK/Zephyr toolchain, and tries to prepare both nRF52840 Dongle DFU ZIPs on the Pi when the required tools are available:

```bash
bash scripts/install_pi.sh
```

Strong first install with strict checks:

```bash
STRICT_WIFI_FIRST_BOOT=1 \
STRICT_SYSTEM_PACKAGES=1 \
STRICT_ESP32_TOOLS=1 \
STRICT_DONGLE_CACHE=1 \
STRICT_NCS_TOOLCHAIN=1 \
bash scripts/install_pi.sh
```

If WiFi was not configured in Raspberry Pi Imager, allow the installer to prompt for WiFi before SDK downloads:

```bash
WIFI_INTERACTIVE=1 \
STRICT_WIFI_FIRST_BOOT=1 \
STRICT_SYSTEM_PACKAGES=1 \
STRICT_ESP32_TOOLS=1 \
STRICT_DONGLE_CACHE=1 \
STRICT_NCS_TOOLCHAIN=1 \
bash scripts/install_pi.sh
```

Force install to fail if both cached DFU ZIPs cannot be prepared:

```bash
STRICT_DONGLE_CACHE=1 bash scripts/install_pi.sh
```

Prepare or refresh both cached nRF52840 Dongle firmware packages:

```bash
bash scripts/prepare_dongle_firmware_cache.sh
```

Install/flash the default component set:

```bash
bash scripts/flash_all_components.sh --all
```

Common variants:

```bash
bash scripts/flash_all_components.sh --pi
NO_MONITOR=1 ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --nrf-lab
bash scripts/flash_all_components.sh --all --build-only
bash scripts/flash_all_components.sh --all --smoke
```

## Current hardware profile

Retained BLE target:

```text
Nordic nRF52840 Dongle / PCA10059 / NRF52840-DONGLE
```

Power path:

```text
USB-C PD/QC charger capable of 12 V
  -> Seloky USB-C PD/QC 12 V trigger board
  -> 5 V buck converter
  -> fused regulated 5 V rail
  -> Raspberry Pi / ESP32-S3 DualEye / USB peripherals
```

Optional CAN path:

```text
Raspberry Pi 3B+ USB host
  -> short internal USB data cable
  -> InnoMaker USB to CAN Converter kit
  -> adapter-side CAN_H / CAN_L / GND / optional SHIELD
  -> isolated CAN bench simulator or owned bench harness
```

Do not wire CAN_H or CAN_L directly to Raspberry Pi GPIO. Do not connect the Seloky 12 V output directly to the Pi.

## Pre-boot dongle mode selector

The Pi companion includes a pre-boot selector that can run before the normal KoalaByte Blue boot splash and main menu.

Choices:

```text
1) KoalaByte Blue Lab Mode
   Default production/lab profile. The dongle advertises as KoalaByte Lab.

2) Koala Konnect Mode
   Alternate USB HCI adapter profile for phone/computer host use.
```

The Pi can store both DFU packages locally:

```text
build/nrf52840-dongle-lab/koalabyte-blue-nrf52840-dongle-dfu.zip
build/nrf52840-dongle-koala-konnect/koala-konnect-nrf52840-dongle-dfu.zip
logs/dongle_firmware_cache.json
```

Prepare or refresh the offline cache manually:

```bash
bash scripts/prepare_dongle_firmware_cache.sh
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py cache-status
```

Interactive selector:

```bash
PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py
```

Direct mode selection:

```bash
PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --mode koalabyte_lab
PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --mode koala_konnect
```

Switch the physical nRF52840 Dongle when it is in DFU bootloader mode:

```bash
NRF_DFU_PORT=/dev/ttyACM0 PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --mode koalabyte_lab
NRF_DFU_PORT=/dev/ttyACM0 PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --mode koala_konnect
```

Normal Pi-side boot wrapper:

```bash
bash scripts/koalabyte_blue_boot.sh
```

That wrapper runs:

```text
pre-boot mode selector -> KoalaByte Blue boot splash -> grouped main menu
```

## Main operations

### Pi companion install

```bash
bash scripts/install_pi.sh
```

Install-time cache controls:

```bash
STRICT_DONGLE_CACHE=1 bash scripts/install_pi.sh
PREPARE_DONGLE_CACHE=0 bash scripts/install_pi.sh
```

### ESP32-S3 DualEye firmware

```bash
bash scripts/flash_esp32.sh
NO_MONITOR=1 ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_esp32.sh
```

### nRF52840 Dongle firmware

```bash
bash scripts/build_nrf52840_dongle_lab.sh
bash scripts/flash_nrf52840_dongle_lab_dfu.sh
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_nrf52840_dongle_lab_dfu.sh
```

The nRF52840 Dongle can run one profile at a time:

```text
koalabyte_lab   KoalaByte Blue Lab Mode / KoalaByte Lab BLE advertisement
koala_konnect   Koala Konnect USB HCI external Bluetooth adapter mode
```

### Koala Mode Switcher

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py status
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py prepare-cache
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py cache-status
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py switch koalabyte_lab --dfu-port /dev/ttyACM0
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py switch koala_konnect --dfu-port /dev/ttyACM0
```

### Koala Kan Kommander

Koala Kan Kommander uses the InnoMaker USB to CAN Converter kit. RevA25 supports bounded CAN listen and gated transmit for a completely isolated bench simulator. Transmit requires both `--bench-simulator` and `--confirm-transmit`.

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py status --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py listen --interface can0 --duration 10
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py report --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py generate-payloads --interface can0 --payload-profile all --base-id 0x600 --sequence-count 8 --tag KOALAKAN
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py transmit --interface can0 --bench-simulator --confirm-transmit --payload-profile heartbeat --base-id 0x600 --sequence-count 3
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py listen-transmit --interface can0 --bench-simulator --confirm-transmit --can-id 0x600 --data "4B 42 01 00" --duration 10
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py transmit-placeholder
```

`transmit-placeholder` remains blocked as a legacy safety artifact. Use `transmit` or `listen-transmit` only on an isolated bench simulator or owned bench harness.

### Outback BlueZ Module Deck

KoalaByte Blue wraps local BlueZ tooling as themed, bounded automation modules on the Pi companion.

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py status
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py scan --duration 15
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py monitor --duration 20
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py all-safe --duration 15
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py gatt-readiness --target AA:BB:CC:DD:EE:FF --owned-device
```

Convenience wrappers:

```bash
bash scripts/run_koala_bluez_manifest.sh
bash scripts/run_koala_bluez_inventory.sh
bash scripts/run_koala_bluez_status.sh
bash scripts/run_koala_bluez_scan.sh --duration 15
bash scripts/run_koala_bluez_monitor.sh --duration 20
bash scripts/run_koala_bluez_all_safe.sh
bash scripts/run_koala_bluez_gatt_readiness.sh --target AA:BB:CC:DD:EE:FF --owned-device
```

## Theme and menu system

Current approved theme:

```text
jungle_jumanji_eucalyptus
```

Approved visual assets live under:

```text
firmware/esp32-dualeye/themes/jungle_jumanji_eucalyptus/
```

Theme/menu guide:

```text
docs/THEME_AND_MENU_SYSTEM.md
```

Pre-boot selector guide:

```text
docs/PREBOOT_MODE_SELECTOR.md
```

Run previews:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
```

## Current production references

```text
production/RevA17-dongle-only/BOM_RevA17_DongleOnly.csv
production/RevA17-dongle-only/PRODUCTION_README_RevA17_DongleOnly.md
production/RevA17-dongle-only/Safety_Test_Record_RevA17.csv
docs/PRODUCTION_FILES.md
docs/FLASHING.md
docs/ORDERABLE_PARTS_LIST.md
docs/THEME_AND_MENU_SYSTEM.md
docs/PREBOOT_MODE_SELECTOR.md
```

## Core paths

```text
pi-companion/koalablue/bluez_tools.py
pi-companion/koalblue/killerkoala_vocabulary.py
pi-companion/koalablue/killerkoala_vocabulary.py
pi-companion/koalablue/menu_catalog.py
pi-companion/koalablue/koala_mode_switcher.py
pi-companion/koalablue/preboot_mode_selector.py
pi-companion/koalablue/koala_kan_kommander.py
pi-companion/config.default.json
firmware/nrf52840-dongle-ear-tag-tx-lab/src/main.c
firmware/esp32-dualeye/src/main.cpp
firmware/esp32-dualeye/src/boot_animation.cpp
scripts/setup_wifi_first_boot.sh
scripts/setup_system_packages.sh
scripts/setup_esp32_tools.sh
scripts/setup_nrf_tools.sh
scripts/setup_nrf_connect_sdk_toolchain.sh
scripts/setup_local_ncs.sh
scripts/prepare_dongle_firmware_cache.sh
scripts/run_preboot_mode_select.py
scripts/koalabyte_blue_boot.sh
scripts/check_repo_readiness.py
scripts/flash_all_components.sh
```

## Safety boundary

KoalaByte Blue is for lawful educational research, defensive testing, owned-device lab work, and authorized Bluetooth/CAN assessment only. Passive capture, local logging, synthetic owned-device lab advertising, Koala Konnect host-adapter use, and Koala Kan Kommander listen/transmit workflows must remain scoped to environments where you have permission. CAN transmit is for completely isolated bench simulators or owned bench harnesses only and requires explicit transmit confirmation flags.
