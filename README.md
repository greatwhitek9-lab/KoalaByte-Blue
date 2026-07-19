<p align="center">
  <img src="assets/code-signature/koalabyte-code-signature.svg" alt="KoalaByte Blue code signature: neon cyan ASCII koala head" width="760">
</p>

# KoalaByte Blue V2 Heltec Edition

**KoalaByte Blue is a handheld BLE/RF/CAN lab cyberdeck for owned-device testing, defensive review, education, packet review, passive survey work, and isolated bench diagnostics.**

The current hardware profile uses:

- Raspberry Pi 3B+ as the Linux brain, primary Wi-Fi controller, BLE support node, menu host, voice router, report host, and installer.
- Waveshare ESP32-S3 DualEye as the animated face, touchscreen bridge, microphone/voice bridge, internal Wi-Fi node, and internal BLE node.
- Heltec Mesh Node T114 with nRF52840 as the primary BLE node, GNSS node, and LoRa/Meshtastic node.
- One external region-matched LoRa antenna. The Pi, ESP32-S3, and nRF52840 BLE/Wi-Fi paths use their internal antennas.
- An eight-key K1-K8 GPIO board for physical controls, with automatic touch-and-speech-only fallback when the board cannot initialize.
- An optional InnoMaker USB-to-CAN adapter for isolated SocketCAN bench work.
- An optional ELM327-compatible OBD-II adapter for TwoCan read-only vehicle diagnostics.

> **Authorization boundary:** use KoalaByte Blue only on hardware, radios, networks, CAN benches, vehicles, captures, and devices you own or have documented permission to test. The installer does not transmit RF, BLE, or CAN traffic during setup. TwoCan does not clear DTCs, perform ECU coding, run actuator tests, request security access, calculate seed/key responses, inject OEM raw frames, or replay captured vehicle traffic.

## Community

- Discord: https://discord.gg/aYAmEnrDs
- Instagram: https://www.instagram.com/urbanpoacher
- TikTok: https://www.tiktok.com/@urbanpoacher
- Facebook: https://www.facebook.com/share/197SYPvCFm/

---

## Quick install

Flash **Raspberry Pi OS Lite 64-bit** to the Pi first, enable SSH, boot the Pi, and connect the boards with data-capable USB cables.

Put the Heltec T114 into UF2 mode before the recommended full install:

```text
1. Connect the T114 to the Pi with a USB-C data cable.
2. Press RST twice quickly.
3. Confirm that the HT-n5262 UF2 volume appears with lsblk.
```

Download the latest bootstrapper and run the dry check:

```bash
cd ~
rm -f koalabyte-install.sh
curl -fsSL -o koalabyte-install.sh \
  https://raw.githubusercontent.com/greatwhitek9-lab/KoalaByte-Blue/Main/install.sh
chmod +x koalabyte-install.sh
bash koalabyte-install.sh check-only
```

Run the full UF2-first installation after the dry check passes:

```bash
bash koalabyte-install.sh --heltec-uf2-first
```

The bootstrapper clones or updates:

```text
~/KoalaByte-Blue
```

It installs the Pi requirements, validates every menu action, installs or checks the runtime services, flashes the Heltec T114, preserves the existing ESP32-S3 DualEye firmware, validates loading-to-mouth/menu transitions, configures an attached InnoMaker USB2CAN as persistent SocketCAN, checks the K1-K8 fallback, and runs the TwoCan read-only safety gate. Set `FLASH_ESP32=1` only when an explicit DualEye reflash is intended.

Useful direct checks:

```bash
cd ~/KoalaByte-Blue
bash scripts/install_koalabyte_one_shot.sh --check-only
bash scripts/check_deployability.sh
PYTHONPATH=pi-companion python3 scripts/check_menu_actions.py
PYTHONPATH=pi-companion python3 scripts/check_menu_theme_fit.py
PYTHONPATH=pi-companion python3 scripts/check_twocan_read_only.py
bash scripts/koalabyte_doctor.sh --quick
```

---

## Control methods

Every enabled leaf menu action uses the same shared handler path and can be executed through:

- KillerKoala voice commands
- Touchscreen selection
- K1-K8 button-board navigation
- USB or Bluetooth keyboard navigation

### K1-K8 map

