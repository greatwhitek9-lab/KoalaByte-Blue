# KoalaByte Blue RevA17 Dongle-Only Production Package / RevA25 Heltec Wireless Tracker V2 GNSS Update

## Current production target

This package is the current source of truth for the KoalaByte Blue stacked Pi 3B+ production-style build.

Retained BLE hardware:

```text
Nordic nRF52840 USB Dongle / PCA10059 / NRF52840-DONGLE
```

The build is **dongle-only** and **no-custom-PCB**. It uses off-the-shelf modules, short USB/JST wiring, M2.5 standoffs, a protected 2S 18650 power layer, the Seloky USB-C PD/QC 12 V trigger board, a 5 V buck converter, optional 3D printed enclosure parts, the optional InnoMaker USB to CAN Converter kit for Koala Kan Kommander, and the optional Heltec Wireless Tracker V2 USB-C LoRa/GNSS node for Didgeridoo.

## Architecture

```text
Top antenna / RF area:  ESP32-S3 2.4 GHz antenna + Wireless Tracker V2 LoRa antenna + GNSS sky-view/optional GNSS antenna provision
Front/UI layer:         ESP32-S3 DualEye module, 2x round 1.28 in LCDs, mic path
LoRa/GNSS layer:        Optional Heltec Wireless Tracker V2 for Didgeridoo
BLE/CAN service layer:  Nordic nRF52840 USB Dongle / PCA10059 + optional InnoMaker USB-to-CAN kit
Main computer layer:    Raspberry Pi 3 Model B+
Power layer:            2x protected 18650 cells, BMS/protection, Seloky USB-C PD/QC 12 V trigger, 5 V 3 A buck
Controls:               Six-button front panel wired to Raspberry Pi GPIO
Audio:                  8 ohm 2 W mini speaker
Enclosure:              Optional 3D printed eucalyptus-green koala-ear case / stacked frame
```

## Production BOM

Use only the current BOM:

```text
production/RevA17-dongle-only/BOM_RevA17_DongleOnly.csv
```

The BOM includes the Raspberry Pi 3B+, ESP32-S3 DualEye, Nordic nRF52840 USB Dongle, six-button front panel, speaker, antennas, 2S protected 18650 power system, **Seloky USB-C PD Trigger Board Module PD/QC Decoy Fast Charge USB Type-C to 12V**, 5 V 3 A buck converter, cabling, fasteners, frame plates, optional printed enclosure parts, the optional **InnoMaker USB to CAN Converter kit**, and the optional **Heltec Wireless Tracker V2 USB-C LoRa/GNSS node** for Didgeridoo.

## RevA25 Didgeridoo Heltec Wireless Tracker V2 GNSS option

Physical USB path:

```text
Raspberry Pi 3B+ USB host
  -> short internal USB-A to USB-C data cable
  -> Heltec Wireless Tracker V2 USB-C LoRa/GNSS node
```

Why this board is preferred for GPS/GNSS:

- ESP32-S3FN8 host MCU.
- SX1262 LoRa radio.
- UC6580 GNSS receiver.
- GPS, GLONASS, BDS, Galileo, NAVIC, and QZSS support through the GNSS receiver.
- USB-C interface for power, flashing/debugging, and serial connection to the Raspberry Pi.
- Meshtastic-compatible board class.

Mechanical and antenna requirements:

