# Production Files

This repository documents the current **KoalaByte Blue V2 Heltec Edition** no-custom-PCB production profile. The active architecture uses a Raspberry Pi 3B+, ESP32-S3 DualEye, **Heltec Mesh Node T114 onboard nRF52840 as the primary BLE board**, optional InnoMaker USB-to-CAN, and a simplified regulated USB portable power-bank power path.

The external Nordic nRF52840 USB Dongle files remain in the repository as explicit legacy compatibility targets only. They are not the default BLE board for the Heltec Edition.

## Current Heltec Edition package

Current production references:

- `README.md` - KoalaByte Blue V2 Heltec Edition quick-start and operation index.
- `docs/FLASHING.md` - Heltec Edition flashing, install, dependency, and node-role guide.
- `docs/ORDERABLE_PARTS_LIST.md` - current orderable hardware list with Heltec T114 as the primary BLE/LoRa board.
- `docs/MAIN_BLE_NODE_ROLES.md` - BLE node role model: Heltec T114 nRF52840 primary, ESP32-S3 secondary node, Raspberry Pi BlueZ secondary/fallback node.
- `docs/PRODUCTION_FILES.md` - this current production index.
- `docs/POWER_BANK_WIRING_MAIN.svg` - current text/SVG wiring diagram for the USB power-bank power path.
- `production/WIRING_DIAGRAM_ANTENNAS.md` - ESP32-S3 DualEye external 2.4 GHz antenna wiring guide.
- `production/WIRING_DIAGRAM_ANTENNAS.svg` - visual ESP32-S3 DualEye antenna wiring diagram.

## Current firmware/software production files

- `firmware/esp32-dualeye/` - ESP32-S3 DualEye firmware, boot animation, theme assets, external 2.4 GHz antenna mode reporting, voice front-end metadata, and secondary local BLE-node support.
- `firmware/esp32-dualeye/voice_commands/` - WakeNet/MultiNet command alias planning files for ESP32-S3 voice activation.
- `firmware/esp32-dualeye/themes/` - active theme and approved SVG visual source-of-truth assets.
- `pi-companion/` - Raspberry Pi companion app, menu, theme, and helper modules.
- `pi-companion/koalablue/ble_event_log.py` - BLE event normalization and source priority. The Heltec T114 nRF52840 is the primary source.
- `pi-companion/koalblue/` - not used; keep new code under `pi-companion/koalablue/`.
- `pi-companion/koalablue/ble_node_manager.py` - Heltec T114 primary BLE node manager with ESP32-S3 and Raspberry Pi BlueZ nodes.
- `pi-companion/koalablue/killerkoala_vocabulary.py` - Raspberry Pi large-vocabulary companion engine with Aussie slang, XP rank tone changes, and anti-repeat phrase rotation.
- `scripts/check_repo_readiness.py` - current ready-to-run repository validation check for the Heltec Edition architecture.
- `scripts/setup_system_packages.sh` - installs/checks Raspberry Pi system packages, including Heltec T114 USB serial, udev, BlueZ, `python3-serial`, and serial terminal tools.
- `scripts/setup_heltec_t114_tools.sh` - Heltec-specific dependency helper. Checks `pyserial`, `bleak`, USB/udev/BlueZ commands, stable `/dev/koalabyte-heltec` aliases, port discovery, and optional `west`/`nrfutil`/NCS tooling.
- `scripts/discover_koalabyte_ports.py` - Heltec-first USB/CAN port discovery. Writes `KOALABYTE_PRIMARY_BLE_PORT`, `KOALABYTE_HELTEC_USB_PORT`, and secondary node paths.
- `scripts/preflight_all_hardware.py` - non-flashing Heltec Edition preflight report.
- `scripts/install_koalabyte_udev_rules.sh` - installs stable `/dev/koalabyte-heltec` and `/dev/koalabyte-esp32-eyes` aliases where udev can identify the devices.
- `scripts/run_ble_node_manager.py` - manual BLE node manager runner using `--primary-port` for the Heltec T114.
- `scripts/run_ble_node_manager_service.sh` - systemd service wrapper for continuous BLE node logging.
- `scripts/install_ble_node_manager_service.sh` - installs the persistent BLE node manager service.
- `scripts/configure_esp32s3_dualeye_2g4_antenna.sh` - writes ESP32-S3 DualEye external antenna status before ESP32 flashing.
- `scripts/flash_all_components.sh` - one-command Pi install, Heltec T114 dependency setup, ESP32 flash, Heltec-primary BLE node manager setup, InnoMaker CAN manifest helper, and USB power-bank checks.
- `scripts/build_firmware_all.sh` - firmware build helper. It builds ESP32 by default and builds legacy external nRF52840 targets only when explicitly requested.
- `scripts/flash_esp32.sh` - ESP32 build/upload helper.
- `scripts/install_pi.sh` - Pi companion dependency installer; runs the Heltec dependency helper by default and leaves legacy external dongle caches opt-in.
- `scripts/run_killerkoala_voice.py` - KillerKoala vocabulary preview and manifest writer.
- `scripts/run_koala_bluez.py` and `scripts/run_koala_bluez_*.sh` - Koala BlueZ runners.
- `scripts/run_koala_mode_switcher.py` - Koala Mode Switcher CLI runner.
- `scripts/run_koala_kan_kommander.py` - Koala Kan Kommander CLI runner.
- `.github/workflows/koalabyte-blue-ci.yml` - CI workflow using the readiness check.

