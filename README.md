# KoalaByte Blue / killerkoala AI Companion Firmware RevA25

<p align="center">
  <strong>Your Bluetooth sidekick in the wild.</strong><br>
  A Raspberry Pi 3B+ + ESP32-S3 DualEye + Nordic nRF52840 Dongle companion for safe Bluetooth research, passive logging, menu-driven field workflows, and optional isolated CAN bench work.
</p>

> **Important:** KoalaByte Blue is for lawful educational research, owned-device lab work, defensive testing, and authorized Bluetooth/CAN assessment only. Keep every scan, capture, review, and bench test inside your own lab or written scope.

---

## What is KoalaByte Blue?

KoalaByte Blue is a dongle-only, no-custom-PCB Bluetooth companion build. It wraps a Raspberry Pi, an ESP32-S3 DualEye display module, and a Nordic nRF52840 Dongle into a portable, themed device that can help you scan, log, review, report, and switch between safe lab firmware profiles without making setup painful.

In plain English: it is a small field/lab companion for Bluetooth inventory work, passive BLE observations, BlueZ helper workflows, an ESP32 menu/display experience, and an AI-style companion called **killerkoala**.

The current repo supports:

- Raspberry Pi 3B+ companion install and local helper tools.
- ESP32-S3 DualEye boot splash, menu display, and serial companion bridge.
- nRF52840 Dongle **KoalaByte Blue Lab Mode** firmware.
- Optional nRF52840 Dongle **Koala Konnect Mode** USB HCI adapter profile.
- Pre-boot dongle mode selector before the normal boot splash/menu flow.
- Outback BlueZ wrapped helper actions.
- Eucalyptus passive BLE logger controls.
- killerkoala voice/status/XP companion behavior.
- Optional **Koala Kan Kommander** CAN workflow for isolated bench simulators or owned harnesses only.

---

## Good use cases

KoalaByte Blue is a good fit for:

- **Bluetooth inventory work** — build a quick list of nearby BLE devices in a permitted lab, classroom, workshop, or owned environment.
- **Passive logging and field notes** — collect local observations and review them later.
- **Device readiness checks** — verify adapters, BlueZ tools, services, local permissions, and companion status.
- **Owned-device BLE testing** — review GATT readiness, pairing posture, beacon plans, and packet-capture notes for devices you own or are authorized to test.
- **Menu-driven demos** — use the ESP32-S3 DualEye display and grouped menu system for a polished handheld-device feel.
- **Offline reporting** — turn observations into Markdown reports, inventory artifacts, and review notes.
- **Optional CAN bench work** — use the InnoMaker USB-to-CAN adapter on an isolated simulator or owned harness only.

---

## Fast path: one simple flash/install action

Start with a normal Raspberry Pi OS install. KoalaByte Blue does **not** replace the Raspberry Pi operating system; the repo scripts install the companion software, firmware tools, SDK/toolchain helpers, cached DFU packages, boot splash, menu, and mode selector after the Pi can boot Linux.

Recommended base OS:

```text
Raspberry Pi OS Lite 64-bit
```

Recommended Raspberry Pi Imager options before first boot:

```text
Enable SSH
Set username and password
Set WiFi SSID/password if available
Set WiFi country, locale, and timezone
```

Minimal first-boot commands after the Pi is running:

```bash
sudo apt update
sudo apt install -y git

git clone https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
```

Run the readiness check:

```bash
python3 scripts/check_repo_readiness.py
```

Then run the all-component helper:

```bash
bash scripts/flash_all_components.sh --all
```

That one helper runs the repo readiness check, installs/updates the Pi companion, checks/prepares system dependencies, prepares ESP32 tooling, prepares nRF tooling, flashes/builds the selected firmware pieces, writes a Koala Kan Kommander manifest check, and keeps unsafe CAN transmit gated behind explicit bench flags.

Useful variants:

```bash
# Pi companion only
bash scripts/flash_all_components.sh --pi

# ESP32-S3 DualEye only
ESP32_PORT=/dev/ttyUSB0 bash scripts/flash_all_components.sh --esp32

# nRF52840 Dongle Lab profile only
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --nrf-lab

# Optional Koala Konnect USB HCI profile only
NRF_DFU_PORT=/dev/ttyACM0 bash scripts/flash_all_components.sh --nrf-konnect

# Build/package without flashing
bash scripts/flash_all_components.sh --all --build-only

# Safe local smoke checks after selected actions
bash scripts/flash_all_components.sh --all --smoke
```

If WiFi was not configured in Raspberry Pi Imager, allow the installer to prompt before SDK downloads:

```bash
WIFI_INTERACTIVE=1 \
STRICT_WIFI_FIRST_BOOT=1 \
STRICT_SYSTEM_PACKAGES=1 \
STRICT_ESP32_TOOLS=1 \
STRICT_DONGLE_CACHE=1 \
STRICT_NCS_TOOLCHAIN=1 \
bash scripts/install_pi.sh
```

---

## Hardware profile

KoalaByte Blue is designed as a dongle-only build using common modules and cables instead of a custom PCB.

### Core components

| Component | Exact model / type | Qty | Purpose |
|---|---|---:|---|
| Main SBC | Raspberry Pi 3 Model B+ | 1 | Main Linux computer and Pi companion host. |
| Display/UI/mic board | Waveshare ESP32-S3-DualEye-LCD-1.28 | 1 | Boot splash, menu UI, mic/front-end, serial companion bridge. |
| BLE dongle | Nordic nRF52840 Dongle / PCA10059 / NRF52840-DONGLE | 1 | BLE lab firmware profile or Koala Konnect USB HCI profile. |
| microSD card | 64GB high-endurance microSD recommended | 1 | Pi OS, logs, reports, artifacts. |
| 5V regulator | Pololu D24V50F5 or equivalent 5V 5A buck | 1 | Stable 5V rail. |
| USB-C PD trigger | Seloky USB-C PD/QC 12V trigger board or equivalent | 1 | USB-C input trigger before buck conversion. |
| Fuse | 3A-5A 5V rail fuse | 1 | Basic over-current protection. |
| Output capacitor | 470uF-1000uF low-ESR capacitor | 1 | Helps stabilize the 5V distribution point. |
| USB/data cables | Short data-capable USB cables | as needed | Internal Pi, ESP32, and dongle connections. |
| Speaker | Small 8 ohm speaker, optional but recommended | 0-1 | Alerts and companion output. |
| Standoffs/frame | M2.5 standoffs plus acrylic/printed frame plates | 1 set | Physical assembly. |

### Optional components

| Component | Exact model / type | Qty | Purpose |
|---|---|---:|---|
| CAN adapter | InnoMaker USB to CAN Converter kit | 0-1 | Optional Koala Kan Kommander bench workflow. |
| Powered USB hub | Small powered USB hub | 0-1 | Helpful if USB load is tight. |
| USB mic fallback | CM108-style USB sound adapter | 0-1 | Fallback if DualEye mic mapping is not complete. |

Power path:

```text
USB-C PD/QC charger capable of 12 V
  -> Seloky USB-C PD/QC 12 V trigger board
  -> 5 V buck converter
  -> fused regulated 5 V rail
  -> Raspberry Pi / ESP32-S3 DualEye / USB peripherals
```

Optional CAN path:

```text
Raspberry Pi 3B+ USB host
  -> short internal USB data cable
  -> InnoMaker USB to CAN Converter kit
  -> adapter-side CAN_H / CAN_L / GND / optional SHIELD
  -> isolated CAN bench simulator or owned bench harness
```

Do **not** connect the Seloky 12V output directly to the Raspberry Pi. Do **not** wire CAN_H or CAN_L directly to Raspberry Pi GPIO.

