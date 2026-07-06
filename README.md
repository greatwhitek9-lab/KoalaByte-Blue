<p align="center">
  <img src="assets/code-signature/koalabyte-code-signature.svg" alt="KoalaByte Blue code signature: neon cyan ASCII koala head" width="760">
</p>

# KoalaByte Blue V2 Heltec Edition - Lab Transmit Enabled

**KoalaByte Blue is a Handheld BLE/RF/CAN lab instrument with full transmission and capture capabilities for authorized owned-device research, vehicle diagnostics, and firmware analysis.**

**IMPORTANT: This version has RF/BLE/CAN transmission ENABLED for lab environments only. Use only on owned devices and authorized test vehicles with proper documentation and written permission.**

## Lab Transmission Features (RevA25+)

✅ **RF/BLE Signal Transmission** - Capture and replay Bluetooth/RF signals from owned devices  
✅ **Vehicle Diagnostics** - OBD-II and CAN bus access for owned vehicles  
✅ **Code Clearing** - DTC (Diagnostic Trouble Code) reset on authorized vehicles  
✅ **Vehicle Code Alterations** - Tuning and ECU modifications with explicit confirmation  
✅ **CAN Bus Monitoring** - Full bidirectional CAN communication logging and transmission  
✅ **Captured Traffic Replay** - Replay previously captured network/RF frames  

## Safety & Legal

KoalaByte Blue is for:
- ✅ Owned-device labs and authorized testing
- ✅ Defensive security research on your own hardware
- ✅ Vehicle diagnostics on vehicles you own
- ✅ Educational purposes with proper supervision
- ❌ NOT for unauthorized access, interference, or illegal use

Do not use on systems, vehicles, radios, networks, or devices you do not own or do not have documented written permission to test.

## Community

Join the KoalaByte Blue Discord for build help, firmware updates, and project discussion: https://discord.gg/aYAmEnrDs

Follow Urban Poacher:

- Instagram: https://www.instagram.com/urbanpoacher?igsh=OHo0aXI1eXZid29u&utm_source=qr
- TikTok: https://www.tiktok.com/@urbanpoacher?_r=1&_t=ZP-97oAxnjUNDT
- Facebook: https://www.facebook.com/share/197SYPvCFm/?mibextid=wwXIfr

---

## Quick build profile

| Part | Role |
|---|---|
| Raspberry Pi 3B+ | Main Linux brain, installer, menus, logs, reports, local services, voice routing, main Wi-Fi controller, GreatWhite Reef PCAP review, readiness checks, and lab transmission control. |
| Waveshare ESP32-S3 DualEye 1.28in board | Animated eyes, touch bridge, mic/voice bridge path, secondary Wi-Fi survey node, BLE support node, and visual personality. |
| Heltec Mesh Node T114 / nRF52840 | Primary active BLE/RF lab transmit/receive node with GNSS and LoRa/Meshtastic path. Full transmission capabilities enabled for lab use. |
| 8 independent key button module | Replaces the old six loose 4-pin tactile buttons. K1-K6 are menu controls, K7 Power On/Off requests shutdown, and K8 Reset / Reboot requests reboot. |
| USB power bank / regulated USB supply | Production power source. No loose 18650/raw battery wiring is required. |
| InnoMaker USB-to-CAN kit | Enabled for active CAN bus communication, vehicle diagnostics, code clearing, and bidirectional monitoring. |

No custom PCB is required for this profile.

---

## Current radio roles

```text
Heltec T114 / nRF52840 -> primary active BLE/RF transmit/receive node, GNSS node, LoRa/Meshtastic node; no Wi-Fi
Raspberry Pi 3B+       -> main Wi-Fi controller, BLE support/fallback node, PCAP review host, and lab transmission orchestrator
ESP32-S3 DualEye       -> secondary Wi-Fi survey node, BLE support node, touch bridge, and face/eye UI
```

---

## What the current `Main` branch includes (Lab Transmit Edition)

