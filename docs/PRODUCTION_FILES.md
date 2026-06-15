# Production Files

This repository keeps one current no-custom-PCB production package for the KoalaByte Blue stacked Raspberry Pi 3B+ device using the Nordic nRF52840 USB Dongle / PCA10059.

## Current dongle-only package

```text
production/RevA17-dongle-only/
```

Current production references:

- `production/RevA17-dongle-only/BOM_RevA17_DongleOnly.csv` - current complete dongle-only BOM with Seloky 12 V PD/QC trigger board and optional InnoMaker USB-to-CAN kit for Koala Kan Kommander.
- `production/RevA17-dongle-only/PRODUCTION_README_RevA17_DongleOnly.md` - current production, assembly, power, validation, and RevA23 InnoMaker CAN guide.
- `production/RevA17-dongle-only/Safety_Test_Record_RevA17.csv` - safety, bring-up, and functional test record template.

## Current firmware/software production files

- `firmware/nrf52840-dongle-ear-tag-tx-lab/src/main.c` - nRF52840 Dongle KoalaByte Lab synthetic advertisement app.
- `firmware/nrf52840-dongle-ear-tag-tx-lab/prj.conf` - KoalaByte Lab device-name/config.
- `firmware/nrf52840-dongle-ear-tag-tx-lab/CMakeLists.txt` - nRF Connect SDK / Zephyr app wiring.
- `firmware/nrf52840-dongle-ear-tag-tx-lab/README.md` - Dongle app guide.
- `docs/FLASHING.md` - current all-component flashing and install guide.
- `docs/NRF52840_DONGLE_FLASHING.md` - nRF52840 Dongle / PCA10059 Zephyr build and DFU guide.
- `docs/KOALA_MODE_SWITCHER_REVA21.md` - Koala Mode Switcher status/build/package/select workflow.
- `docs/KOALA_KONNECT_REVA20.md` - Koala Konnect USB HCI adapter profile guide.
- `docs/KOALA_KAN_KOMMANDER_REVA22.md` - optional Koala Kan Kommander InnoMaker USB-to-CAN hardware/software guide.
- `docs/ORDERABLE_PARTS_LIST.md` - orderable hardware list with Seloky 12 V PD/QC trigger board and InnoMaker USB-to-CAN kit.
- `docs/POWER_UPDATE_REVA2.md` - power-path validation guide for Seloky trigger and 5 V buck regulator.
- `firmware/esp32-dualeye/` - ESP32-S3 DualEye firmware and display helpers.
- `pi-companion/koalbl...` - removed; do not use the old typo path.
- `pi-companion/koalablue/koala_kan_kommander.py` - optional Koala Kan Kommander module.
- `pi-companion/` - Raspberry Pi companion app, menu, theme, and helper modules.
- `scripts/check_repo_readiness.py` - current ready-to-run repository validation check.
- `scripts/flash_all_components.sh` - one-command Pi install, ESP32 flash, nRF52840 Dongle build/DFU, and InnoMaker CAN manifest helper.
- `scripts/run_koala_mode_switcher.py` - Koala Mode Switcher CLI runner.
- `scripts/run_koala_kan_kommander.py` - Koala Kan Kommander CLI runner.
- `scripts/build_nrf52840_dongle_lab.sh` - KoalaByte Lab dongle build helper.
- `scripts/flash_nrf52840_dongle_lab_dfu.sh` - KoalaByte Lab dongle DFU package/apply helper.
- `scripts/build_koala_konnect.sh` - Koala Konnect build wrapper.
- `scripts/flash_koala_konnect.sh` - Koala Konnect DFU package/apply wrapper.
- `scripts/build_firmware_all.sh` - all-firmware build helper.
- `scripts/flash_esp32.sh` - ESP32 build/upload helper.
- `scripts/install_pi.sh` - Pi companion dependency installer.
- `scripts/run_koala_bluez.py` and `scripts/run_koala_bluez_*.sh` - Koala BlueZ runners.
- `.github/workflows/koalabyte-blue-ci.yml` - CI workflow using the readiness check.

No custom PCB is required. The build uses commercially available development boards/modules, USB cabling, standoffs, a protected battery/power system, optional InnoMaker USB-to-CAN accessory hardware, and an open-frame stacked layout.

## RevA23 CAN mechanical rule

The current Koala Kan Kommander physical option is the InnoMaker USB to CAN Converter kit. Do not use or reintroduce the earlier circular CAN panel port in RevA23 case notes or renderings. Use an internal mount or rectangular side/rear service-bay cutout with strain relief.

## Readiness rule

The repository is considered current only when:

1. `python3 scripts/check_repo_readiness.py` passes.
2. CI can compile the Pi companion Python code and scripts.
3. ESP32 firmware builds with PlatformIO.
4. The nRF52840 Dongle Zephyr project wiring and DFU helpers are present.
5. Optional Koala Kan Kommander files remain present and passive by default.
6. `scripts/flash_all_components.sh --all` is documented as the primary all-component helper.
7. Removed legacy production packages and legacy power parts are not reintroduced.
