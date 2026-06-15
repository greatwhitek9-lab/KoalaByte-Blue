# Production Files

This repository keeps one current no-custom-PCB production package for the KoalaByte Blue stacked Raspberry Pi 3B+ device using the Nordic nRF52840 USB Dongle / PCA10059.

## Current dongle-only package

```text
production/RevA17-dongle-only/
```

Current production references:

- `production/RevA17-dongle-only/BOM_RevA17_DongleOnly.csv` — current complete dongle-only BOM.
- `production/RevA17-dongle-only/PRODUCTION_README_RevA17_DongleOnly.md` — current production, assembly, flashing, and validation guide.
- `production/RevA17-dongle-only/Safety_Test_Record_RevA17.csv` — safety, bring-up, flash, and functional test record template.

## Current firmware/software production files

- `firmware/nrf52840-dongle-ear-tag-tx-lab/src/main.c` — nRF52840 Dongle Ear Tag TX Lab synthetic advertisement firmware.
- `firmware/nrf52840-dongle-ear-tag-tx-lab/prj.conf` — EarTag-TX-Lab device-name/config.
- `firmware/nrf52840-dongle-ear-tag-tx-lab/CMakeLists.txt` — nRF Connect SDK / Zephyr app wiring.
- `firmware/nrf52840-dongle-ear-tag-tx-lab/README.md` — Dongle firmware guide.
- `docs/NRF52840_DONGLE_FLASHING.md` — nRF52840 Dongle / PCA10059 Zephyr build and DFU guide.
- `firmware/esp32-dualeye/src/boot_animation.cpp` — ESP32 procedural KoalaByte Blue boot screen.
- `firmware/esp32-dualeye/include/boot_animation.h` — boot screen interface.
- `firmware/esp32-dualeye/src/menu_theme.cpp` — ESP32 eucalyptus branch / bubbly menu helper renderer.
- `firmware/esp32-dualeye/include/menu_theme.h` — ESP32 menu-theme helper interface.
- `firmware/esp32-dualeye/include/config.h` — firmware configuration and toggles.
- `firmware/esp32-dualeye/platformio.ini` — PlatformIO build config with TFT_eSPI dependency.
- `pi-companion/koalablue/killerkoala_vocabulary.py` — killerkoala event/inquiry vocabulary and XP-rank tone engine.
- `pi-companion/koalablue/menu_theme.py` — Pi jungle/eucalyptus graphical and terminal menu theme.
- `pi-companion/koalablue/ear_tag_tx_lab.py` — Pi-side Ear Tag TX Lab plan artifact helper.
- `pi-companion/koalablue/bluez_tools.py` — Koala BlueZ local helper layer.
- `pi-companion/koalablue/koala_kapture.py` — passive BLE metadata capture helper.
- `scripts/check_repo_readiness.py` — current ready-to-flash repository validation check.
- `scripts/check_boot_animation_config.py` — compatibility wrapper for old validation workflows.
- `scripts/run_killerkoala_voice.py` — killerkoala vocabulary preview and manifest runner.
- `scripts/run_koala_kapture.py` — Koala Kapture passive metadata capture runner.
- `scripts/build_nrf52840_dongle_lab.sh` — nRF52840 Dongle / PCA10059 Zephyr build helper.
- `scripts/flash_nrf52840_dongle_lab_dfu.sh` — nRF52840 Dongle DFU package/flash helper.
- `scripts/build_firmware_all.sh` — all-firmware build helper for ESP32 and nRF52840 Dongle.
- `scripts/flash_esp32.sh` — ESP32 clean-build/upload/serial-monitor helper.
- `scripts/install_pi.sh` — Pi companion dependency installer.
- `scripts/run_boot_splash.py` — Pi companion boot-screen runner.
- `scripts/run_menu_screen.py` — terminal and graphical jungle menu runner.
- `scripts/run_ear_tag_tx_lab.py` — Ear Tag TX Lab plan runner.
- `scripts/run_koala_bluez.py` — Koala BlueZ main runner.
- `scripts/run_koala_bluez_inventory.sh` — Koala BlueZ inventory wrapper.
- `scripts/run_koala_bluez_status.sh` — Koala BlueZ status wrapper.
- `scripts/run_koala_bluez_scan.sh` — Koala BlueZ scan wrapper.
- `scripts/run_koala_bluez_monitor.sh` — Koala BlueZ monitor wrapper.
- `scripts/install_boot_splash_autostart.sh` — Pi desktop autostart installer for the boot screen.
- `.github/workflows/koalabyte-blue-ci.yml` — firmware/Python/Zephyr-project CI workflow using the readiness check.

No custom PCB is required. The build uses commercially available development boards/modules, USB cabling, standoffs, a protected battery/power system, and an open-frame stacked layout.

## Readiness rule

The repository is considered current only when:

1. `python3 scripts/check_repo_readiness.py` passes.
2. CI can compile the Pi companion Python code and scripts.
3. ESP32 firmware builds with PlatformIO.
4. The nRF52840 Dongle Zephyr project wiring and DFU helpers are present.
5. Removed legacy production packages are not reintroduced.