| Feature | What it does |
|---|---|
| One-shot installer | Runs the Pi, ESP32-S3, Heltec T114, menu, service, and readiness setup from one command. |
| Lab transmission enabled | RF/BLE transmission, CAN communication, vehicle diagnostics, and code operations fully enabled. |
| Active BLE transmit/receive | Heltec T114 configured for bidirectional RF/BLE communication for owned lab devices. |
| Vehicle diagnostics support | Full OBD-II access, DTC clearing, and vehicle code alterations with explicit confirmation. |
| CAN bus full access | Active transmit/receive on CAN interfaces, not limited to listen-only mode. |
| Wrapped jungle UI boot | Starts in the full jungle/eucalyptus graphical interface by default, not terminal mode. |
| 8-key front panel | Supports K1-K8 GPIO input, including K7 Power On/Off and K8 Reset / Reboot. |
| KoalaByte Doctor | Runs quick/full diagnostics and writes `logs/doctor/koalabyte_doctor_status.json`. |
| Stable udev names | Adds `/dev/koalabyte-*` aliases for easier board discovery. |
| Heltec T114 HT-n5262 flash support | Supports the manual double-RST UF2 bootloader volume named `HT-n5262`. |
| ESP32-S3 DualEye touch | Includes a Waveshare CST816x I2C touch backend and Pi touch menu bridge. |
| Cleaned jungle menu | Keeps branded tools, wrapped BlueZ tools, Koala Kan Kommander, GreatWhite Reef, pop-up keyboard input, and the Lab submenu. |
| Koala Kry Lab Transmit | RF/BLE signal capture and replay with real transmission enabled for owned devices. |
| Koala Kan Lab Transmit | Active CAN transmission for vehicle diagnostics, monitoring, and code operations. |
| GreatWhite Reef | Adds TigerShark (`tshark`) and Great Wire Shark (`wireshark`) PCAP/PCAPNG review. |
| GreatWhite selectable PCAPs | Syncs `.pcap`/`.pcapng` files into `logs/greatwhite_reef/pcaps/`, then exposes selectable `PCAP N: filename` menu rows. |
| Pop-up text input | Opens only from actual text-input rows for WiGLE name/key, protected local lock/unlock, BlueZ lab target, and Meshtastic message/destination text. |
| KillerKoala companion | Uses fast local phrase responses by default with optional TinyLlama/Ollama banter. |

Fast repo check:

```bash
bash scripts/install_koalabyte_one_shot.sh --check-only
```

---

## Hardware needed

### Required

```text
Raspberry Pi 3B+
128 GB microSD card recommended, 32 GB minimum for basic testing
Regulated USB power bank or USB power supply
Waveshare ESP32-S3 DualEye 1.28in board
Heltec Mesh Node T114
USB data cable for ESP32-S3 DualEye
USB-C data cable for Heltec T114
8 independent key button module with VCC, GND, and K1-K8 header
40-pin GPIO extender/cable or direct GPIO wiring
Correct antennas for the boards you use
```

### Optional

```text
InnoMaker USB-to-CAN kit (highly recommended for vehicle diagnostics)
USB data cable for InnoMaker CAN kit
External case-mounted antenna pigtails
8 ohm speaker path for the ESP32-S3 if your board supports it
Small fan for the Raspberry Pi case
Powered USB hub if USB devices disconnect or the Pi shows undervoltage
USB or Bluetooth keyboard for faster text entry
```

### Software tools installed by the Pi helper

```text
TigerShark -> tshark
Great Wire Shark -> wireshark
PlatformIO -> pio, for ESP32-S3 firmware flashing
nRF/Zephyr tools -> west, when Heltec T114 build/flash is enabled
TwoCan/ELM327 tools for vehicle diagnostics
```

Power rule: use a regulated USB power bank or USB supply. Do not feed raw battery voltage into the Pi, ESP32-S3, Heltec T114, button wiring, CAN wiring, or antenna hardware.

---

## Installation

### Fresh Raspberry Pi 3B+ install: Pi OS Lite, no desktop

**Do not flash KoalaByte directly to the SD card.** First flash Raspberry Pi OS Lite, boot the Pi, then run the KoalaByte installer.

#### 1. Flash Raspberry Pi OS Lite to the microSD

Use Raspberry Pi Imager on your computer:

```text
Raspberry Pi Device: Raspberry Pi 3
Operating System: Raspberry Pi OS Lite, 64-bit recommended
Storage: your microSD card
```

#### 2. SSH into the Pi and update

