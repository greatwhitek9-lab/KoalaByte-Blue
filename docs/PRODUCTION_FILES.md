# Production Files

This repository includes the latest no-custom-PCB production package for the KoalaByte Blue stacked Pi 3B+ device using the Nordic nRF52840 Dongle/PCA10059.

Location:

```text
production/RevA1-nrf52840-dongle/
```

Included production references:

- `KoalaBlue_Pi3B_NRF52840_Dongle_Production_Package_RevA1.pdf` — consolidated build package
- `KoalaBlue_Pi3B_NRF52840_Dongle_Production_Package_RevA1.zip` — full production package archive
- `KoalaBlue_NRF52840_Dongle_Render_Datasheet_RevA1.png` — rendered product/datasheet image
- `Stack_Diagram_RevA1.png` — mechanical stack diagram
- `Wiring_Diagram_RevA1.png` — wiring diagram
- `Power_Budget_RevA1.png` — power budget diagram
- `BOM_RevA1.csv` — bill of materials
- `Safety_Test_Record_RevA1.csv` — safety test record template
- `ASSEMBLY_AND_FLASHING_INSTRUCTIONS_RevA5_BUTTONS.md` — updated in-repo RevA17 assembly, flashing, button, boot-screen, jungle-menu, Ear Tag TX Lab, BlueZ, and killerkoala vocabulary procedure

Current firmware/software production files outside the static package archive:

- `firmware/nrf52840-dk-lab-peripheral/src/main.c` — nRF52840 DK Ear Tag TX Lab synthetic advertisement firmware
- `firmware/nrf52840-dk-lab-peripheral/prj.conf` — EarTag-TX-Lab device-name/config
- `firmware/nrf52840-dk-lab-peripheral/CMakeLists.txt` — nRF Connect SDK / Zephyr app wiring
- `firmware/nrf52840-dk-lab-peripheral/README.md` — Ear Tag TX Lab firmware guide
- `firmware/esp32-dualeye/src/boot_animation.cpp` — ESP32 procedural KoalaByte Blue boot screen
- `firmware/esp32-dualeye/include/boot_animation.h` — boot screen interface
- `firmware/esp32-dualeye/src/menu_theme.cpp` — ESP32 eucalyptus branch / bubbly menu helper renderer
- `firmware/esp32-dualeye/include/menu_theme.h` — ESP32 menu-theme helper interface
- `firmware/esp32-dualeye/include/config.h` — firmware configuration and toggles
- `firmware/esp32-dualeye/platformio.ini` — PlatformIO build config with TFT_eSPI dependency
- `pi-companion/koalablue/killerkoala_vocabulary.py` — killerkoala event/inquiry vocabulary and XP-rank tone engine
- `pi-companion/koalablue/menu_theme.py` — Pi jungle/eucalyptus graphical and terminal menu theme
- `pi-companion/koalablue/ear_tag_tx_lab.py` — Pi-side Ear Tag TX Lab plan artifact helper
- `pi-companion/koalablue/bluez_tools.py` — Koala BlueZ local helper layer
- `scripts/run_killerkoala_voice.py` — killerkoala vocabulary preview and manifest runner
- `scripts/build_nrf52840_dk_lab.sh` — nRF Connect SDK / Zephyr build helper
- `scripts/build_firmware_all.sh` — all-firmware build helper
- `scripts/flash_esp32.sh` — ESP32 clean-build/upload/serial-monitor helper
- `scripts/flash_nrf52840_dk_lab.sh` — nRF52840 DK Ear Tag TX Lab build/flash helper
- `scripts/install_pi.sh` — Pi companion dependency installer
- `scripts/run_boot_splash.py` — Pi companion boot-screen runner
- `scripts/run_menu_screen.py` — terminal and graphical jungle menu runner
- `scripts/run_ear_tag_tx_lab.py` — Ear Tag TX Lab plan runner
- `scripts/run_koala_bluez.py` — Koala BlueZ main runner
- `scripts/run_koala_bluez_inventory.sh` — Koala BlueZ inventory wrapper
- `scripts/run_koala_bluez_status.sh` — Koala BlueZ status wrapper
- `scripts/run_koala_bluez_scan.sh` — Koala BlueZ scan wrapper
- `scripts/run_koala_bluez_monitor.sh` — Koala BlueZ monitor wrapper
- `scripts/install_boot_splash_autostart.sh` — Pi desktop autostart installer for the boot screen
- `scripts/check_boot_animation_config.py` — RevA17 repository validation check
- `.github/workflows/koalabyte-blue-ci.yml` — firmware/Python/Zephyr-project CI workflow

No custom PCB is required. The build uses commercially available development boards, USB cabling, standoffs, a battery/power system, and an open-frame stacked layout.

## RevA17 note

The static production ZIP/PDF names still say RevA1 because they describe the no-custom-PCB hardware package. The live repository now contains newer RevA17 software/firmware additions, including nRF Connect SDK / Zephyr firmware build helpers, Koala BlueZ local helper commands, and killerkoala companion vocabulary. Use the latest repository scripts and docs when flashing or installing software.