```text
K1 -> Main Menu                 -> GPIO5
K2 -> Left / Back               -> GPIO6
K3 -> Enter / Select            -> GPIO13
K4 -> Right / Forward           -> GPIO19
K5 -> Up                        -> GPIO26
K6 -> Down                      -> GPIO21
K7 -> Power On/Off              -> GPIO20 -> safe shutdown request
K8 -> Reset / Reboot            -> GPIO16 -> safe reboot request
```

Keyboard navigation:

```text
Arrow keys or W/A/S/D -> move
Enter                  -> select/save
Backspace or Left      -> return/delete
Escape                 -> cancel
```

Voice syntax:

```text
killerkoala open <menu or submenu label>
killerkoala run <menu item label>
killerkoala run <command key>
```

Examples:

```text
killerkoala open Eucalyptus
killerkoala open Koala Kan Kommander
killerkoala open TwoCan Read-Only Tools
killerkoala run Stored DTC Report
killerkoala run T114 BLE Check
killerkoala run Readiness Monitors
killerkoala run GreatWhite Reef Report
```

### Loading sequence

While a selected action is executing, the ESP32-S3 DualEye displays the
action name and status while the Heltec T114 plays the Koalagotchi action
animation. The shared action clock still advances through seven frames:

```text
<< L >>
<< LO >>
<< LOA >>
<< LOAD >>
<< LOADI >>
<< LOADIN >>
<< LOADING >>
```

### Button-board fallback

When the K1-K8 GPIO stack cannot initialize, the installer continues and writes `touch_speech_only` mode. Touch, speech, and keyboard controls remain available while GPIO buttons are bypassed.

Check or repair the mode with:

```bash
cd ~/KoalaByte-Blue
PYTHONPATH=pi-companion python3 scripts/set_control_mode.py --show
PYTHONPATH=pi-companion python3 scripts/setup_gpio_buttons.py --probe
```

---

# Complete jungle menu reference

The visible terminal and touchscreen interfaces share the same jungle/Jumanji-inspired renderer, carved title treatment, eucalyptus borders, row ordering, text fitting, descriptions, and action handlers.

Command keys are included below for troubleshooting, voice aliases, and development. Rows beginning with `submenu:` open another menu. Rows beginning with `keyboard:` open the protected pop-up keyboard.

## Main Canopy

| # | Menu item | Command key | Function |
|---:|---|---|---|
| 1 | Eucalyptus | `submenu:eucalyptus` | Opens passive BLE logging, GPS, and WiGLE controls. |
| 2 | Koala Kombat Kruisin’ | `submenu:kruisin` | Opens passive Wi-Fi/BLE/GPS survey and mapping tools. |
| 3 | Bluetooth Tools | `submenu:bluetooth` | Opens the custom Bluetooth and wrapped BlueZ tool chest. |
| 4 | Didgeridoo | `submenu:didgeridoo` | Opens T114 BLE, GNSS, Meshtastic, and protected location tools. |
| 5 | CAN Bench Tools | `submenu:can_bench` | Opens Koala Kan Kommander and optional CAN tools. |
| 6 | GreatWhite Reef | `submenu:greatwhite_reef` | Opens TigerShark and Great Wire Shark capture review. |
| 7 | Reports & Reviews | `submenu:reports` | Opens defensive report, inventory, and documentation actions. |
| 8 | System / Companion | `submenu:system` | Opens KillerKoala, XP, firmware, and control status. |
| 9 | Lab | `submenu:lab` | Opens authorized-lab scope and protected helper controls. |
| 10 | Power On/Off | `shutdown_confirm` | Requests safe software shutdown. |
| 11 | Reset / Reboot | `reset_confirm` | Requests safe Raspberry Pi reboot. |
| 12 | Power & Exit | `submenu:power` | Opens shutdown, reboot, and menu-exit controls. |

<details>
<summary><strong>Eucalyptus submenu</strong></summary>

