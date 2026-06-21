# Production Files

This repository keeps one current no-custom-PCB production package for the KoalaByte Blue stacked Raspberry Pi 3B+ device using the Nordic nRF52840 USB Dongle / PCA10059, optional InnoMaker USB-to-CAN, optional Heltec USB-C LoRa/GNSS node hardware, optional T114 validation hardware, and a simplified USB portable power-bank power path.

## Current dongle-only package

```text
production/RevA17-dongle-only/
```

Current production references:

- `production/RevA17-dongle-only/BOM_RevA17_DongleOnly.csv` - current complete dongle-only BOM using the Nordic nRF52840 USB Dongle, ESP32-S3 DualEye, Raspberry Pi 3B+, PIFFA-style 50000 mAh USB portable power bank, short USB power/data cables, optional powered USB hub, optional InnoMaker USB-to-CAN kit for Koala Kan Kommander, optional Heltec Wireless Tracker V2 USB-C LoRa/GNSS node hardware for Didgeridoo, and optional T114 validation hardware.
- `production/RevA17-dongle-only/PRODUCTION_README_RevA17_DongleOnly.md` - current production, assembly, validation, RevA23 InnoMaker CAN guide, RevA25 Heltec Wireless Tracker V2 GNSS update, opt-in T114 alternate target rule, and USB power-bank power path.
- `production/RevA17-dongle-only/BATTERY_POWER_2S_18650.md` - compatibility filename now containing the current USB power-bank power guide. The 2x18650/BMS/fuse/switch/buck path is no longer the main production path.
- `production/RevA17-dongle-only/Safety_Test_Record_RevA17.csv` - safety, bring-up, power-bank, and functional test record template.

## Current top-level docs

- `README.md` - current quick-start and operation index.
- `docs/FLASHING.md` - current all-component flashing and install guide.
- `docs/ORDERABLE_PARTS_LIST.md` - current orderable hardware list with USB power bank replacing the old 18650 stack.
- `docs/PRODUCTION_FILES.md` - this current production index.
- `docs/POWER_BANK_WIRING_MAIN.svg` - current text/SVG wiring diagram for the USB power-bank power path.
- `docs/DIDGERIDOO_LORA_SETUP.md` - Didgeridoo software/setup guide for the Heltec Wireless Tracker V2 USB-C Meshtastic LoRa/GNSS node; detailed case-hole and enclosure geometry remains in the production package.
- `docs/NRF52840_T114_ALT_TARGET.md` - opt-in Heltec Mesh Node T114 V2 alternate nRF52840 target guide; not a production replacement for the Nordic dongle yet.
- `docs/THEME_AND_MENU_SYSTEM.md` - consolidated current RevA23 theme, boot-splash, and menu guide.
- `docs/NRF52840_DONGLE_FLASHING.md` - nRF52840 Dongle / PCA10059 Zephyr build and DFU guide.
- `docs/KOALA_KAN_KOMMANDER_REVA22.md` - Koala Kan Kommander InnoMaker USB-to-CAN guide.
- `docs/KOALA_MODE_SWITCHER_REVA21.md` - Koala Mode Switcher guide.
- `docs/KOALA_KONNECT_REVA20.md` - Koala Konnect USB HCI adapter profile guide.
- `docs/KOALA_BLUEZ_TOOLS_REVA16.md` - Outback BlueZ Module Deck guide.

## Current firmware/software production files

- `firmware/esp32-dualeye/` - ESP32-S3 DualEye firmware, boot animation, and theme assets.
- `firmware/esp32-dualeye/themes/` - active theme and approved SVG visual source-of-truth assets.
- `firmware/nrf52840-dongle-ear-tag-tx-lab/` - nRF52840 Dongle KoalaByte Lab Zephyr app. This remains the default nRF production firmware source.
- `pi-companion/` - Raspberry Pi companion app, menu, theme, and helper modules.
- `scripts/check_repo_readiness.py` - current ready-to-run repository validation check.
- `scripts/flash_all_components.sh` - one-command Pi install, ESP32 flash, nRF52840 Dongle build/DFU, InnoMaker CAN manifest helper, Didgeridoo dependency setup, and opt-in T114 alternate build path.
- `scripts/build_firmware_all.sh` - all-firmware build helper with optional `BUILD_T114_LAB=1` support.
- `scripts/flash_esp32.sh` - ESP32 build/upload helper.
- `scripts/build_nrf52840_dongle_lab.sh` - KoalaByte Lab dongle build helper.
- `scripts/flash_nrf52840_dongle_lab_dfu.sh` - KoalaByte Lab dongle DFU helper.
- `scripts/build_nrf52840_t114_lab.sh` - experimental T114 alternate nRF52840 target build helper.
- `scripts/flash_nrf52840_t114_lab.sh` - experimental T114 alternate nRF52840 flash wrapper requiring a confirmed flash command.
- `scripts/build_koala_konnect.sh` - Koala Konnect build wrapper.
- `scripts/flash_koala_konnect.sh` - Koala Konnect DFU wrapper.
- `scripts/install_pi.sh` - Pi companion dependency installer.
- `scripts/run_koala_bluez.py` and `scripts/run_koala_bluez_*.sh` - Koala BlueZ runners.
- `scripts/run_koala_mode_switcher.py` - Koala Mode Switcher CLI runner.
- `scripts/run_koala_kan_kommander.py` - Koala Kan Kommander CLI runner.
- `scripts/run_didgeridoo.py` - Didgeridoo Wireless Tracker V2 Meshtastic/GNSS setup/status runner.
- `.github/workflows/koalabyte-blue-ci.yml` - CI workflow using the readiness check.

