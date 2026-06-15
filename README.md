# KoalaByte Blue / killerkoala AI Companion Firmware RevA17

ESP32-S3 DualEye firmware, Raspberry Pi companion software, nRF Connect SDK / Zephyr firmware for the Nordic nRF52840 Dongle, RevA6 six-button front-panel GPIO support, RevA8 **eucalyptus** passive BLE scanner/logger naming, RevA13 animated boot splash support, RevA14 jungle/eucalyptus menu styling, RevA15 Ear Tag TX Lab, RevA16 **Koala BlueZ Tools**, and RevA17 **killerkoala companion vocabulary** for the **KoalaByte Blue Pi3B+ stacked research device**.

## Hardware profile

Production compact BLE board:

```text
Nordic nRF52840 Dongle / PCA10059 / NRF52840-DONGLE
```

The nRF52840 DK/PCA10056 has been removed from the retained production and firmware build path. The only Nordic BLE target retained in this repo is the nRF52840 Dongle.

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

The older `scripts/check_boot_animation_config.py` remains as a compatibility wrapper, but new workflows should use `scripts/check_repo_readiness.py`.

## RevA17 killerkoala companion vocabulary

killerkoala now has a structured event/inquiry vocabulary with Australian male voice metadata, gruff cyberpunk attitude, and XP-based confidence scaling.

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py status
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py scan_start --xp 100
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py bluez_status --xp 300
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py --manifest
```

XP ranks:

```text
Noob   = 0+ XP
Hacker = 75+ XP
Legend = 250+ XP
```

See [`docs/KILLERKOALA_VOCABULARY_REVA17.md`](docs/KILLERKOALA_VOCABULARY_REVA17.md).

## nRF Connect SDK / Zephyr firmware build

Dongle build:

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

## RevA16 Koala BlueZ Tools

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py status
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py scan --duration 15
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py monitor --duration 20
```

Convenience wrappers:

```bash
bash scripts/run_koala_bluez_inventory.sh
bash scripts/run_koala_bluez_status.sh
bash scripts/run_koala_bluez_scan.sh --duration 15
bash scripts/run_koala_bluez_monitor.sh --duration 20
```

See [`docs/KOALA_BLUEZ_TOOLS_REVA16.md`](docs/KOALA_BLUEZ_TOOLS_REVA16.md).

## RevA15 Ear Tag TX Lab

Ear Tag TX Lab is the safe transmit-oriented lab mode. It advertises a clearly named, synthetic BLE service-data pattern from the nRF52840 Dongle for owned-device signal-integrity observation.

```text
EarTag-TX-Lab
```

```bash
bash scripts/build_nrf52840_dongle_lab.sh
bash scripts/flash_nrf52840_dongle_lab_dfu.sh
PYTHONPATH=pi-companion python3 scripts/run_ear_tag_tx_lab.py
```

See [`docs/EAR_TAG_TX_LAB_REVA15.md`](docs/EAR_TAG_TX_LAB_REVA15.md).

## RevA15 Koala Kry review boundary

Koala Kry remains an offline captured-metadata replay simulator. It includes a safe review-manifest path for lab requests that need documentation before separate owned-device radio work.

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kry.py --request-rf-transmit --lab-setting --owned-device
```

See [`docs/KOALA_KRY_REVA12.md`](docs/KOALA_KRY_REVA12.md).

## RevA14 jungle/eucalyptus menu theme

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py
```

See [`docs/MENU_THEME_REVA14.md`](docs/MENU_THEME_REVA14.md).

## RevA13 animated boot splash

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
bash scripts/install_boot_splash_autostart.sh
python3 scripts/check_repo_readiness.py
```

See [`docs/BOOT_ANIMATION_REVA13.md`](docs/BOOT_ANIMATION_REVA13.md).

## Core paths

```text
pi-companion/koalablue/killerkoala_vocabulary.py
pi-companion/koalablue/bluez_tools.py
pi-companion/koalblue/koala_kry.py
pi-companion/koalablue/ear_tag_tx_lab.py
pi-companion/koalablue/menu_catalog.py
pi-companion/koalablue/menu_theme.py
pi-companion/koalablue/boot_animation.py
firmware/nrf52840-dongle-ear-tag-tx-lab/src/main.c
firmware/esp32-dualeye/src/boot_animation.cpp
firmware/esp32-dualeye/src/menu_theme.cpp
scripts/check_repo_readiness.py
scripts/run_killerkoala_voice.py
scripts/build_nrf52840_dongle_lab.sh
scripts/flash_nrf52840_dongle_lab_dfu.sh
scripts/build_firmware_all.sh
scripts/run_koala_bluez.py
scripts/run_koala_kry.py
scripts/run_ear_tag_tx_lab.py
scripts/run_menu_screen.py
scripts/run_boot_splash.py
```

## Ready-to-flash status

```bash
python3 scripts/check_repo_readiness.py
bash scripts/flash_esp32.sh
bash scripts/install_pi.sh
bash scripts/build_nrf52840_dongle_lab.sh
bash scripts/flash_nrf52840_dongle_lab_dfu.sh
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
ear_tag_tx_lab               Synthetic owned-device BLE advertisement plan and firmware path
koala_bluez_inventory        List installed local BlueZ helper tools
koala_bluez_status           Save local Bluetooth/BlueZ adapter status
koala_bluez_scan             Run timed local discovery and save results
koala_bluez_monitor          Run timed local HCI monitor logging
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

This package is for authorized Bluetooth research, BLE inventory, local logging, AI companion behavior, and safe lab validation only. Koala Kry stays offline; Ear Tag TX Lab uses owned-device synthetic lab payloads; Koala BlueZ Tools wrap local adapter status, discovery, and logging workflows; killerkoala vocabulary provides safe lab narration and status responses.
