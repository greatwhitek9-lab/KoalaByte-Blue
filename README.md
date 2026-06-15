# KoalaByte Blue / killerkoala AI Companion Firmware RevA21 + RevA23 InnoMaker CAN Update

ESP32-S3 DualEye firmware, Raspberry Pi companion software, and nRF Connect SDK / Zephyr firmware for the Nordic nRF52840 Dongle/PCA10059 production target.

RevA21 keeps the build **dongle-only**, adds **Koala Mode Switcher**, keeps **KoalaByte Lab** as the default dongle firmware profile, preserves **Koala Konnect** as the optional USB HCI adapter profile, and updates the power path to the **Seloky USB-C PD/QC 12 V trigger board**.

RevA23 adds the user-specified **InnoMaker USB to CAN Converter kit** for the optional **Koala Kan Kommander** path. This replaces the earlier generic/circular CAN panel-port visual with an internal or side/rear service-bay adapter mount.

## Hardware profile

Production compact BLE board:

```text
Nordic nRF52840 Dongle / PCA10059 / NRF52840-DONGLE
```

Only the nRF52840 Dongle/PCA10059 is retained as the Nordic BLE target in this repo.

Current USB-C input trigger:

```text
Seloky USB-C PD Trigger Board Module PD/QC Decoy Fast Charge USB Type-C to 12V
```

Power path:

```text
USB-C PD/QC charger capable of 12 V
  -> Seloky USB-C PD/QC 12 V trigger board
  -> 5 V buck converter
  -> fused regulated 5 V rail
  -> Raspberry Pi / ESP32-S3 DualEye / USB peripherals
```

Verify the Seloky trigger output is about 12 V before connecting the buck converter. Do not connect 12 V directly to the Pi or any 5 V module.

## RevA23 Koala Kan Kommander - InnoMaker CAN kit

Recommended optional CAN observation path:

```text
Raspberry Pi 3B+ USB host
  -> short internal USB data cable
  -> InnoMaker USB to CAN Converter kit
  -> adapter-side CAN_H / CAN_L / GND / optional SHIELD
  -> authorized bench harness or owned-device test network
```

Mechanical update:

- Do **not** use the earlier circular CAN panel port.
- Mount the InnoMaker adapter inside the Level 2 USB service bay or side/rear service area.
- Use a rectangular service slot or internal strain-relieved mount if the adapter or harness must be accessible.
- Keep the adapter and CAN cable away from antennas, battery contacts, speaker grille, and Raspberry Pi GPIO.
- Do not wire CAN_H or CAN_L directly to Raspberry Pi GPIO.

Software remains passive by default. The `transmit-placeholder` action stays blocked.

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py status --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py listen --interface can0 --duration 10
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py report --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py transmit-placeholder
```

## Ready-to-flash check

Run the consolidated readiness check before flashing:

```bash
python3 scripts/check_repo_readiness.py
```

Expected result:

```text
KoalaByte Blue repo readiness check passed.
Ready-to-flash file wiring is present for ESP32, nRF52840 Dongle/DFU, and Pi companion.
```

## RevA18 Outback BlueZ Module Deck

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

Themed module titles:

```text
Gumleaf Gear Check          Local BlueZ helper inventory
Eucalyptus Bus Scout        Adapter/controller/D-Bus status
Dropbear Discovery Sweep    Timed discovery with address hashing by default
Billabong HCI Watch         Timed btmon capture with .btsnoop artifact support
Joey Target Card            Owned-device target info
Treehouse Service Notes     Owned-device service notes
Gumnut GATT Readiness       Owned-device GATT checklist artifact
Kookaburra Safe Nest Run    Inventory + status + bounded scan
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

See [`docs/KOALA_BLUEZ_TOOLS_REVA16.md`](docs/KOALA_BLUEZ_TOOLS_REVA16.md).

## Koala Mode Switcher

