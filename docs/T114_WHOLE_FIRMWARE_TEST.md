# T114 Whole-Firmware Test Plan

This test plan validates the KoalaByte Blue stack with the **Heltec Mesh Node T114 V2** used in the nRF52840 role **instead of the Nordic nRF52840 Dongle for the test run only**.

The Nordic nRF52840 Dongle remains the production default until T114 build, flash, enumeration, and KoalaByte Lab BLE behavior are proven.

## Test goal

Validate this alternate stack:

```text
Raspberry Pi 3B+
  -> ESP32-S3 DualEye UI firmware
  -> Heltec Mesh Node T114 V2 alternate nRF52840 KoalaByte Lab firmware
  -> optional InnoMaker USB-to-CAN manifest check
  -> Didgeridoo / Wireless Tracker V2 setup-status checks
  -> Pi companion menu and local smoke checks
```

The test intentionally skips the Nordic nRF52840 Dongle build/flash path.

## Required inputs

Before running a real T114 build, confirm the exact Zephyr/NCS board target for the T114 board support package:

```bash
export T114_BOARD=<confirmed_zephyr_board_target>
```

If flashing, also confirm the exact bootloader/vendor flash command:

```bash
export T114_FLASH_CMD='<confirmed flash command>'
export T114_PORT=/dev/ttyACM0   # example only
```

Do not guess the board target or bootloader method. The helper refuses to build or flash when those values are missing.

## Build-only full-stack test

Use this first. It runs repo readiness, Python compile checks, safe Pi companion smoke checks, ESP32 build if PlatformIO is available, and the T114 nRF build helper.

```bash
T114_BOARD=<confirmed_zephyr_board_target> \
bash scripts/test_t114_as_dongle_replacement.sh --build-only
```

## Hardware flash test

Run this only after the T114 board target and flash command are verified:

```bash
T114_BOARD=<confirmed_zephyr_board_target> \
T114_PORT=/dev/ttyACM0 \
T114_FLASH_CMD='<confirmed flash command>' \
bash scripts/test_t114_as_dongle_replacement.sh --flash-t114
```

## What the script verifies

- Repository readiness check passes.
- Pi companion Python and script files compile.
- Safe local Pi companion manifests/status checks run.
- ESP32-S3 DualEye firmware build is attempted unless skipped.
- T114 alternate nRF52840 KoalaByte Lab build is attempted.
- T114 flash is attempted only with `--flash-t114` and a confirmed `T114_FLASH_CMD`.
- Nordic nRF52840 Dongle DFU is not used in this test path.

## Useful skip flags

```bash
bash scripts/test_t114_as_dongle_replacement.sh --build-only --skip-esp32
bash scripts/test_t114_as_dongle_replacement.sh --build-only --skip-smoke
bash scripts/test_t114_as_dongle_replacement.sh --build-only --skip-can
```

## Pass criteria

- T114 build completes under `build/nrf52840-t114-lab/`.
- If flashing is enabled, the T114 flashes with the confirmed method.
- The board enumerates over USB after flashing.
- KoalaByte Lab BLE behavior is visible from an authorized local scanner.
- ESP32-S3 DualEye build still succeeds.
- Pi companion menu and local modules still import and run their safe smoke checks.

## Fail criteria

Stop and do not treat T114 as a replacement if any of these occur:

- `T114_BOARD` is unknown.
- T114 build requires board-specific overlays that are not present.
- T114 flash method is unknown.
- The board does not enumerate after flashing.
- KoalaByte Lab BLE behavior is not visible.
- The T114 firmware breaks Pi companion assumptions.

## Next step after passing

If this test passes repeatedly, create a dedicated T114 firmware directory and board-specific overlay instead of continuing to reuse the dongle app directory directly:

```text
firmware/nrf52840-t114-koalabyte-lab/
```

Until then, the T114 remains an alternate validation target, not the production default.
