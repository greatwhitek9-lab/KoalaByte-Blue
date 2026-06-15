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
- `ASSEMBLY_AND_FLASHING_INSTRUCTIONS_RevA5_BUTTONS.md` — updated in-repo RevA14 assembly, flashing, button, boot-animation, and jungle-menu procedure

Current firmware/software production files outside the static package archive:

- `firmware/esp32-dualeye/src/boot_animation.cpp` — ESP32 procedural KoalaByte Blue boot animation
- `firmware/esp32-dualeye/include/boot_animation.h` — boot animation interface
- `firmware/esp32-dualeye/src/menu_theme.cpp` — ESP32 eucalyptus branch / bubbly menu helper renderer
- `firmware/esp32-dualeye/include/menu_theme.h` — ESP32 menu-theme helper interface
- `firmware/esp32-dualeye/include/config.h` — RevA13/RevA14 firmware configuration and boot/menu toggles
- `firmware/esp32-dualeye/platformio.ini` — PlatformIO build config with TFT_eSPI dependency
- `pi-companion/koalablue/menu_theme.py` — Pi jungle/eucalyptus graphical and terminal menu theme
- `scripts/flash_esp32.sh` — ESP32 clean-build/upload/serial-monitor helper
- `scripts/install_pi.sh` — Pi companion dependency installer
- `scripts/run_boot_splash.py` — Pi companion boot splash runner
- `scripts/run_menu_screen.py` — terminal and graphical jungle menu runner
- `scripts/install_boot_splash_autostart.sh` — Pi desktop autostart installer for the boot splash
- `scripts/check_boot_animation_config.py` — repository validation check for boot/menu wiring
- `.github/workflows/koalabyte-blue-ci.yml` — firmware/Python CI workflow

No custom PCB is required. The build uses commercially available development boards, USB cabling, standoffs, a battery/power system, and an open-frame stacked layout.

## RevA14 note

The static production ZIP/PDF names still say RevA1 because they describe the no-custom-PCB hardware package. The live repository now contains newer RevA14 software/firmware additions, including the animated KoalaByte Blue boot screen and the large bubbly jungle/eucalyptus menu theme. Use the latest repository scripts and docs when flashing or installing software.
