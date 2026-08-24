# KoalaByte Blue documentation

This directory contains operational, hardware, runtime, and authorized-lab reference material for KoalaByte Blue. Start with the [project README](../README.md) for the canonical installation and deployment sequence.

## Installation and recovery

- [Flashing](FLASHING.md) — firmware flashing and recovery workflow.
- [Install dependencies](INSTALL_DEPENDENCIES.md) — host and toolchain prerequisites.
- [nRF Connect SDK local setup](NCS_LOCAL_SETUP.md) — Nordic/Zephyr environment setup.
- [Pi hardware stage](PI_HARDWARE_STAGE.md) — Raspberry Pi hardware preparation.
- [HDMI display switch](HDMI_DISPLAY.md) — optional eyes, mouth, menu, and Koalagotchi monitor output with Raspberry Pi OS switching.
- [SD card formatter](SD_CARD_FORMATTER.md) — media preparation.
- [Live-boot SD maintenance](LIVE_BOOT_SD_MAINTENANCE.md) — offline repair and maintenance.

## Hardware, nodes, and user interface

- [8-key button board](8_KEY_BUTTON_BOARD.md) — K1-K8 wiring and controls.
- [Main BLE node roles](MAIN_BLE_NODE_ROLES.md) — Pi, ESP32-S3, and Heltec BLE ownership/failover.
- [Theme and menu system](THEME_AND_MENU_SYSTEM.md) — display and menu behavior.
- [Lyrebird music player](LYREBIRD.md) — Pi-owned music, radio presets, voice/menu controls, and speech ducking.
- [Preboot mode selector](PREBOOT_MODE_SELECTOR.md) — startup mode selection.
- [Split loading sequence](SPLIT_LOADING_SEQUENCE.md) — coordinated boot/loading behavior.
- [Heltec V2 feature notes](MINED_HELTEC_V2_FEATURES.md) — Heltec feature reference.

## Production and field readiness

- [Production files](PRODUCTION_FILES.md) — production-facing file inventory.
- [Field-readiness upgrades](FIELD_READINESS_UPGRADES.md) — hardening and deployment notes.
- [External antenna configuration](../scripts/configure_koalabyte_external_antennas.sh) — antenna setup script.
- [nRF52840 dongle flashing](NRF52840_DONGLE_FLASHING.md) — dongle firmware procedure.

## Authorized lab tools

Use these components only on systems, radios, networks, captures, vehicles, and test benches you own or are explicitly authorized to assess.

- [Authorized lab actions](AUTHORIZED_LAB_ACTIONS.md) — scope and operating constraints.
- [TwoCAN read-only tools](TWOCAN_READ_ONLY_TOOLS.md) — passive/read-only CAN tooling.
- [Koala BlueZ tools](KOALA_BLUEZ_TOOLS_REVA16.md) — Bluetooth tooling.
- [Koala KRY](KOALA_KRY_REVA12.md)
- [Koala Kapture](KOALA_KAPTURE_REVA12.md)
- [Koala Konnect](KOALA_KONNECT_REVA20.md)
- [Urban Poaching](URBAN_POACHING_REVA10.md)
- [Ear Tag TX Lab](EAR_TAG_TX_LAB_REVA15.md)
- [That's Not a Knife service](THATS_NOT_A_KNIFE_SERVICE.md)

## Documentation maintenance

When changing behavior, update the relevant document in the same pull request. Keep commands copy-pasteable, identify the target hardware explicitly, and distinguish verified behavior from planned work. Do not commit generated logs, release bundles, credentials, local SDK worktrees, or PlatformIO build output.