For exact orderable parts and estimated pricing, see:

```text
docs/ORDERABLE_PARTS_LIST.md
```

---

## Boot flow

Normal startup order:

```text
Pre-boot mode selector -> KoalaByte Blue boot splash -> grouped main menu
```

Normal Pi-side boot wrapper:

```bash
bash scripts/koalabyte_blue_boot.sh
```

Preview the splash/menu from a desktop session:

```bash
PYTHONPATH=pi-companion python3 scripts/run_boot_splash.py --windowed --duration 3
PYTHONPATH=pi-companion python3 scripts/run_menu_screen.py --graphical --windowed
```

---

## Pre-boot dongle mode selector

The nRF52840 Dongle can hold only one active firmware profile at a time. The pre-boot selector lets you choose which profile the dongle should use before the normal boot splash and menu start.

Available choices:

```text
1) KoalaByte Blue Lab Mode
   Default production/lab profile. The dongle advertises as KoalaByte Lab.

2) Koala Konnect Mode
   Alternate USB HCI adapter profile for phone/computer host use.
```

Prepare or refresh both cached DFU packages on the Pi:

```bash
bash scripts/prepare_dongle_firmware_cache.sh
PYTHONPATH=pi-companion python3 scripts/run_koala_mode_switcher.py cache-status
```

Interactive selector:

```bash
PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py
```

Direct mode selection:

```bash
PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --mode koalabyte_lab
PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --mode koala_konnect
```

Switch the physical nRF52840 Dongle when it is in DFU bootloader mode:

```bash
NRF_DFU_PORT=/dev/ttyACM0 PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --mode koalabyte_lab
NRF_DFU_PORT=/dev/ttyACM0 PYTHONPATH=pi-companion python3 scripts/run_preboot_mode_select.py --mode koala_konnect
```

If no DFU port is available, the selector records the requested mode in `logs/preboot_mode_selection.json` but does not claim that the physical dongle was switched.

---

## Main menu actions

The grouped menu is driven from `pi-companion/koalablue/menu_catalog.py`. Current groups are:

```text
Bluetooth Tools
CAN Bench Tools
Reports & Reviews
System / Companion
```

### Bluetooth Tools

| Menu item | Command | What it does |
|---|---|---|
| Scan | `scan` | Run a safe BLE inventory scan. |
| Summary | `summary` | Summarize observed BLE devices. |
| Show Devices | `show` | Show the current BLE device table. |
| eucalyptus Status | `eucalyptus status` | Show always-on passive BLE logger status. |
| eucalyptus Start | `eucalyptus start` | Start always-on passive BLE logging. |
| eucalyptus Stop | `eucalyptus stop` | Stop always-on passive BLE logging. |
| eucalyptus Restart | `eucalyptus restart` | Restart always-on passive BLE logging. |
| eucalyptus Upload Status | `eucalyptus upload-status` | Show WiGLE upload readiness/status. |
| Koala Kapture | `koala_kapture` | Capture and archive BLE advertisement metadata. |
| Koala Kry | `koala_kry` | Replay captured metadata offline into the report/XP pipeline. |
| Ear Tag | `ear_tag` | Named lab BLE beacon. |
| KoalaByte Lab | `ear_tag_tx_lab` | Synthetic owned-device BLE advertisement for signal-integrity observation. |
| Gumleaf Gear Check | `koala_bluez_inventory` | Inventory installed BlueZ helpers under KoalaByte themed names. |
| Eucalyptus Bus Scout | `koala_bluez_status` | Collect local adapter, controller, rfkill, and optional D-Bus status. |
| Dropbear Discovery Sweep | `koala_bluez_scan` | Run bounded Bluetooth discovery and save redacted results by default. |
| Billabong HCI Watch | `koala_bluez_monitor` | Run bounded btmon HCI capture and save lab artifacts. |
| Kookaburra Safe Nest Run | `koala_bluez_all_safe` | Run BlueZ inventory, status, and bounded discovery with safe defaults. |
| Urban Poaching | `urban_poaching` | Authorized BLE RSSI lab game. |