| # | Menu item | Command key |
|---:|---|---|
| 1 | Eucalyptus Prompt Status | `eucalyptus_prompt_status` |
| 2 | Type WiGLE Name | `keyboard:wigle_api_name` |
| 3 | Type WiGLE Key | `keyboard:wigle_api_token` |
| 4 | Eucalyptus GPS ON | `eucalyptus_gps_on` |
| 5 | Eucalyptus GPS OFF | `eucalyptus_gps_off` |
| 6 | Eucalyptus WiGLE Dry-Run ON | `eucalyptus_wigle_dry_run_on` |
| 7 | Eucalyptus WiGLE Dry-Run OFF | `eucalyptus_wigle_dry_run_off` |
| 8 | Eucalyptus WiGLE Upload ON | `eucalyptus_wigle_upload_on` |
| 9 | Eucalyptus WiGLE Upload OFF | `eucalyptus_wigle_upload_off` |
| 10 | Eucalyptus Canopy Status | `eucalyptus status` |
| 11 | Eucalyptus Canopy Start | `eucalyptus start` |
| 12 | Eucalyptus Canopy Stop | `eucalyptus stop` |
| 13 | Eucalyptus Canopy Restart | `eucalyptus restart` |
| 14 | Eucalyptus GPS Trail | `eucalyptus gps-trail` |
| 15 | Eucalyptus Upload Trail | `eucalyptus upload-status` |
| 16 | Eucalyptus WiGLE Upload | `eucalyptus wigle-upload` |
| 17 | Eucalyptus Koalagotchi Mode | `eucalyptus_mode` |
| 18 | Back to Main Canopy | `submenu:main` |

</details>

<details>
<summary><strong>Koala Kombat Kruisin’ submenu</strong></summary>

| # | Menu item | Command key |
|---:|---|---|
| 1 | Kruisin’ Prompt Status | `kruisin_prompt_status` |
| 2 | Type WiGLE Name | `keyboard:wigle_api_name` |
| 3 | Type WiGLE Key | `keyboard:wigle_api_token` |
| 4 | Kruisin’ GPS ON | `kruisin_gps_on` |
| 5 | Kruisin’ GPS OFF | `kruisin_gps_off` |
| 6 | Kruisin’ Nodes ON | `kruisin_nodes_on` |
| 7 | Kruisin’ Nodes OFF | `kruisin_nodes_off` |
| 8 | Kruisin’ Default Ports | `kruisin_default_ports` |
| 9 | Kruisin’ WiGLE Dry-Run ON | `kruisin_wigle_dry_run_on` |
| 10 | Kruisin’ WiGLE Dry-Run OFF | `kruisin_wigle_dry_run_off` |
| 11 | Kruisin’ WiGLE Upload ON | `kruisin_wigle_upload_on` |
| 12 | Kruisin’ WiGLE Upload OFF | `kruisin_wigle_upload_off` |
| 13 | Kruisin’ Status | `kruisin status` |
| 14 | Wi-Fi AP Survey | `kruisin wifi-survey` |
| 15 | BLE Survey | `kruisin ble-survey` |
| 16 | Wi-Fi + BLE Survey | `kruisin survey` |
| 17 | Kruisin’ GPS Status | `kruisin gps-status` |
| 18 | Kruisin’ WiGLE Upload | `kruisin wigle-upload` |
| 19 | Back to Main Canopy | `submenu:main` |

</details>

<details>
<summary><strong>Bluetooth Tools submenu</strong></summary>

| # | Menu item | Command key |
|---:|---|---|
| 1 | Koala Kapture | `submenu:koala_kapture` |
| 2 | Koala Kry | `submenu:koala_kry` |
| 3 | KoalaByte Lab | `ear_tag_tx_lab` |
| 4 | BlueZ Lab Scope Status | `bluez_lab_scope_status` |
| 5 | Type BlueZ Lab Target | `keyboard:bluez_lab_target` |
| 6 | Owned Device Scope ON | `bluez_lab_owned_on` |
| 7 | Owned Device Scope OFF | `bluez_lab_owned_off` |
| 8 | Clear BlueZ Lab Scope | `bluez_lab_scope_clear` |
| 9 | Outback Module Deck | `koala_bluez_manifest` |
| 10 | Gumleaf Gear Check | `koala_bluez_inventory` |
| 11 | Eucalyptus Bus Scout | `koala_bluez_status` |
| 12 | Dropbear Discovery Sweep | `koala_bluez_scan` |
| 13 | Billabong HCI Watch | `koala_bluez_monitor` |
| 14 | Kookaburra Safe Nest Run | `koala_bluez_all_safe` |
| 15 | Joey Target Dossier | `koala_bluez_info` |
| 16 | Treehouse Service Trace | `koala_bluez_services` |
| 17 | Gumnut GATT Gatecheck | `koala_bluez_gatt_readiness` |
| 18 | Outback Radio Ledger | `bluez_outback_radio_ledger` |
| 19 | Classic Track Finder | `bluez_classic_track_finder` |
| 20 | Treehouse RFCOMM Wiremap | `bluez_treehouse_rfcomm_wiremap` |
| 21 | Pouch Link Echo | `bluez_pouch_link_echo` |
| 22 | Gumnut GATT Ghostmap | `bluez_gumnut_gatt_ghostmap` |
| 23 | Platypus BT-Proxy | `bluez_platypus_bt_proxy` |
| 24 | that’s not a knife | `thats_not_a_knife` |
| 25 | AntEater | `anteater` |
| 26 | Urban Poaching | `urban_poaching` |
| 27 | Back to Main Canopy | `submenu:main` |

