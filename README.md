# KoalaByte Blue / killerkoala AI Companion Firmware RevA15

ESP32-S3 DualEye firmware, Raspberry Pi companion software, optional Nordic nRF52840 DK lab firmware, RevA6 six-button front-panel GPIO support, RevA8 **eucalyptus** passive BLE scanner/logger naming, RevA9 **Ear Tag** lab beacon naming, RevA13 animated boot splash support, RevA14 jungle/eucalyptus menu styling, and RevA15 Koala Kry safe review plus **Ear Tag TX Lab** synthetic BLE advertisement support for the **KoalaByte Blue Pi3B+ stacked research device**.

## Hardware profile

Production compact BLE board:

```text
Nordic nRF52840 Dongle / PCA10059 / NRF52840-DONGLE
```

Optional development/debug board:

```text
Nordic nRF52840 DK / PCA10056
```

Use the DK for development and validation. Keep the Dongle in the final compact physical build.

## RevA15 Ear Tag TX Lab

Ear Tag TX Lab is the safe transmit-oriented lab mode. It advertises a clearly named, synthetic BLE service-data pattern from the nRF52840 DK for owned-device signal-integrity observation.

It advertises as:

```text
EarTag-TX-Lab
```

Build and flash:

```bash
bash scripts/flash_nrf52840_dk_lab.sh
```

Generate the Pi-side plan artifact:

```bash
PYTHONPATH=pi-companion python3 scripts/run_ear_tag_tx_lab.py
```

See [`docs/EAR_TAG_TX_LAB_REVA15.md`](docs/EAR_TAG_TX_LAB_REVA15.md).

## RevA15 Koala Kry review boundary

Koala Kry remains an offline captured-metadata replay simulator. It includes a safe review-manifest path for lab requests that need documentation before separate owned-device radio work.

Review command:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kry.py --request-rf-transmit --lab-setting --owned-device
```

That command writes:

```text
logs/koala_kry_replay/koala_kry_transmit_review_YYYYMMDD_HHMMSS.json
```

The manifest keeps Koala Kry offline and points toward safe alternatives such as Ear Tag TX Lab and fresh clearly named owned-device lab advertisements.

See [`docs/KOALA_KRY_REVA12.md`](docs/KOALA_KRY_REVA12.md).

## RevA14 jungle/eucalyptus menu theme

KoalaByte Blue includes a large rounded bubbly jungle-title style for menu selections, bordered with eucalyptus branches.

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py
```

See [`docs/MENU_THEME_REVA14.md`](docs/MENU_THEME_REVA14.md).

## RevA13 animated boot splash

KoalaByte Blue includes boot animation support in both the ESP32-S3 firmware and the Raspberry Pi companion layer.

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
bash scripts/install_boot_splash_autostart.sh
python3 scripts/check_boot_animation_config.py
```

See [`docs/BOOT_ANIMATION_REVA13.md`](docs/BOOT_ANIMATION_REVA13.md).

## Core paths

```text
pi-companion/koalablue/koala_kry.py
pi-companion/koalablue/ear_tag_tx_lab.py
pi-companion/koalablue/menu_catalog.py
pi-companion/koalablue/menu_theme.py
pi-companion/koalablue/boot_animation.py
firmware/nrf52840-dk-lab-peripheral/src/main.c
firmware/esp32-dualeye/src/boot_animation.cpp
firmware/esp32-dualeye/src/menu_theme.cpp
scripts/run_koala_kry.py
scripts/run_ear_tag_tx_lab.py
scripts/run_menu_screen.py
scripts/run_boot_splash.py
scripts/check_boot_animation_config.py
```

## Ready-to-flash status

```bash
bash scripts/flash_esp32.sh
bash scripts/install_pi.sh
bash scripts/flash_nrf52840_dk_lab.sh
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

## Front-panel controls

```text
Button 1 = main menu
Button 2 = previous / left / back
Button 3 = select; hold for shutdown
Button 4 = next / right / forward
Button 5 = up / previous
Button 6 = down / next
Touch drag = scroll
Touch long press = select
```

## Safety boundary

This package is for authorized Bluetooth research, BLE inventory, local logging, AI companion behavior, and safe lab validation only. Koala Kry stays offline; Ear Tag TX Lab uses owned-device synthetic lab payloads.