1. The Heltec Wireless Tracker V2 mounts internally in the USB service layer or side/rear service bay.
2. The node connects to the Raspberry Pi by USB. Do **not** use Raspberry Pi GPIO for this USB Meshtastic/GNSS node path.
3. Keep one 2.4 GHz antenna opening for the ESP32-S3 DualEye IPEX1/U.FL Wi-Fi/Bluetooth antenna path.
4. Add one smaller LoRa antenna opening for the Wireless Tracker V2 LoRa IPEX/U.FL antenna connector. Match the antenna to the purchased LoRa band: 470-510 MHz, 863-870 MHz, or 902-928 MHz.
5. The Wireless Tracker V2 has onboard Wi-Fi/Bluetooth 2.4 GHz antenna hardware. Do not add a separate external 2.4 GHz case hole for the tracker unless the exact board revision and hardware docs explicitly call for one.
6. Provide GNSS sky-view clearance: use plastic above/around the GNSS antenna area and avoid placing the GNSS antenna path under battery cells, the speaker magnet, metal screws, metal standoffs, or dense wire bundles.
7. If the production build intentionally uses an external GNSS antenna, add a GNSS antenna opening or internal GNSS antenna pad location as a separate mechanical feature. Follow the Heltec hardware documentation for switching the GNSS antenna path to IPEX/U.FL.
8. Do not connect a 2.4 GHz antenna to the LoRa connector. Do not connect the LoRa antenna to any 2.4 GHz antenna connector.
9. Keep LoRa coax and any GNSS coax separated from the buck converter, 18650 battery wiring, fan motor, speaker magnet, CAN harness, and USB bundle.

Recommended case/top-plate RF layout:

```text
Top / rear RF area
  [2.4 GHz opening] ESP32-S3 DualEye Wi-Fi/Bluetooth antenna
  [small LoRa opening] Wireless Tracker V2 LoRa antenna
  [GNSS sky-view zone] non-metal/plastic clearance above tracker GNSS antenna
  [optional GNSS opening] only if using external GNSS IPEX/U.FL antenna
```

Software requirements:

```bash
PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py status
PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py meshtastic-login --connection serial --port /dev/ttyUSB0 --verify
PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py meshtastic-info
```

Didgeridoo Phase 1 is setup/status/profile only. It does not send raw LoRa packets or Meshtastic text messages.

## RevA23 InnoMaker Koala Kan Kommander option

Physical path:

```text
Raspberry Pi 3B+ USB host
  -> short internal USB cable
  -> InnoMaker USB to CAN Converter kit
  -> adapter-side CAN_H / CAN_L / GND / optional SHIELD
  -> authorized bench harness or owned-device test network
```

Mechanical requirements:

1. Do **not** use the earlier circular CAN panel port.
2. Mount the InnoMaker converter internally, in the Level 2 USB service bay, or at the side/rear service area.
3. Use a rectangular service slot or internal mount with cable strain relief if the adapter-side CAN connector must be accessible.
4. Keep the adapter and CAN wiring away from antennas, battery contacts, speaker grille, and the Raspberry Pi GPIO header.
5. Do not wire CAN_H or CAN_L directly to Raspberry Pi GPIO.

Software requirements:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py status --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py listen --interface can0 --duration 10
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py report --interface can0
```

The production plug-in is passive by default and `transmit-placeholder` remains blocked.

## Power path

The current USB-C power input part is:

```text
Seloky USB-C PD Trigger Board Module PD/QC Decoy Fast Charge USB Type-C to 12V
```

Recommended path:

```text
USB-C PD/QC charger capable of 12 V
  -> Seloky USB-C PD/QC 12 V trigger board
  -> 5 V 3 A buck converter
  -> fused regulated 5 V rail
  -> Raspberry Pi / ESP32-S3 DualEye / USB peripherals
