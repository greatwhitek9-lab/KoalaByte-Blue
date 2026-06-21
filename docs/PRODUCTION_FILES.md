# Production Files

This repository keeps one current no-custom-PCB production package for the KoalaByte Blue stacked Raspberry Pi 3B+ device using the Nordic nRF52840 USB Dongle / PCA10059, optional InnoMaker USB-to-CAN, and a simplified USB portable power-bank power path.

The `main` branch is the KoalaByte Blue Nordic-dongle production branch. Alternate board-specific builds belong in their own branches and should not be documented as main-branch production hardware.

## Current dongle-only package

```text
production/RevA17-dongle-only/
```

Current production references:

- `production/RevA17-dongle-only/BOM_RevA17_DongleOnly.csv` - current complete dongle-only BOM using the Nordic nRF52840 USB Dongle, ESP32-S3 DualEye, Raspberry Pi 3B+, PIFFA-style 50000 mAh USB portable power bank, short USB power/data cables, optional powered USB hub, and optional InnoMaker USB-to-CAN kit for Koala Kan Kommander.
- `production/RevA17-dongle-only/PRODUCTION_README_RevA17_DongleOnly.md` - current production, assembly, validation, RevA23 InnoMaker CAN guide, and USB power-bank power path.
- `production/RevA17-dongle-only/BATTERY_POWER_2S_18650.md` - compatibility filename now containing the current USB power-bank power guide. The 2x18650/BMS/fuse/switch/buck path is no longer the main production path.
- `production/RevA17-dongle-only/Safety_Test_Record_RevA17.csv` - safety, bring-up, power-bank, and functional test record template.

## Current top-level docs

- `README.md` - current quick-start and operation index.
- `docs/FLASHING.md` - current all-component flashing and install guide.
- `docs/ORDERABLE_PARTS_LIST.md` - current orderable hardware list with USB power bank replacing the old 18650 stack.
- `docs/PRODUCTION_FILES.md` - this current production index.
- `docs/POWER_BANK_WIRING_MAIN.svg` - current text/SVG wiring diagram for the USB power-bank power path.
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
- `scripts/flash_all_components.sh` - one-command Pi install, ESP32 flash, nRF52840 Dongle build/DFU, InnoMaker CAN manifest helper, and USB power-bank checks.
- `scripts/build_firmware_all.sh` - all-firmware build helper for the main Nordic-dongle branch.
- `scripts/flash_esp32.sh` - ESP32 build/upload helper.
- `scripts/build_nrf52840_dongle_lab.sh` - KoalaByte Lab dongle build helper.
- `scripts/flash_nrf52840_dongle_lab_dfu.sh` - KoalaByte Lab dongle DFU helper.
- `scripts/build_koala_konnect.sh` - Koala Konnect build wrapper.
- `scripts/flash_koala_konnect.sh` - Koala Konnect DFU wrapper.
- `scripts/install_pi.sh` - Pi companion dependency installer.
- `scripts/run_koala_bluez.py` and `scripts/run_koala_bluez_*.sh` - Koala BlueZ runners.
- `scripts/run_koala_mode_switcher.py` - Koala Mode Switcher CLI runner.
- `scripts/run_koala_kan_kommander.py` - Koala Kan Kommander CLI runner.
- `.github/workflows/koalabyte-blue-ci.yml` - CI workflow using the readiness check.

No custom PCB is required. The build uses commercially available development boards/modules, USB cabling, standoffs, a PIFFA-style USB portable power bank, optional powered USB hub, optional InnoMaker USB-to-CAN accessory hardware, approved firmware theme assets, and an open-frame stacked layout.

## RevA23 CAN mechanical rule

The current Koala Kan Kommander physical option is the InnoMaker USB to CAN Converter kit. Do not use or reintroduce the earlier circular CAN panel port in RevA23 case notes or renderings. Use an internal mount or rectangular side/rear service-bay cutout with strain relief.

## USB power-bank mechanical rule

The current production path is powered by a PIFFA-style USB portable power bank through regulated USB output. Leave clearance for the Raspberry Pi 3B+ micro-USB power cable, USB cable bend radius, optional powered USB hub, Nordic nRF52840 dongle, ESP32-S3 DualEye, optional InnoMaker adapter, and strain relief. Do not route raw battery voltage to Pi GPIO, ESP32 GPIO, button wiring, USB devices, or CAN wiring.

## Branch cleanup rule

Main should remain limited to the Nordic nRF52840 USB Dongle production build. Alternate board hardware, alternate radio workflows, and branch-specific setup guides belong only in their own branches.

## Cleanup rule

The older standalone menu/boot notes were consolidated into `docs/THEME_AND_MENU_SYSTEM.md`. Keep future theme/menu updates there unless a new guide is genuinely separate.

## Readiness rule

The repository is considered current only when:

1. `python3 scripts/check_repo_readiness.py` passes.
2. CI can compile the Pi companion Python code and scripts.
3. ESP32 firmware builds with PlatformIO.
4. The nRF52840 Dongle Zephyr project wiring and DFU helpers are present.
5. Optional Koala Kan Kommander files remain present and passive by default unless explicitly gated for bench simulator work.
6. `scripts/flash_all_components.sh --all` is documented as the primary all-component helper.
7. The USB power-bank production guide and BOM remain aligned.
8. Removed legacy production packages and branch-specific alternate board docs are not reintroduced.