</details>

<details>
<summary><strong>Koala Kapture submenu</strong></summary>

| # | Menu item | Command key |
|---:|---|---|
| 1 | Kapture Policy Status | `lab_transmit_policy_status` |
| 2 | RF/BLE Mode: Gated Lab | `lab_transmit_rf_ble_gated_lab` |
| 3 | RF/BLE Mode: Listen Only | `lab_transmit_rf_ble_listen_only` |
| 4 | RF/BLE Mode: Disabled | `lab_transmit_rf_ble_disabled` |
| 5 | RF/BLE Lab Confirm ON | `lab_transmit_rf_ble_arm_on` |
| 6 | RF/BLE Lab Confirm OFF | `lab_transmit_rf_ble_arm_off` |
| 7 | Kapture Listen Gate | `koala_kapture_listen_gate` |
| 8 | Kapture Transmit Safety Check | `koala_kapture_transmit_placeholder` |
| 9 | Kapture Transmit Gate | `koala_kapture_transmit_gate` |
| 10 | Kapture Listen + Transmit Gate | `koala_kapture_listen_transmit_gate` |
| 11 | Back to Bluetooth Tools | `submenu:bluetooth` |
| 12 | Back to Main Canopy | `submenu:main` |

Transmit-capable rows remain bounded to an explicitly armed, owned, isolated lab fixture. The installer does not transmit during setup.

</details>

<details>
<summary><strong>Koala Kry submenu</strong></summary>

| # | Menu item | Command key |
|---:|---|---|
| 1 | Kry Prompt Status | `koala_kry_prompt_status` |
| 2 | Kry Policy Status | `lab_transmit_policy_status` |
| 3 | RF/BLE Mode: Gated Lab | `lab_transmit_rf_ble_gated_lab` |
| 4 | RF/BLE Mode: Listen Only | `lab_transmit_rf_ble_listen_only` |
| 5 | RF/BLE Mode: Disabled | `lab_transmit_rf_ble_disabled` |
| 6 | RF/BLE Lab Confirm ON | `lab_transmit_rf_ble_arm_on` |
| 7 | RF/BLE Lab Confirm OFF | `lab_transmit_rf_ble_arm_off` |
| 8 | Kry Listen Gate | `koala_kry_listen_gate` |
| 9 | Kry Transmit Safety Check | `koala_kry_transmit_placeholder` |
| 10 | Kry Transmit Gate | `koala_kry_transmit_gate` |
| 11 | Kry Listen + Transmit Gate | `koala_kry_listen_transmit_gate` |
| 12 | Use Latest Capture | `koala_kry_use_latest_capture` |
| 13 | Speed Live | `koala_kry_speed_live` |
| 14 | Speed Fast | `koala_kry_speed_fast` |
| 15 | Speed Instant | `koala_kry_speed_instant` |
| 16 | Limit 50 Records | `koala_kry_limit_50` |
| 17 | Limit 200 Records | `koala_kry_limit_200` |
| 18 | Replay All Records | `koala_kry_limit_all` |
| 19 | RF Review ON | `koala_kry_rf_review_on` |
| 20 | RF Review OFF | `koala_kry_rf_review_off` |
| 21 | Lab Ack ON | `koala_kry_lab_ack_on` |
| 22 | Owned Device Ack ON | `koala_kry_owned_ack_on` |
| 23 | Clear Kry Draft | `koala_kry_clear_prompt` |
| 24 | Run Koala Kry Replay | `koala_kry_run_replay` |
| 25 | Write RF Bench Review | `koala_kry_run_review` |
| 26 | Back to Bluetooth Tools | `submenu:bluetooth` |
| 27 | Back to Main Canopy | `submenu:main` |