### CAN Bench Tools

| Menu item | Command | What it does |
|---|---|---|
| Koala Kan Kommander | `koala_kan_kommander` | InnoMaker USB-to-CAN listen and gated bench-simulator transmit plug-in. |

CAN transmit remains gated. Transmit commands require an isolated bench simulator or owned bench harness plus explicit confirmation flags.

### Reports & Reviews

| Menu item | Command | What it does |
|---|---|---|
| Koala Kry RF Review | `koala_kry_transmit_review` | Write RF bench isolation, authorization, and test-plan manifest; no RF is sent by Koala Kry. |
| Report | `report` | Write a Markdown session report. |
| Authorized BLE Inventory | `authorized_ble_inventory` | Create a lab inventory from passive BLE observations. |
| GATT Readiness Checklist | `gatt_readiness_checklist` | Generate a pre-test checklist for owned-device GATT review. |
| Pairing Security Review | `pairing_security_review` | Review pairing/access-control posture for owned lab devices. |
| Lab Beacon Plan | `lab_beacon_plan` | Create a safe ESP32 demo beacon/peripheral testing plan. |
| Packet Capture Notes | `packet_capture_notes` | Create safe Wireshark/nRF52840 protocol-analysis notes. |
| Defensive Lab Report | `defensive_report` | Generate a defensive lab report template. |

### System / Companion

| Menu item | Command | What it does |
|---|---|---|
| Koala Mode Switcher | `koala_mode_switcher` | Build/package/select KoalaByte Lab or Koala Konnect for the nRF52840 Dongle. |
| KillerKoala Voice | `killerkoala_voice` | Preview event reactions and inquiry vocabulary by XP rank. |
| Buttons | `buttons` | Show/check GPIO front-panel button status. |
| Level / Status | `level/status` | Show XP and rank. |
| Wake killerkoala | `wake killerkoala` | Test wake-word flow. |
| Restricted Placeholder | `restricted_placeholder` | Reserved locked slot; intentionally non-operational. |
| Settings | `settings` | Device and companion settings. |
| Lab | `lab` | Password-gated Authorized Lab Use menu. |
| Shutdown | `shutdown_confirm` | Confirm safe shutdown. |
| Quit | `quit` | Exit the Pi companion UI. |

---

## Outback BlueZ module deck

KoalaByte Blue wraps local BlueZ tooling as themed, bounded automation modules on the Pi companion.

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py status
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py scan --duration 15
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py monitor --duration 20
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py all-safe --duration 15
PYTHONPATH=pi-companion python3 scripts/run_koala_bluez.py gatt-readiness --target AA:BB:CC:DD:EE:FF --owned-device
```

Convenience wrappers:

```bash
bash scripts/run_koala_bluez_manifest.sh
bash scripts/run_koala_bluez_inventory.sh
bash scripts/run_koala_bluez_status.sh
bash scripts/run_koala_bluez_scan.sh --duration 15
bash scripts/run_koala_bluez_monitor.sh --duration 20
bash scripts/run_koala_bluez_all_safe.sh
bash scripts/run_koala_bluez_gatt_readiness.sh --target AA:BB:CC:DD:EE:FF --owned-device
```

The Outback BlueZ deck uses bounded runs and safe defaults. Raw addresses should only be used where you have authorization and a real need for them.

---

## Koala Kan Kommander

Koala Kan Kommander uses the optional InnoMaker USB-to-CAN Converter kit. It supports bounded CAN listen/reporting and gated bench-simulator transmit. Transmit requires both `--bench-simulator` and `--confirm-transmit`.

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py status --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py listen --interface can0 --duration 10
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py report --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py generate-payloads --interface can0 --payload-profile all --base-id 0x600 --sequence-count 8 --tag KOALAKAN
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py transmit --interface can0 --bench-simulator --confirm-transmit --payload-profile heartbeat --base-id 0x600 --sequence-count 3
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py listen-transmit --interface can0 --bench-simulator --confirm-transmit --can-id 0x600 --data "4B 42 01 00" --duration 10
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py transmit-placeholder
```