```

Validation requirements:

- Verify the Seloky trigger board outputs about 12 V with a multimeter before connecting the buck converter.
- Do not connect the Seloky 12 V output directly to the Raspberry Pi or 5 V modules.
- Verify the buck output is 4.9 V to 5.1 V under normal load before closing the case.

## Firmware and software paths

Retained firmware/software paths:

```text
firmware/esp32-dualeye/
firmware/nrf52840-dongle-ear-tag-tx-lab/
pi-companion/
scripts/
```

Main retained companion features:

- `killerkoala` AI companion vocabulary and XP leveling.
- `eucalyptus` always-on passive Bluetooth/BLE scanner/logger naming and config.
- Koala BlueZ local adapter inventory/status/discovery/monitor helpers.
- Koala Kapture passive metadata capture.
- Koala Kry offline metadata replay/report pipeline.
- KoalaByte Lab synthetic owned-device BLE advertisement firmware for the USB Dongle.
- Koala Konnect optional external Bluetooth adapter mode for the USB Dongle.
- Koala Mode Switcher Pi-side controller for preparing and selecting the dongle firmware profile.
- Koala Kan Kommander passive InnoMaker USB-to-CAN status/listen/report workflow.
- Didgeridoo Heltec Wireless Tracker V2 Meshtastic LoRa/GNSS node setup, login profile, and node-info workflow.

## Flash-ready validation flow

Run this first from the repository root:

```bash
python3 scripts/check_repo_readiness.py
```

Expected output:

```text
KoalaByte Blue repo readiness check passed.
Ready-to-flash file wiring is present for ESP32, nRF52840 Dongle/DFU, Pi companion, Koala Kan Kommander InnoMaker CAN support, and Didgeridoo Heltec Wireless Tracker V2 GNSS setup.
```

Primary all-component helper:

```bash
bash scripts/flash_all_components.sh --all
```

Useful alternatives:

```bash
bash scripts/flash_all_components.sh --pi
NO_MONITOR=1 ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --nrf-lab
bash scripts/flash_all_components.sh --all --build-only
bash scripts/flash_all_components.sh --all --smoke
```

## ESP32-S3 DualEye flashing

```bash
bash scripts/flash_esp32.sh
NO_MONITOR=1 ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_esp32.sh
```

Expected behavior:

- KoalaByte Blue animated boot splash appears.
- DualEye firmware emits serial boot JSON.
- Serial JSON includes `"boot_animation":1`.

## Raspberry Pi companion install

```bash
bash scripts/install_pi.sh
```

The installer creates/updates the Pi companion virtual environment, installs Python dependencies, runs `compileall`, and runs `scripts/check_repo_readiness.py`.

Useful smoke tests:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py status
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py status --xp 100
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
PYTHONPATH=pi-companion python3 scripts/run_didgeridoo.py manifest
```

## nRF52840 Dongle build and DFU

Build the default KoalaByte Lab dongle firmware:

```bash
bash scripts/build_nrf52840_dongle_lab.sh
```

Create the DFU package:

```bash
bash scripts/flash_nrf52840_dongle_lab_dfu.sh
```

Flash after placing the Dongle in bootloader mode and identifying the DFU serial port:

```bash
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_nrf52840_dongle_lab_dfu.sh
```

Expected BLE advertisement name after the default lab firmware is flashed:

```text
KoalaByte Lab
```

The advertisement is synthetic, clearly labeled, and intended for owned-device signal-integrity observation only. It does not replay captured packets or captured identifiers.

## Koala Mode Switcher

Koala Mode Switcher prepares and selects between the two supported nRF52840 Dongle profiles:

```text
KoalaByte Lab   default BLE lab advertisement profile
Koala Konnect   optional USB HCI external Bluetooth adapter profile
```

Show current mode and artifacts:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py status
```

Build and create DFU ZIPs for both profiles:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py prepare-all
```

Select KoalaByte Lab after placing the dongle in bootloader mode:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py switch koalabyte_lab --dfu-port /dev/ttyACM0
```

Select Koala Konnect after placing the dongle in bootloader mode:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py switch koala_konnect --dfu-port /dev/ttyACM0
```

State and event logs:

```text
logs/dongle_mode_state.json
logs/dongle_mode_events.jsonl
```

See:

```text
docs/KOALA_MODE_SWITCHER_REVA21.md
docs/KOALA_KONNECT_REVA20.md
```

## Koala Konnect external Bluetooth adapter mode

Koala Konnect is an optional alternate firmware profile for the same nRF52840 USB Dongle. It turns the dongle into a USB HCI Bluetooth controller for a compatible phone or computer host.