Koala Kry’s saved-capture replay is an offline metadata review path unless a separately gated synthetic lab backend is explicitly armed. It does not replay captured RF traffic over the air.

</details>

<details>
<summary><strong>Didgeridoo submenu</strong></summary>

| # | Menu item | Command key |
|---:|---|---|
| 1 | Heltec Link | `status:t114_link` |
| 2 | Radio/GPS | `status:t114_radio_gps` |
| 3 | T114 BLE Check | `t114_primary_ble_scan` |
| 4 | Lab TX Status | `status:t114_tx` |
| 5 | Sextant | `t114_primary_gnss_fix` |
| 6 | Create Location Password | `keyboard:location_password` |
| 7 | Unlock Current Process | `keyboard:location_unlock_password` |
| 8 | Location Unlock ON | `location_gate_unlock_on` |
| 9 | Location Unlock OFF | `location_gate_unlock_off` |
| 10 | Meshtastic App | `submenu:meshtastic` |
| 11 | Protected Location Gate Status | `location_gate_status` |
| 12 | Protected GNSS Current Fix | `location_gate_gnss_current` |
| 13 | Back to Main Canopy | `submenu:main` |

</details>

<details>
<summary><strong>Meshtastic App submenu</strong></summary>

| # | Menu item | Command key |
|---:|---|---|
| 1 | Meshtastic Profile | `meshtastic_profile` |
| 2 | Meshtastic Compatibility | `meshtastic_compat` |
| 3 | Phone App Pairing | `meshtastic_phone_pairing` |
| 4 | ESP32 Device Link | `meshtastic_esp32_link` |
| 5 | Use Heltec USB Serial | `meshtastic_use_serial` |
| 6 | Use Network TCP | `meshtastic_use_tcp` |
| 7 | Use BLE Link | `meshtastic_use_ble` |
| 8 | Meshtastic Status | `meshtastic_status` |
| 9 | Meshtastic Nodes | `meshtastic_nodes` |
| 10 | Meshtastic GPS Info | `meshtastic_gps` |
| 11 | Meshtastic Listen Gate | `meshtastic_listen` |
| 12 | Send Prompt Status | `meshtastic_send_prompt_status` |
| 13 | Type Mesh Message | `keyboard:meshtastic_send_message` |
| 14 | Type Mesh Destination | `keyboard:meshtastic_send_dest` |
| 15 | Set Test Message | `meshtastic_set_test_message` |
| 16 | Set Check-In Message | `meshtastic_set_checkin_message` |
| 17 | Confirm Send ON | `meshtastic_confirm_on` |
| 18 | Confirm Send OFF | `meshtastic_confirm_off` |
| 19 | Clear Send Draft | `meshtastic_clear_send` |
| 20 | Meshtastic Send Gate | `meshtastic_send` |
| 21 | Back to Didgeridoo | `submenu:didgeridoo` |
| 22 | Back to Main Canopy | `submenu:main` |

</details>

<details>
<summary><strong>CAN Bench Tools submenu</strong></summary>

| # | Menu item | Command key |
|---:|---|---|
| 1 | Koala Kan Kommander | `submenu:koala_kan` |
| 2 | Back to Main Canopy | `submenu:main` |

</details>

<details>
<summary><strong>Koala Kan Kommander submenu</strong></summary>

| # | Menu item | Command key |
|---:|---|---|
| 1 | Run Full Kan Check | `koala_kan_kommander` |
| 2 | Kan Manifest | `koala_kan_manifest` |
| 3 | Detect CAN Interfaces | `koala_kan_inventory` |
| 4 | CAN0 Status | `koala_kan_status` |
| 5 | Listen 10 Seconds | `koala_kan_listen_10s` |
| 6 | Generate Bench Payloads | `koala_kan_generate_payloads` |
| 7 | Write CAN Bench Report | `koala_kan_report` |
| 8 | TwoCan Vehicle Diagnostics | `twocan_vehicle_diagnostics` |
| 9 | TwoCan Read-Only Tools | `submenu:twocan_read_only` |
| 10 | TwoCan Clear Codes Safety Note | `twocan_clear_codes_safety_note` |
| 11 | Lab Transmit Policy Status | `lab_transmit_policy_status` |
| 12 | CAN Mode: Gated Bench | `lab_transmit_can_gated_bench` |
| 13 | CAN Mode: Listen Only | `lab_transmit_can_listen_only` |
| 14 | CAN Mode: Disabled | `lab_transmit_can_disabled` |
| 15 | Bench Simulator Confirm ON | `lab_transmit_bench_arm_on` |
| 16 | Bench Simulator Confirm OFF | `lab_transmit_bench_arm_off` |
| 17 | Transmit Safety Check | `koala_kan_transmit_placeholder` |
| 18 | Bench Transmit Gate | `koala_kan_transmit_gate` |
| 19 | Listen + Bench Transmit Gate | `koala_kan_listen_transmit_gate` |
| 20 | Back to CAN Bench Tools | `submenu:can_bench` |
| 21 | Back to Main Canopy | `submenu:main` |

