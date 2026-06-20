# Heltec Mesh Node T114 V2 Alternate nRF52840 Target

This guide adds the Heltec Mesh Node T114 V2 style board as an **alternate nRF52840 target** for KoalaByte Blue. It does **not** replace the Nordic nRF52840 USB Dongle / PCA10059 path yet.

The current stable production path remains:

```text
Nordic nRF52840 USB Dongle / PCA10059
  -> KoalaByte Lab / Koala Konnect firmware
```

The alternate experimental path is:

```text
Heltec Mesh Node T114 V2 style board
  -> nRF52840 + SX1262 LoRa + display/GNSS-capable tracker hardware
  -> opt-in KoalaByte Lab firmware target
```

## Why this is not a drop-in replacement yet

The existing KoalaByte Blue nRF firmware build is configured around the Nordic dongle board target:

```text
nrf52840dongle_nrf52840
```

The T114 board is also nRF52840-based, but its board definition, GPIO map, display pins, LoRa pins, bootloader, and flash method may differ. Because of that, the repo now treats T114 as an alternate target until hardware validation is complete.

## What stays the same

The following can mostly stay the same:

- KoalaByte Lab naming
- Koala Mode Switcher concept
- Pi companion menu structure
- nRF Connect SDK / Zephyr build flow
- KoalaByte Lab BLE advertisement app logic, as a first porting base
- Repository default Nordic Dongle support

## What changes

The T114 path needs separate handling for:

- Zephyr board target name
- Flash/upload method
- Button/display/LoRa/GNSS pin definitions
- Any board-specific devicetree overlays
- Whether the board is running KoalaByte firmware or Meshtastic firmware

## Build command

Set the Zephyr board target once it is confirmed for the exact T114 board support package:

```bash
T114_BOARD=<confirmed_zephyr_board_target> bash scripts/build_nrf52840_t114_lab.sh
```

Examples of how to test discovery:

```bash
bash scripts/build_nrf52840_t114_lab.sh
T114_BOARD=heltec_t114_nrf52840 bash scripts/build_nrf52840_t114_lab.sh
```

If `T114_BOARD` is not set and the helper cannot find a supported candidate in the current Zephyr/NCS workspace, it exits with guidance instead of silently building for the wrong board.

## Flash command

The T114 flash method is intentionally not hard-coded yet. Use a confirmed vendor/bootloader flash command:

```bash
T114_FLASH_CMD='<confirmed flash command>' bash scripts/flash_nrf52840_t114_lab.sh
```

The helper substitutes these placeholders when present:

```text
{HEX}       built Zephyr HEX path
{BIN}       built Zephyr BIN path
{UF2}       built Zephyr UF2 path if produced
{PORT}      T114 serial/DFU port from T114_PORT
{BUILD_DIR} T114 build directory
```

Example pattern only:

```bash
T114_PORT=/dev/ttyACM0 \
T114_FLASH_CMD='west flash -d {BUILD_DIR}' \
bash scripts/flash_nrf52840_t114_lab.sh
```

## Firmware role warning

The T114 board can be used as either a KoalaByte nRF target or a Meshtastic node, but not both at the same time unless a future custom firmware combines those roles.

Recommended staged approach:

1. Keep the Nordic nRF52840 Dongle as the production default.
2. Add and validate the T114 build target.
3. Confirm USB enumeration and flash method.
4. Confirm KoalaByte Lab BLE behavior.
5. Only then decide whether to promote T114 from alternate target to production replacement.

## Current scope

Included now:

- Alternate T114 nRF52840 build helper
- Alternate T114 flash helper wrapper
- `flash_all_components.sh --nrf-t114-lab` opt-in path
- Documentation for keeping the Nordic dongle default

Not included yet:

- T114-specific devicetree overlay
- T114 display integration
- T114 SX1262 LoRa control in KoalaByte firmware
- T114 GNSS parsing in KoalaByte firmware
- Replacing the Nordic dongle in production defaults
