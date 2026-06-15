# KoalaByte Blue RevA17 Assembly, Flashing, and Readiness Guide

## Current software/firmware stack

- ESP32-S3 DualEye boot screen and menu-theme helper firmware.
- Raspberry Pi companion with boot splash, jungle/eucalyptus menu, Koala BlueZ helpers, and killerkoala vocabulary.
- nRF Connect SDK / Zephyr firmware for the optional nRF52840 DK Ear Tag TX Lab beacon.
- Six-button Raspberry Pi front-panel navigation.
- No custom PCB required.

## Ready-to-flash repository check

From the repository root, run:

```bash
python3 scripts/check_repo_readiness.py
```

Expected output:

```text
KoalaByte Blue repo readiness check passed.
Ready-to-flash file wiring is present for ESP32, nRF52840 DK/Zephyr, and Pi companion.
```

The older `scripts/check_boot_animation_config.py` file remains only as a compatibility wrapper.

## Button hardware

The nRF52840 Dongle includes one tiny onboard user button, but it is not enough for a front-panel user interface. The production build uses:

```text
Adafruit Tactile Button switch (6mm) x 20 pack, Product ID 367
```

Use six buttons from the pack:

```text
1 Main Menu | 2 Left/Back | 3 Enter/Select + hold Shutdown | 4 Right/Forward | 5 Up | 6 Down
```

## Button wiring

| Button # | Function | Pi BCM GPIO | Pi physical pin | Button other side |
|---:|---|---:|---:|---|
| 1 | Main Menu | GPIO5 | 29 | GND |
| 2 | Move Left / Back | GPIO6 | 31 | GND |
| 3 | Enter / Select; hold for Shutdown | GPIO13 | 33 | GND |
| 4 | Move Right / Forward | GPIO19 | 35 | GND |
| 5 | Up | GPIO26 | 37 | GND |
| 6 | Down | GPIO21 | 40 | GND |
| Shared ground | GND bus | GND | 39 | All button grounds |

Each button is normally open. One leg goes to the assigned GPIO pin, and the other leg goes to GND. The software uses internal pull-up resistors.

## Raspberry Pi companion installation

From the repository root on the Raspberry Pi:

```bash
bash scripts/install_pi.sh
```

The installer now runs Python compile checks and the consolidated repo readiness check.

Test the boot splash:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
```

Test the jungle/eucalyptus menu:

```bash
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
```

Test Koala BlueZ:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py inventory
```

Test killerkoala vocabulary:

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py status --xp 100
```

## ESP32 flashing

From the repository root:

```bash
python3 scripts/check_repo_readiness.py
bash scripts/flash_esp32.sh
```

Expected ESP32 display behavior:

```text
KoalaByte Blue animated boot splash appears first
Left eye pulses purple
Right eye pulses blue
Progress bar completes
Firmware then emits normal serial JSON boot message
```

Expected serial JSON includes:

```json
{"boot_animation":1}
```

If the display remains blank but serial boot JSON appears, confirm the exact TFT_eSPI LCD setup for the ESP32-S3 DualEye board revision.

## nRF52840 DK / Zephyr flashing

Build only:

```bash
bash scripts/build_nrf52840_dk_lab.sh
```

Build and flash:

```bash
bash scripts/flash_nrf52840_dk_lab.sh
```

Expected BLE advertisement name:

```text
EarTag-TX-Lab
```

This is a synthetic owned-device lab advertisement. It does not replay captured packets or identifiers.

## Step-by-step button build

1. Print or drill a six-button front panel.
2. Dry-fit six tactile switches in the bezel/front panel and label the positions left-to-right as 1 through 6.
3. Solder or crimp one signal wire to each button.
4. Daisy-chain the other side of all six buttons to a shared black GND wire.
5. Connect Button 1 to Pi GPIO5 / physical pin 29.
6. Connect Button 2 to Pi GPIO6 / physical pin 31.
7. Connect Button 3 to Pi GPIO13 / physical pin 33.
8. Connect Button 4 to Pi GPIO19 / physical pin 35.
9. Connect Button 5 to Pi GPIO26 / physical pin 37.
10. Connect Button 6 to Pi GPIO21 / physical pin 40.
11. Connect the shared ground to Pi physical pin 39.
12. Add heat-shrink and strain relief so the button harness cannot pull on the Pi header.
13. Run the six-button GPIO test from the repo root:

```bash
python3 scripts/test_gpio_buttons.py
```

14. Press each button from left to right and verify the output matches buttons 1 through 6.
15. Hold Button 3 for 3 seconds and verify a `shutdown` hold event is printed.

## Validation checklist

- [ ] `python3 scripts/check_repo_readiness.py` passes.
- [ ] Pi boots without undervoltage warning.
- [ ] Pi companion dependencies install with `scripts/install_pi.sh`.
- [ ] Pi boot splash runs in windowed test mode.
- [ ] Pi jungle/eucalyptus graphical menu runs in windowed test mode.
- [ ] Koala BlueZ inventory reports available local BlueZ tools.
- [ ] killerkoala voice preview returns an XP-scaled response.
- [ ] ESP32 firmware builds with PlatformIO.
- [ ] ESP32 boot animation appears on the DualEye display.
- [ ] ESP32 serial JSON boot message includes `boot_animation`.
- [ ] nRF52840 DK Zephyr firmware builds.
- [ ] nRF52840 DK advertises as `EarTag-TX-Lab`.
- [ ] nRF52840 Dongle enumerates on USB for the compact production build.
- [ ] All six front buttons generate GPIO button events.
- [ ] Button 3 short press emits `select`.
- [ ] Button 3 hold emits `shutdown`.
- [ ] Shared GND bus is secure.
- [ ] Button harness has strain relief.
- [ ] Case closes without pinching wires.
- [ ] 5V rail remains within 5.05 V to 5.15 V under load.
