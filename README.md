# KoalaByte Blue / killerkoala AI Companion Firmware RevA25

KoalaByte Blue is the dongle-only Raspberry Pi 3B+ / ESP32-S3 DualEye / Nordic nRF52840 Dongle build for the killerkoala companion, safe BlueZ helper deck, KoalaByte Lab dongle firmware, Koala Konnect, and optional Koala Kan Kommander CAN bench path.

## Start here

Run the readiness check:

```bash
python3 scripts/check_repo_readiness.py
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

## Main operations

### Pi companion install

```bash
bash scripts/install_pi.sh
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
koalabyte_lab   KoalaByte Lab synthetic owned-device BLE lab advertisement
koala_konnect   Koala Konnect USB HCI external Bluetooth adapter mode
```

### Koala Mode Switcher

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py status
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py prepare-all
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
bash scripts/run_koala_bluez_all_safe.sh --duration 15
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
```

## Core paths

```text
pi-companion/koalablue/bluez_tools.py
pi-companion/koalablue/killerkoala_vocabulary.py
pi-companion/koalablue/menu_catalog.py
pi-companion/koalablue/koala_mode_switcher.py
pi-companion/koalablue/koala_kan_kommander.py
pi-companion/config.default.json
firmware/nrf52840-dongle-ear-tag-tx-lab/src/main.c
firmware/esp32-dualeye/src/main.cpp
firmware/esp32-dualeye/src/boot_animation.cpp
scripts/check_repo_readiness.py
scripts/flash_all_components.sh
```

## Safety boundary

KoalaByte Blue is for lawful educational research, defensive testing, owned-device lab work, and authorized Bluetooth/CAN assessment only. Passive capture, local logging, synthetic owned-device lab advertising, Koala Konnect host-adapter use, and Koala Kan Kommander listen/transmit workflows must remain scoped to environments where you have permission. CAN transmit is for completely isolated bench simulators or owned bench harnesses only and requires explicit transmit confirmation flags.