Only one dongle firmware mode can be installed at a time. Use Koala Mode Switcher to select KoalaByte Lab or Koala Konnect.

## Six-button front panel

Use six normally-open tactile buttons, numbered left to right:

```text
1 Main Menu | 2 Left/Back | 3 Enter/Select + hold Shutdown | 4 Right/Forward | 5 Up | 6 Down
```

GPIO wiring:

| Button # | Function | Pi BCM GPIO | Pi physical pin | Button other side |
|---:|---|---:|---:|---|
| 1 | Main Menu | GPIO5 | 29 | GND |
| 2 | Move Left / Back | GPIO6 | 31 | GND |
| 3 | Enter / Select; hold for Shutdown | GPIO13 | 33 | GND |
| 4 | Move Right / Forward | GPIO19 | 35 | GND |
| 5 | Up | GPIO26 | 37 | GND |
| 6 | Down | GPIO21 | 40 | GND |
| Shared ground | GND bus | GND | 39 | All button grounds |

Test buttons:

```bash
python3 scripts/test_gpio_buttons.py
```

## Validation checklist

- [ ] `python3 scripts/check_repo_readiness.py` passes.
- [ ] `bash scripts/flash_all_components.sh --check-only` passes.
- [ ] `python -m compileall pi-companion scripts` passes.
- [ ] Seloky trigger board output measures about 12 V before the buck converter.
- [ ] 5 V rail measures 4.9 V to 5.1 V under normal load.
- [ ] ESP32 firmware builds with PlatformIO.
- [ ] nRF52840 Dongle KoalaByte Lab firmware builds with nRF Connect SDK / Zephyr.
- [ ] Optional Koala Konnect firmware builds when `BUILD_KOALA_KONNECT=1` or `scripts/build_koala_konnect.sh` is used.
- [ ] Koala Mode Switcher `status` command writes `logs/dongle_mode_state.json`.
- [ ] Koala Mode Switcher `prepare-all` creates both expected DFU ZIPs.
- [ ] Raspberry Pi companion installs with `scripts/install_pi.sh`.
- [ ] Pi boots without undervoltage warning.
- [ ] nRF52840 Dongle enumerates over USB.
- [ ] ESP32 DualEye boot animation and serial JSON are visible.
- [ ] Heltec Wireless Tracker V2 enumerates by USB as `/dev/ttyUSB*` or `/dev/ttyACM*` when connected.
- [ ] Didgeridoo `status`, `meshtastic-login`, and `meshtastic-info` checks complete for the connected node.
- [ ] Wireless Tracker V2 reports valid GNSS/location data after correct firmware, antenna path, region, and sky-view checks.
- [ ] Koala BlueZ inventory/status commands run.
- [ ] Koala Kan Kommander detects the InnoMaker adapter as a SocketCAN interface such as `can0` when installed.
- [ ] killerkoala voice preview returns an XP-scaled response.
- [ ] eucalyptus writes passive BLE capture/log output under `/blecaptures` when enabled.
- [ ] All six front buttons generate the expected GPIO events.
- [ ] Button 3 short press emits `select`; Button 3 hold emits `shutdown`.
- [ ] Battery, BMS, buck converter, switch, cable strain relief, antenna openings, GNSS sky-view clearance, optional Wireless Tracker V2 mount, and optional InnoMaker adapter mount pass inspection.

## Safety boundary

KoalaByte Blue is for lawful educational research, defensive testing, owned-device lab work, authorized Bluetooth assessment, scoped CAN observation, and authorized Meshtastic/LoRa/GNSS node configuration only. Passive capture, local logging, synthetic owned-device lab advertising, Koala Mode Switcher DFU use, Koala Konnect host-adapter use, Koala Kan Kommander passive observation, Didgeridoo node setup/status, and all Bluetooth/CAN/LoRa/GNSS activity must remain scoped to environments where you have permission.