The InnoMaker adapter is optional. Bench transmit rows are limited to synthetic 11-bit lab IDs on an isolated simulator or harness and require explicit mode and confirmation gates.

</details>

<details>
<summary><strong>TwoCan Read-Only Tools submenu</strong></summary>

| # | Menu item | Command key |
|---:|---|---|
| 1 | Run Full Read-Only Scan | `twocan_full_read_only_report` |
| 2 | Adapter Identity | `twocan_adapter_identity` |
| 3 | Vehicle VIN and Calibration | `twocan_vehicle_identity` |
| 4 | Stored DTC Report | `twocan_stored_dtcs` |
| 5 | Pending DTC Report | `twocan_pending_dtcs` |
| 6 | Permanent DTC Report | `twocan_permanent_dtcs` |
| 7 | Freeze-Frame Snapshot | `twocan_freeze_frame` |
| 8 | Readiness Monitors | `twocan_readiness_monitors` |
| 9 | Live PID Snapshot | `twocan_live_pid_snapshot` |
| 10 | Live PID Log 30 Seconds | `twocan_live_pid_log_30s` |
| 11 | Offline CAN Capture Review | `twocan_offline_capture_review` |
| 12 | Repair Verification Checklist | `twocan_repair_verification_checklist` |
| 13 | TwoCan Clear Codes Safety Note | `twocan_clear_codes_safety_note` |
| 14 | Back to Koala Kan Kommander | `submenu:koala_kan` |
| 15 | Back to Main Canopy | `submenu:main` |

Live diagnostic actions use an ELM327-compatible OBD-II adapter and explicitly allowlisted read-only services. Offline capture review parses local JSON, candump, log, or text files and never transmits or replays the capture.

Artifacts are written under:

```text
logs/twocan_vehicle_diagnostics/
```

</details>

<details>
<summary><strong>GreatWhite Reef submenu</strong></summary>

| # | Menu item | Command key |
|---:|---|---|
| 1 | Reef Status | `greatwhite_reef_status` |
| 2 | TigerShark Install Check | `greatwhite_tigershark_check` |
| 3 | TigerShark Interfaces | `greatwhite_tigershark_interfaces` |
| 4 | TigerShark PCAP Folder | `greatwhite_tigershark_pcap_folder` |
| 5 | TigerShark Read Latest PCAP | `greatwhite_tigershark_read_latest` |
| 6+ | PCAP N: `<filename>` | `greatwhite_pcap_read:<filename>` |
| Next | Great Wire Shark Launch Notes | `great_wire_shark_launch_notes` |
| Next | Great Wire Shark Folder Notes | `great_wire_shark_folder_notes` |
| Next | GreatWhite Reef Report | `greatwhite_reef_report` |
| Last | Back to Main Canopy | `submenu:main` |

The `PCAP N` rows are generated dynamically from saved `.pcap` and `.pcapng` files. GreatWhite Reef stores and synchronizes captures under:

```text
logs/greatwhite_reef/pcaps/
```

</details>

<details>
<summary><strong>Reports & Reviews submenu</strong></summary>

| # | Menu item | Command key |
|---:|---|---|
| 1 | Koala Kry RF Review | `koala_kry_run_review` |
| 2 | Boomerang | `boomerang` |
| 3 | Authorized BLE Inventory | `authorized_ble_inventory` |
| 4 | GATT Readiness Checklist | `gatt_readiness_checklist` |
| 5 | Pairing Security Review | `pairing_security_review` |
| 6 | Lab Beacon Plan | `lab_beacon_plan` |
| 7 | Packet Capture Notes | `packet_capture_notes` |
| 8 | Defensive Lab Report | `defensive_lab_report` |
| 9 | Back to Main Canopy | `submenu:main` |