No custom PCB is required. The build uses commercially available development boards/modules, USB cabling, standoffs, a PIFFA-style USB portable power bank, optional powered USB hub, optional InnoMaker USB-to-CAN accessory hardware, optional Heltec Wireless Tracker V2 USB-C LoRa/GNSS node hardware, optional T114 nRF52840 validation hardware, approved firmware theme assets, and an open-frame stacked layout.

## T114 alternate target rule

The Heltec Mesh Node T114 V2 style board may be tested as an alternate nRF52840 target, but it is not the production replacement for the Nordic nRF52840 USB Dongle on main yet.

Rules:

1. Keep the Nordic nRF52840 Dongle / PCA10059 build path as the production default.
2. Use the T114 path only with `--nrf-t114-lab`, `BUILD_T114_LAB=1`, or the dedicated T114 scripts.
3. Confirm the exact Zephyr board target before running the T114 build.
4. Confirm the exact T114 bootloader/flash command before flashing.

## RevA25 Heltec Wireless Tracker V2 / Didgeridoo mechanical antenna and GNSS rule

Case-hole and antenna-placement details belong in the production package, not inside the Didgeridoo software guide.

The current case/top RF area must provide:

1. One 2.4 GHz antenna opening for the ESP32-S3 DualEye IPEX1/U.FL Wi-Fi/Bluetooth antenna path.
2. One smaller LoRa antenna opening only when the Heltec Wireless Tracker V2 LoRa IPEX/U.FL antenna connector is installed.
3. One GNSS sky-view clearance zone above the Wireless Tracker V2 GNSS antenna area when GNSS hardware is installed.
4. Optional GNSS external antenna opening only if the build intentionally switches the Wireless Tracker V2 to a documented external GNSS IPEX/U.FL antenna path.

The Wireless Tracker V2 uses onboard Wi-Fi/Bluetooth 2.4 GHz antenna hardware unless the exact board revision documents an external 2.4 GHz connector. The LoRa antenna must be matched to the purchased board and legal region. Do not substitute a 2.4 GHz antenna for the LoRa antenna. Do not place the GNSS antenna path beneath speaker magnets, metal screws/standoffs, USB cable bundles, or dense wire bundles.

## RevA23 CAN mechanical rule

The current Koala Kan Kommander physical option is the InnoMaker USB to CAN Converter kit. Do not use or reintroduce the earlier circular CAN panel port in RevA23 case notes or renderings. Use an internal mount or rectangular side/rear service-bay cutout with strain relief.

## USB power-bank mechanical rule

The current production path is powered by a PIFFA-style USB portable power bank through regulated USB output. Leave clearance for the Raspberry Pi 3B+ micro-USB power cable, USB cable bend radius, optional powered USB hub, Nordic nRF52840 dongle, ESP32-S3 DualEye, optional Heltec board, optional InnoMaker adapter, and strain relief. Do not route raw battery voltage to Pi GPIO, ESP32 GPIO, button wiring, USB devices, CAN wiring, or the Meshtastic/GNSS/T114 node.

## Cleanup rule

The older standalone menu/boot notes were consolidated into `docs/THEME_AND_MENU_SYSTEM.md`. Keep future theme/menu updates there unless a new guide is genuinely separate.

## Readiness rule

The repository is considered current only when:

1. `python3 scripts/check_repo_readiness.py` passes.
2. CI can compile the Pi companion Python code and scripts.
3. ESP32 firmware builds with PlatformIO.
4. The nRF52840 Dongle Zephyr project wiring and DFU helpers are present.
5. Optional Koala Kan Kommander files remain present and passive by default.
6. Optional Didgeridoo files remain setup/status/profile only by default.
7. Optional T114 files remain opt-in and do not replace the Nordic dongle default on main.
8. `scripts/flash_all_components.sh --all` is documented as the primary all-component helper.
9. The USB power-bank production guide and BOM remain aligned.
10. Removed legacy production packages and legacy theme docs are not reintroduced.
