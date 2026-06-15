# KoalaByte Blue / killerkoala AI Companion Firmware RevA13

ESP32-S3 DualEye firmware, Raspberry Pi companion software, optional Nordic nRF52840 DK lab firmware, RevA6 six-button front-panel GPIO support, RevA8 **eucalyptus** always-on BLE scanner/logger naming, RevA9 **Ear Tag** lab beacon naming, the expanded shared full-function menu, and RevA13 animated **KoalaByte Blue** boot splash support for the **KoalaByte Blue Pi3B+ stacked research device**.

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

## RevA13 animated boot splash

KoalaByte Blue now includes boot animation support in both the ESP32-S3 firmware and the Raspberry Pi companion layer.

ESP32 firmware path:

```text
firmware/esp32-dualeye/src/boot_animation.cpp
firmware/esp32-dualeye/include/boot_animation.h
```

Pi companion path:

```text
pi-companion/koalablue/boot_animation.py
scripts/run_boot_splash.py
scripts/install_boot_splash_autostart.sh
```

The boot screen shows a dark KoalaByte face, pulsing purple left eye, pulsing true-blue right eye, **KoalaByte Blue** title with **Blue** rendered blue, `BOOTING...`, and an animated progress bar.

Test Pi splash windowed:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
```

Install desktop autostart on the Pi:

```bash
bash scripts/install_boot_splash_autostart.sh
```

See [`docs/BOOT_ANIMATION_REVA13.md`](docs/BOOT_ANIMATION_REVA13.md).

## RevA8 eucalyptus always-on BLE scanner/logger

The always-on passive Bluetooth/BLE scanner/logger action is named:

```text
eucalyptus
```

`eucalyptus` stores passive BLE observations under:

```text
/blecaptures/
```

Suggested UI/CLI command names:

```text
eucalyptus status
eucalyptus start
eucalyptus stop
eucalyptus restart
eucalyptus upload-status
```

WiGLE upload remains disabled until credentials and valid location settings are configured.

## RevA9 Ear Tag lab beacon

The safe named lab BLE beacon skill is now named:

```text
Ear Tag
```

The default lab BLE advertisement name is:

```text
EarTag-Lab
```

To rename it before flashing:

```bash
python3 scripts/set_lab_ble_name.py MyLabName
bash scripts/flash_nrf52840_dk_lab.sh
```

Use names that clearly identify the device as your own lab hardware.

## RevA6 front-panel controls

The nRF52840 Dongle includes one small onboard user button, but the final KoalaByte Blue case uses six external Raspberry Pi GPIO buttons numbered **1 through 6 from left to right**:

```text
Button 1 = Main Menu                         -> Pi GPIO5  / physical pin 29
Button 2 = Move Left / Back                  -> Pi GPIO6  / physical pin 31
Button 3 = Enter / Select; hold for Shutdown -> Pi GPIO13 / physical pin 33
Button 4 = Move Right / Forward              -> Pi GPIO19 / physical pin 35
Button 5 = Up                                -> Pi GPIO26 / physical pin 37
Button 6 = Down                              -> Pi GPIO21 / physical pin 40
GND      = Shared ground bus                 -> Pi GND    / physical pin 39
```

Button part in BOM:

```text
Adafruit Tactile Button switch (6mm) x 20 pack / Product ID 367
```

## Ready-to-flash status

The ESP32-S3 DualEye firmware is a PlatformIO project and can be built/flashed directly from `firmware/esp32-dualeye/`. See [`docs/FLASHING.md`](docs/FLASHING.md).

Quick ESP32 flash:

```bash
bash scripts/flash_esp32.sh
```

The optional nRF52840 DK lab peripheral firmware is an nRF Connect SDK / Zephyr project at:

```text
firmware/nrf52840-dk-lab-peripheral/
```

Quick nRF52840 DK flash:

```bash
bash scripts/flash_nrf52840_dk_lab.sh
```

## What is included

- ESP32-S3 DualEye firmware scaffold with USB serial JSON protocol.
- RevA13 procedural ESP32 boot animation launched during firmware `setup()`.
- RevA13 Pi companion fullscreen boot splash runner and desktop autostart installer.
- Mic wake path enabled by default with wake word **killerkoala**.
- Raspberry Pi companion dependency/config files.
- `eucalyptus` always-on passive BLE capture configuration under `/blecaptures/`.
- RevA6 Raspberry Pi six-button GPIO manager.
- RevA9 **Ear Tag** named lab beacon configuration.
- Shared full-function menu catalog for GPIO buttons, touch scrolling, and long-press selection.
- Production BOM and safety-test CSV files.
- Optional nRF52840 DK safe lab-peripheral firmware.
- Flashing guides and production-file manifests.

## Production package

The no-custom-PCB physical production files are staged under:

```text
production/RevA1-nrf52840-dongle/
```

Latest hardware/software additions:

- `docs/NRF52840_DK_OPTION_REVA4.md`
- `docs/FRONT_PANEL_BUTTONS_REVA5.md`
- `docs/BUTTON_WIRING_REVA5.md`
- `docs/LAB_TAG_BEACON_SKILL_REVA7.md`
- `docs/EUCALYPTUS_ALWAYS_ON_BLE_REVA8.md`
- `docs/MENU_SELECTION_REVA12.md`
- `docs/BOOT_ANIMATION_REVA13.md`
- `pi-companion/koalablue/menu_catalog.py`
- `pi-companion/koalablue/boot_animation.py`
- `firmware/esp32-dualeye/src/boot_animation.cpp`
- `scripts/run_boot_splash.py`
- `scripts/install_boot_splash_autostart.sh`
- `scripts/set_lab_ble_name.py`
- `production/RevA1-nrf52840-dongle/BOM_RevA5_Dongle_DK_Buttons.csv`
- `production/RevA1-nrf52840-dongle/ASSEMBLY_AND_FLASHING_INSTRUCTIONS_RevA5_BUTTONS.md`

## Safety boundary

This package is for authorized Bluetooth research, BLE inventory, local logging, AI companion behavior, and safe lab validation only.

## Main Pi commands

```text
scan                         Run a safe BLE inventory scan
summary                      Summarize observed BLE devices
show                         Show device table
eucalyptus status            Show always-on passive BLE logger status
eucalyptus start             Start always-on passive BLE logger
eucalyptus stop              Stop always-on passive BLE logger
eucalyptus restart           Restart always-on passive BLE logger
eucalyptus upload-status     Show WiGLE upload readiness/status
koala_kapture                Capture and archive BLE advertisement metadata
koala_kry                    Replay captured metadata offline into the report/XP pipeline
ear_tag                      Safe named lab BLE beacon skill
urban_poaching               Authorized BLE RSSI lab game
buttons                      Show/check GPIO front-panel button status
level/status                 Show XP and rank
report                       Write Markdown report
wake killerkoala             Test wake-word flow
authorized_ble_inventory     Generate authorized BLE inventory artifact
gatt_readiness_checklist     Generate owned-device GATT readiness checklist
pairing_security_review      Generate pairing/access-control review notes
lab_beacon_plan              Generate safe lab beacon/peripheral plan
packet_capture_notes         Generate protocol-analysis notes for owned/lab traffic
defensive_report             Generate defensive lab report template
lab                          Password-gated Authorized Lab Use menu
settings                     Device and companion settings
shutdown_confirm             Confirm safe shutdown
quit                         Exit
```

## Full function menu

The Pi companion menu uses the shared catalog at:

```text
pi-companion/koalablue/menu_catalog.py
```

Controls:

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

Validate the terminal menu:

```bash
cd pi-companion
PYTHONPATH=. python ../scripts/run_menu_screen.py
```

## First ESP32 flash

```bash
git clone https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
python3 -m pip install --user platformio
bash scripts/flash_esp32.sh
```

## First nRF52840 DK flash

Install Nordic nRF Connect SDK first, then:

```bash
git clone https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
python3 scripts/set_lab_ble_name.py EarTag-Lab
bash scripts/flash_nrf52840_dk_lab.sh
```

## Button test

```bash
python3 scripts/test_gpio_buttons.py
```