```bash
ssh <your-user>@koalabyte-blue.local
sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

#### 3. Plug in the KoalaByte boards

Use data-capable USB cables for all boards.

#### 4. Put the Heltec T114 into UF2 mode

```text
1. Connect the Heltec T114 to the Pi with a USB-C data cable
2. Press the T114 RST key twice quickly
3. Wait for the mounted UF2 bootloader volume named HT-n5262
```

#### 5. Download and run the installer

```bash
curl -fsSL -o koalabyte-install.sh https://raw.githubusercontent.com/greatwhitek9-lab/KoalaByte-Blue/main/install.sh
bash koalabyte-install.sh --check-only
bash koalabyte-install.sh --heltec-uf2-first
```

#### 6. Reboot and start KoalaByte Blue

```bash
sudo reboot
```

The systemd service should start the wrapped KoalaByte Blue jungle UI automatically.

---

## Lab Transmission Safety Confirmation

Before using lab transmission features, ensure:

1. ✅ **Device Ownership** - You own or have written permission for all target devices
2. ✅ **Lab Environment** - Operations are in a controlled lab, not on public/commercial networks
3. ✅ **Documentation** - Maintain audit logs and documentation of all operations
4. ✅ **Written Authorization** - Have written authorization from device owners for vehicle diagnostics/modifications
5. ✅ **Legal Compliance** - Ensure compliance with all applicable laws and regulations

### Enabling Lab Transmission Features

Lab transmission is controlled via menu options and command-line flags:

**RF/BLE Transmission:**
```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kry.py --lab-setting --owned-device --request-rf-transmit
```

**CAN Vehicle Operations:**
```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py transmit --interface can0 --confirm-transmit
```

**Vehicle Diagnostics:**
```bash
PYTHONPATH=pi-companion python3 scripts/run_vehicle_diagnostics.py --lab-setting --owned-device
```

All transmission operations require explicit confirmation flags and generate detailed audit trails in `logs/`.

---

## Button, touchscreen, keyboard, and voice control

```text
K1 -> Main Menu -> GPIO5
K2 -> Move Left / Back -> GPIO6
K3 -> Enter / Select -> GPIO13
K4 -> Move Right / Forward -> GPIO19
K5 -> Up -> GPIO26
K6 -> Down -> GPIO21
K7 -> Power On/Off -> GPIO20 -> safe shutdown request
K8 -> Reset / Reboot -> GPIO16 -> safe reboot request
```

---

## Jungle menu overview

### Main Canopy

| Main item | What it opens |
|---|---|
| Eucalyptus | Passive BLE logger controls, GPS trail builder, WiGLE text input/status/upload, and Koalagotchi mode. |
| Koala Kombat Kruisin | Passive Wi-Fi/BLE/GPS survey mapping, WiGLE text input, and WiGLE upload tools. |
| Bluetooth Tools | Custom BLE tools plus wrapped BlueZ tools with custom KoalaByte names. |
| Didgeridoo | Heltec T114/nRF52840 BLE, GNSS, LoRa/Meshtastic, Meshtastic App, protected lock input, and location helpers. |
| CAN Lab Tools | InnoMaker USB-to-CAN with full vehicle diagnostics, code clearing, and transmission capabilities. |
| GreatWhite Reef | TigerShark and Great Wire Shark PCAP/PCAPNG review, selectable PCAP rows, and packet-analysis reporting. |
| Reports & Reviews | Documentation, review, inventory, and lab report builders. |
| System / Companion | KillerKoala voice, XP/status, buttons, settings, and helper controls. |
| Lab | Protected lab-focused BlueZ shortcuts, saved target scope, and location gate status. |
| Power & Exit | K7 Power On/Off shutdown, K8 Reset / Reboot, and quit controls. |

---

## Antenna routing

```text
Heltec T114 LoRa connector -> region-matched LoRa antenna
Heltec T114 2.4 GHz connector -> 2.4 GHz antenna if your T114 board exposes one
ESP32-S3 DualEye 2.4 GHz connector -> ESP32-S3 Wi-Fi/BLE antenna if your board exposes one
Raspberry Pi 3B+ -> built-in Wi-Fi antenna; optional USB Wi-Fi adapter only
InnoMaker CAN -> vehicle OBD-II CAN bus or bench test system
```

Do not swap LoRa and 2.4 GHz antennas. They are different radio paths.

---

## Safety boundary

**This is a lab transmission-enabled version. Transmission is ACTIVE for owned devices in authorized lab settings.**

KoalaByte Blue is for:
- ✅ Owned-device labs and authorized testing environments
- ✅ Defensive security research on your own hardware
- ✅ Vehicle diagnostics on vehicles you own with written permission
- ✅ Educational purposes with proper supervision and documentation
- ❌ NOT for unauthorized access, interference, or illegal activities

Do not use KoalaByte Blue against:
- ❌ Vehicles you do not own
- ❌ Networks without authorization
- ❌ Public or commercial systems
- ❌ Devices without written permission

**All transmission operations maintain audit trails and require explicit confirmation flags.**