</details>

<details>
<summary><strong>System / Companion submenu</strong></summary>

| # | Menu item | Command key |
|---:|---|---|
| 1 | Prompt State Status | `prompt_state_status` |
| 2 | Companion Status | `companion_status` |
| 3 | KillerKoala Voice | `killerkoala_voice` |
| 4 | KillerKoala Hybrid | `killerkoala_hybrid` |
| 5 | XP Status | `xp_status` |
| 6 | Button Map | `button_map` |
| 7 | Firmware Version | `firmware_version` |
| 8 | Back to Main Canopy | `submenu:main` |

</details>

<details>
<summary><strong>Lab submenu</strong></summary>

| # | Menu item | Command key |
|---:|---|---|
| 1 | BlueZ Lab Scope Status | `bluez_lab_scope_status` |
| 2 | Type BlueZ Lab Target | `keyboard:bluez_lab_target` |
| 3 | Owned Device Scope ON | `bluez_lab_owned_on` |
| 4 | Owned Device Scope OFF | `bluez_lab_owned_off` |
| 5 | Clear BlueZ Lab Scope | `bluez_lab_scope_clear` |
| 6 | RF/BLE Mode: Gated Lab | `lab_transmit_rf_ble_gated_lab` |
| 7 | RF/BLE Mode: Listen Only | `lab_transmit_rf_ble_listen_only` |
| 8 | RF/BLE Mode: Disabled | `lab_transmit_rf_ble_disabled` |
| 9 | RF/BLE Lab Confirm ON | `lab_transmit_rf_ble_arm_on` |
| 10 | RF/BLE Lab Confirm OFF | `lab_transmit_rf_ble_arm_off` |
| 11 | RF/BLE Passive Only | `lab_transmit_rf_ble_passive_only` |
| 12 | RF/BLE Install Disabled | `lab_transmit_rf_ble_disabled_install` |
| 13 | Joey Target Dossier | `koala_bluez_info` |
| 14 | Treehouse Service Trace | `koala_bluez_services` |
| 15 | Gumnut GATT Gatecheck | `koala_bluez_gatt_readiness` |
| 16 | Outback Radio Ledger | `bluez_outback_radio_ledger` |
| 17 | Classic Track Finder | `bluez_classic_track_finder` |
| 18 | Treehouse RFCOMM Wiremap | `bluez_treehouse_rfcomm_wiremap` |
| 19 | Pouch Link Echo | `bluez_pouch_link_echo` |
| 20 | Gumnut GATT Ghostmap | `bluez_gumnut_gatt_ghostmap` |
| 21 | Platypus BT-Proxy | `bluez_platypus_bt_proxy` |
| 22 | Create Location Password | `keyboard:location_password` |
| 23 | Unlock Current Process | `keyboard:location_unlock_password` |
| 24 | Location Unlock ON | `location_gate_unlock_on` |
| 25 | Location Unlock OFF | `location_gate_unlock_off` |
| 26 | Protected Location Gate Status | `location_gate_status` |
| 27 | Back to Main Canopy | `submenu:main` |

</details>

<details>
<summary><strong>Power & Exit submenu</strong></summary>

| # | Menu item | Command key |
|---:|---|---|
| 1 | Power On/Off | `shutdown_confirm` |
| 2 | Reset / Reboot | `reset_confirm` |
| 3 | Quit Menu | `quit` |
| 4 | Back to Main Canopy | `submenu:main` |

</details>

---

## Menu validation and generated manifests

The repository verifies that every enabled leaf action has an executable handler, every submenu target exists, voice labels resolve, text stays inside the jungle borders, and duplicate command routes are intentional.

```bash
cd ~/KoalaByte-Blue
PYTHONPATH=pi-companion python3 scripts/check_menu_actions.py
PYTHONPATH=pi-companion python3 scripts/check_menu_theme_fit.py
PYTHONPATH=pi-companion python3 scripts/check_menu_display_sync.py
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_loading_face.py
PYTHONPATH=pi-companion python3 scripts/check_twocan_read_only.py
```

Important artifacts:

```text
logs/menu_actions/menu_action_manifest.json
logs/menu_actions/menu_action_status.json
logs/menu_actions/menu_theme_fit_status.json
logs/menu_sync/current_menu_state.json
logs/killerkoala_face/loading_face_readiness.json
logs/twocan_vehicle_diagnostics/twocan_read_only_readiness.json
logs/one_shot/full_runtime_dependencies.json
```

---

## One-shot installer coverage

The one-shot installer:

- clones or updates the current `Main` branch;
- prepares the Python virtual environment and installs `pi-companion/requirements.txt`;
- installs `obd>=0.7.3` for TwoCan read-only actions;
- validates the complete menu catalog and all input methods;
- validates touch-and-speech-only GPIO fallback;
- validates the KillerKoala loading-face sequence;
- validates the TwoCan read-only allowlist and no-replay capture parser;
- prepares and flashes the Heltec combined-safe UF2 profile;
- preserves the existing ESP32-S3 DualEye firmware by default; an explicit reflash requires `FLASH_ESP32=1`;
- checks face, mouth, menu, and voice bridges;
- installs stable udev names and boot services where available;
- records the owned-lab transmit policy;
- keeps the optional InnoMaker CAN path non-fatal unless strict mode is enabled;
- preserves InnoMaker factory firmware, configures native SocketCAN, and installs a repeatable boot/hot-plug service when the adapter is detected;
- runs KoalaByte Doctor and deployability checks.

Status files include:

```text
logs/one_shot_install_status.json
logs/one_shot/full_runtime_dependencies.json
logs/one_shot/lab_transmit_policy.json
logs/control/control_mode.json
logs/gpio_buttons/gpio_button_status.json
logs/can/innomaker_optional_status.json
logs/twocan_vehicle_diagnostics/twocan_read_only_readiness.json
logs/doctor/koalabyte_doctor_status.json
```

---

## Antenna routing

```text
Heltec T114 LoRa connector  -> one external, region-matched LoRa antenna
Heltec T114 / nRF52840 BLE  -> onboard internal BLE antenna
ESP32-S3 DualEye Wi-Fi/BLE  -> onboard internal 2.4 GHz antenna
Raspberry Pi 3B+ Wi-Fi/BLE  -> built-in internal antenna
```

Do not connect a 2.4 GHz antenna to the LoRa path or a LoRa antenna to a 2.4 GHz path.

---

## Protected location gate

Location-protected actions use a local password hash stored at:

```text
logs/security/location_password.json
```

Set and unlock it from the menu:

```text
Didgeridoo -> Create Location Password -> enter password -> Save
Didgeridoo -> Unlock Current Process -> enter password -> Save
```

Or from SSH:

```bash
cd ~/KoalaByte-Blue
PYTHONPATH=pi-companion python3 scripts/run_location_password_gate.py setup
PYTHONPATH=pi-companion python3 scripts/run_location_password_gate.py status
PYTHONPATH=pi-companion python3 scripts/run_location_password_gate.py unlock
```

---

## TwoCan CLI

The graphical menu is the normal path, but the same read-only actions can be run from SSH:

```bash
cd ~/KoalaByte-Blue
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py adapter
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py identity
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py stored-dtcs
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py pending-dtcs
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py permanent-dtcs
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py freeze-frame
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py readiness
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py live-snapshot
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py live-log --duration 30 --interval 1
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py capture-review --capture /path/to/saved-capture.log
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py repair-checklist
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py full
```

Select a specific ELM327 adapter when needed:

```bash
KOALABYTE_OBD_PORT=/dev/ttyUSB0 \
PYTHONPATH=pi-companion python3 scripts/run_twocan_read_only.py stored-dtcs
```

---

## Safety boundary

KoalaByte Blue is built for owned-device labs, defensive review, education, passive surveying, local packet analysis, and isolated bench testing.

Do not use it against public networks, other people’s Bluetooth devices, unauthorized Meshtastic nodes, live production CAN systems, industrial controllers, road vehicles you are not explicitly authorized to diagnose, or any target outside your documented scope.

TwoCan intentionally excludes:

- DTC clearing or reset service 04
- ECU coding, adaptation, or programming
- actuator and output tests
- UDS security access
- seed/key workflows
- OEM-specific raw-frame injection
- captured CAN traffic replay
- synthetic ECU or UDS security simulators

For any justified reset or manufacturer-specific procedure after a documented repair, use a dedicated commercial or manufacturer-approved diagnostic tool.