Koala Mode Switcher prepares and selects the active nRF52840 Dongle profile.

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py status
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py prepare-all
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py switch koalabyte_lab --dfu-port /dev/ttyACM0
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py switch koala_konnect --dfu-port /dev/ttyACM0
```

Supported dongle profiles:

```text
koalabyte_lab   KoalaByte Lab synthetic owned-device BLE lab advertisement
koala_konnect   Koala Konnect USB HCI external Bluetooth adapter mode
```

See [`docs/KOALA_MODE_SWITCHER_REVA21.md`](docs/KOALA_MODE_SWITCHER_REVA21.md).

## nRF Connect SDK / Zephyr firmware build

Default KoalaByte Lab dongle build:

```bash
bash scripts/build_nrf52840_dongle_lab.sh
```

Build all retained firmware targets:

```bash
bash scripts/build_firmware_all.sh
```

Dongle DFU package/flash helper:

```bash
bash scripts/flash_nrf52840_dongle_lab_dfu.sh
```

See [`docs/NRF52840_DONGLE_FLASHING.md`](docs/NRF52840_DONGLE_FLASHING.md).

## ESP32-S3 DualEye firmware

```bash
bash scripts/flash_esp32.sh
```

The ESP32 side retains the KoalaByte Blue animated boot splash and menu theme.

## Pi companion install

```bash
bash scripts/install_pi.sh
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py status --xp 100
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
scripts/check_repo_readiness.py
scripts/run_koala_bluez.py
scripts/run_koala_mode_switcher.py
scripts/run_koala_kan_kommander.py
scripts/run_koala_bluez_manifest.sh
scripts/run_koala_bluez_inventory.sh
scripts/run_koala_bluez_status.sh
scripts/run_koala_bluez_scan.sh
scripts/run_koala_bluez_monitor.sh
scripts/run_koala_bluez_all_safe.sh
scripts/run_koala_bluez_gatt_readiness.sh
scripts/build_nrf52840_dongle_lab.sh
scripts/flash_nrf52840_dongle_lab_dfu.sh
scripts/build_koala_konnect.sh
scripts/flash_koala_konnect.sh
scripts/build_firmware_all.sh
```

## Main Pi commands

```text
scan                         Run a safe BLE inventory scan
summary                      Summarize observed BLE devices
show                         Show device table
eucalyptus status            Show passive BLE logger status
eucalyptus start             Start passive BLE logger
eucalyptus stop              Stop passive BLE logger
eucalyptus restart           Restart passive BLE logger
eucalyptus upload-status     Show WiGLE upload readiness/status
koala_kapture                Capture and archive BLE advertisement metadata
koala_kry                    Replay captured metadata offline into the report/XP pipeline
koala_kry_transmit_review    Write safe review manifest; no radio output
ear_tag                      Safe named lab BLE beacon skill
ear_tag_tx_lab               KoalaByte Lab synthetic owned-device BLE advertisement plan and firmware path
koala_mode_switcher          Build/package/select KoalaByte Lab or Koala Konnect
koala_kan_kommander          Passive InnoMaker USB-to-CAN status/listen/report workflow
koala_bluez_manifest         Write the Outback BlueZ module manifest
koala_bluez_inventory        Gumleaf Gear Check: local BlueZ helper inventory
koala_bluez_status           Eucalyptus Bus Scout: adapter/controller status
koala_bluez_scan             Dropbear Discovery Sweep: timed discovery
koala_bluez_monitor          Billabong HCI Watch: timed HCI monitor logging
koala_bluez_all_safe         Kookaburra Safe Nest Run: safe module sequence
killerkoala_voice            Preview event reactions and inquiry vocabulary by XP rank
urban_poaching               Authorized BLE RSSI lab game
buttons                      Show/check GPIO front-panel button status
level/status                 Show XP and rank
report                       Write Markdown report
wake killerkoala             Test wake-word flow
authorized_ble_inventory     Generate authorized BLE inventory artifact
gatt_readiness_checklist     Generate owned-device GATT readiness checklist
pairing_security_review      Generate pairing/access-control review notes
lab_beacon_plan              Generate safe BLE beacon/peripheral testing plan
packet_capture_notes         Generate protocol-analysis notes for owned/lab traffic
defensive_report             Generate defensive lab report template
lab                          Password-gated Authorized Lab Use menu
settings                     Device and companion settings
shutdown_confirm             Confirm safe shutdown
quit                         Exit
```

## Safety boundary

This package is for authorized Bluetooth research, BLE inventory, local logging, AI companion behavior, safe lab validation, and scoped CAN observation only. Koala Kry stays offline; KoalaByte Lab uses owned-device synthetic lab payloads; Koala Konnect turns the dongle into a host-controlled USB HCI adapter; Outback BlueZ wraps local adapter status, discovery, HCI capture, and owned-device documentation workflows; Koala Kan Kommander uses the InnoMaker USB-to-CAN kit passively by default.