`transmit-placeholder` remains blocked as a legacy safety artifact. Use `transmit` or `listen-transmit` only on an isolated bench simulator or owned bench harness.

---

## killerkoala companion

The AI companion layer is named **killerkoala**. It is designed as a gruff cyberpunk lab companion for local status reactions, safe workflow narration, and device interaction.

Current XP ranks:

```text
Noob    0-74 XP
Hacker  75-249 XP
Legend  250+ XP
```

Try the voice/status preview:

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py status --xp 100
```

The companion vocabulary is scoped to authorized lab guidance, local diagnostics, status reactions, and defensive workflow narration.

---

## Theme and menu system

Current approved theme:

```text
jungle_jumanji_eucalyptus
```

Theme source folder:

```text
firmware/esp32-dualeye/themes/jungle_jumanji_eucalyptus/
```

Theme/menu guide:

```text
docs/THEME_AND_MENU_SYSTEM.md
```

Pre-boot selector guide:

```text
docs/PREBOOT_MODE_SELECTOR.md
```

### Image assets

The Copilot draft referenced these optional hero image paths:

```text
docs/images/koalabyte-blue-device-poster.png
docs/images/koalabyte-blue-boot-splash.png
```

Those PNG files are not currently tracked in this repository. Add the real device/poster and boot-splash images at those paths before adding visible `<img>` tags to the top of this README; otherwise GitHub will render broken images.

---

## Current production references

```text
production/RevA17-dongle-only/BOM_RevA17_DongleOnly.csv
production/RevA17-dongle-only/PRODUCTION_README_RevA17_DongleOnly.md
production/RevA17-dongle-only/Safety_Test_Record_RevA17.csv
docs/PRODUCTION_FILES.md
docs/FLASHING.md
docs/ORDERABLE_PARTS_LIST.md
docs/THEME_AND_MENU_SYSTEM.md
docs/PREBOOT_MODE_SELECTOR.md
```

---

## Core paths

```text
pi-companion/koalablue/bluez_tools.py
pi-companion/koalablue/killerkoala_vocabulary.py
pi-companion/koalablue/menu_catalog.py
pi-companion/koalablue/koala_mode_switcher.py
pi-companion/koalablue/preboot_mode_selector.py
pi-companion/koalablue/koala_kan_kommander.py
pi-companion/config.default.json
firmware/nrf52840-dongle-ear-tag-tx-lab/src/main.c
firmware/esp32-dualeye/src/main.cpp
firmware/esp32-dualeye/src/boot_animation.cpp
scripts/setup_wifi_first_boot.sh
scripts/setup_system_packages.sh
scripts/setup_esp32_tools.sh
scripts/setup_nrf_tools.sh
scripts/setup_nrf_connect_sdk_toolchain.sh
scripts/setup_local_ncs.sh
scripts/prepare_dongle_firmware_cache.sh
scripts/run_preboot_mode_select.py
scripts/koalabyte_blue_boot.sh
scripts/check_repo_readiness.py
scripts/flash_all_components.sh
```

---

## Safety boundary

KoalaByte Blue is for lawful educational research, defensive testing, owned-device lab work, and authorized Bluetooth/CAN assessment only. Passive capture, local logging, synthetic owned-device lab advertising, Koala Konnect host-adapter use, and Koala Kan Kommander listen/transmit workflows must remain scoped to environments where you have permission.

CAN transmit is for completely isolated bench simulators or owned bench harnesses only and requires explicit transmit confirmation flags.

Keep it clean, keep it scoped, and leave no trace.