## Legacy compatibility files

The following folders/files are retained for explicit legacy external dongle builds and bench comparisons only. They should not be described as the default Heltec Edition architecture:

```text
firmware/nrf52840-dongle-ble-primary/
firmware/nrf52840-dongle-ear-tag-tx-lab/
docs/NRF52840_DONGLE_FLASHING.md
scripts/build_nrf52840_dongle_ble_primary.sh
scripts/flash_nrf52840_dongle_ble_primary_dfu.sh
scripts/build_nrf52840_dongle_lab.sh
scripts/flash_nrf52840_dongle_lab_dfu.sh
scripts/build_nrf52840_dongle_hci_usb_adapter.sh
production/RevA17-dongle-only/
```

## Hardware architecture rule

```text
Heltec Mesh Node T114 onboard nRF52840
  -> primary BLE board / canonical BLE observation source

ESP32-S3 DualEye
  -> face, eyes, buttons, UI, voice front end, secondary local BLE node

Raspberry Pi 3B+
  -> companion brain, logging, reports, BlueZ secondary/fallback BLE node

InnoMaker USB-to-CAN kit
  -> optional isolated CAN bench adapter through Linux SocketCAN
```

No custom PCB is required. The build uses commercially available development boards/modules, USB cabling, standoffs, a PIFFA-style USB portable power bank, optional powered USB hub, optional InnoMaker USB-to-CAN accessory hardware, approved firmware theme assets, and an open-frame stacked layout.

## ESP32-S3 DualEye antenna rule

```text
ESP32-S3 DualEye 2.4 GHz / IPEX1-U.FL-MHF1 connector
  -> short IPEX/U.FL/MHF1 coax pigtail
  -> case-mounted SMA or RP-SMA bulkhead connector
  -> external 2.4 GHz WiFi/Bluetooth antenna
```

Use the external-antenna board variant when possible. If the board revision uses an antenna-selector resistor or jumper, configure it for the external IPEX/U.FL path according to the vendor documentation.

## Heltec T114 antenna rule

Use a frequency-matched LoRa antenna for the Heltec T114's regional band and connector. Do not run LoRa radio workflows without an appropriate antenna connected.

## KillerKoala voice/AI companion rule

```text
ESP32-S3 DualEye:
  wake word and short command recognition front end

Raspberry Pi:
  KillerKoala large-vocabulary companion brain
  Aussie/cyberpunk phrase variation
  XP/rank tone changes
  anti-repeat response rotation
```

The ESP32-S3 records the intended voice front-end stack at boot. The Pi generates the long companion response so KillerKoala does not repeat the same handful of phrases.

## CAN mechanical rule

The current Koala Kan Kommander physical option is the InnoMaker USB to CAN Converter kit. Do not use or reintroduce the earlier circular CAN panel port in current case notes or renderings. Use an internal mount or rectangular side/rear service-bay cutout with strain relief.

## USB power-bank mechanical rule

The current production path is powered by a PIFFA-style USB portable power bank through regulated USB output. Leave clearance for the Raspberry Pi 3B+ micro-USB power cable, USB cable bend radius, optional powered USB hub, Heltec T114 USB-C cable, ESP32-S3 DualEye USB-C cable, ESP32 antenna pigtail/bulkhead path, optional InnoMaker adapter, and strain relief. Do not route raw battery voltage to Pi GPIO, ESP32 GPIO, Heltec headers, button wiring, USB devices, or CAN wiring.

## Cleanup rule

The older standalone menu/boot notes were consolidated into `docs/THEME_AND_MENU_SYSTEM.md`. Keep future theme/menu updates there unless a new guide is genuinely separate.

## Readiness rule

The repository is considered current only when:

1. `python3 scripts/check_repo_readiness.py` passes.
2. CI can compile the Pi companion Python code and scripts.
3. ESP32 firmware builds with PlatformIO.
4. `scripts/setup_heltec_t114_tools.sh` is present and wired into the Pi/flasher install path.
5. Heltec T114 preflight identifies the primary BLE serial path or clearly reports it missing.
6. Optional Koala Kan Kommander files remain present and passive by default unless explicitly gated for bench simulator work.
7. `scripts/flash_all_components.sh --all` is documented as the primary all-component helper for the Heltec Edition.
8. The USB power-bank production guide and orderable parts list remain aligned.
