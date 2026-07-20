<p align="center">
  <img src="assets/code-signature/koalabyte-code-signature.svg" alt="KoalaByte Blue code signature" width="760">
</p>

# KoalaByte Blue

KoalaByte Blue is a Raspberry Pi 3B+-coordinated cyberpet and authorized-device lab platform. One canonical command now builds, flashes, installs, and verifies the current system:

```bash
bash one-shot-install.sh
```

The deployment includes:

- **Heltec T114 / HT-n5262** — primary BLE controller, GNSS source, guarded LoRa/Meshtastic hooks, articulated KillerKoala mouth, and Koalagotchi action/alarm display.
- **Waveshare ESP32-S3 DualEye** — wake word, saved local responses, microphone, local speaker, menu/eye display, Pi Wi-Fi/serial node, and guarded BLE fallback.
- **Raspberry Pi OS Lite** — main brain, K1-K8 menu controller, action executor, Heltec BLE node, Wi-Fi host, TinyLlama AI, optional web research, Australian speech, Mopidy music player, logs, services, and diagnostics.
- **K1-K8 front-panel board** — physical menu navigation, protected shutdown, and protected reboot.

Use the project only with systems, networks, radios, captures, vehicles, and test benches you own or are authorized to assess.

## Hardware ownership

### Heltec T114

The T114 is the primary embedded radio/display controller:

- Primary BLE controller and passive BLE observer.
- Primary GNSS/NMEA source.
- Guarded SX1262 LoRa/Meshtastic integration. Direct LoRa driving remains disabled until the exact pin map, region, antenna path, and recovery procedure are physically validated.
- Six-second KillerKoala boot image.
- Smooth articulated mouth during idle and speech.
- Koalagotchi during menu-action execution.
- Alarmed Koalagotchi with synchronized cyber-purple/cyber-green flashing during errors.
- Software request for entry into the HT-n5262 UF2 bootloader after the new firmware is installed.

### Waveshare ESP32-S3 DualEye

The ESP32-S3 owns the local front-end experience:

- Wake phrases: `Killer Koala` and `Hey Killer Koala`.
- Ten-second active voice session, refreshed by accepted speech and trusted K1-K8 events.
- Saved local greetings, acknowledgements, status, help, banter, error, and generated menu responses.
- Automatic Pi/TinyLlama escalation when the Waveshare vocabulary does not match.
- Local microphone capture and local saved-response audio.
- Animated cyberpunk koala eyes, eyebrows, fur, menu status, action names, results, and speech expressions.
- Wi-Fi/serial command and telemetry node for the Pi.
- BLE standby by default. If Pi BlueZ is unavailable, the Pi explicitly elects the ESP32 as the guarded Heltec BLE fallback node. A persistent crash guard prevents repeated BLE-controller boot loops.

### Raspberry Pi

The Pi is the project’s main brain:

- Executes all menu and voice actions.
- Owns headless K1-K8 navigation and synchronized display state.
- Preferred Heltec BLE companion node through BlueZ.
- Coordinates fallback to ESP32 BLE when the Pi Bluetooth adapter is unavailable.
- Runs local `killerkoala-tinyllama:latest` through Ollama.
- Performs web research for current or precision-dependent questions when internet access is available.
- Maintains short conversational context and the gruff cyberpunk Australian KillerKoala persona.
- Uses the male Australian `en-AU-WilliamNeural` TTS backend while the spoken identity remains **KillerKoala**.
- Runs Mopidy for local music, internet-radio presets, and optional streaming extensions.
- Pauses/ducks music around KillerKoala speech.
- Owns the universal error lifecycle, service management, logs, diagnostics, and reports.

## Complete one-shot deployment

### Clean Raspberry Pi

Connect the ESP32-S3 and T114 to the Pi, then run:

```bash
curl -fsSL -o /tmp/koalabyte-install.sh \
  https://raw.githubusercontent.com/greatwhitek9-lab/KoalaByte-Blue/Main/install.sh
bash /tmp/koalabyte-install.sh
```

`install.sh` installs Git when necessary, clones or fast-forwards `Main`, and invokes `one-shot-install.sh`.

### Existing checkout

```bash
cd ~/KoalaByte-Blue
git checkout Main
git pull --ff-only origin Main
KOALABYTE_SERVICE_USER="$(whoami)" bash one-shot-install.sh
```

### Validate without modifying hardware

```bash
cd ~/KoalaByte-Blue
KOALABYTE_SERVICE_USER="$(whoami)" \
INSTALL_INNOMAKER_CAN=0 \
bash one-shot-install.sh --check-only
```

### Deployment options

```bash
bash one-shot-install.sh --skip-packages
bash one-shot-install.sh --skip-audio
bash one-shot-install.sh --skip-can
bash one-shot-install.sh --skip-ai
bash one-shot-install.sh --skip-music
bash one-shot-install.sh --skip-firmware
bash one-shot-install.sh --firmware-build-only
bash one-shot-install.sh --use-existing-firmware-bundle
```

The default deployment is strict and requires both peripherals. `--skip-firmware` is the explicit Pi-only maintenance mode.

## One-shot sequence

The canonical installer performs this transaction:

1. Validate shell, Python, menu, AI, music, BLE, display, error, and deployment source contracts.
2. Install Raspberry Pi packages, Python environment, hardware groups, udev rules, optional SocketCAN support, and audio prerequisites.
3. Stop services that own ESP32/T114 serial ports.
4. Discover both peripherals and refuse a complete deployment if either is missing.
5. Install/update PlatformIO and the nRF Connect SDK/Zephyr toolchain when required.
6. Build the current ESP32-S3 source and T114 source from the checked-out commit.
7. Package `releases/koalabyte-blue-current/` with a manifest and SHA-256 checksums.
8. Validate the complete ESP32 image set and T114 UF2 vector/family/application offset.
9. Request T114 UF2 bootloader mode, mount the `HT-n5262` volume, copy the current UF2, and wait for the runtime USB alias.
10. Probe each ESP32 serial candidate with an ESP32-S3 chip-ID command before any destructive write.
11. Flash the ESP32 bootloader, partition table, OTA data, application, and speech-model image.
12. Verify ESP32 `node_status` and rediscover both peripherals.
13. Install TinyLlama, Mopidy, restricted power controls, menu, BLE, voice, display, and diagnostic services.
14. Run K1-K8, AI, music, BLE failover, error lifecycle, display sync, dependency, and hardware checks.
15. Enable/restart services and write final status reports.

The InnoMaker/SocketCAN adapter remains on stock firmware. The installer does not transmit CAN frames.

### First T114 upgrade

The newly built T114 firmware supports software entry into UF2 mode. If the currently installed older firmware does not, the same installer pauses and asks for one physical double-tap of the T114 reset button. Leave the installer running; it continues when the `HT-n5262` volume appears.

## Firmware bundle

The generated bundle is:

```text
releases/koalabyte-blue-current/
├── manifest.json
├── SHA256SUMS.txt
├── esp32/
│   ├── bootloader.bin       @ 0x00000000
│   ├── partitions.bin       @ 0x00008000
│   ├── boot_app0.bin        @ 0x0000e000
│   ├── firmware.bin         @ 0x00010000
│   └── srmodels.bin         @ 0x00cb0000
└── t114/
    ├── koalabyte-t114-current.uf2
    └── vector-validation.txt
```

T114 deployment metadata:

```text
UF2 volume label: HT-n5262
UF2 family:       0x239a0071
Application:      0x00026000
```

## K1-K8 button board

Use **3.3 V only**. The Pi internal pull-ups are enabled: idle is HIGH and a press pulls the input LOW.

| Key | Function | Command | BCM | Physical pin | Activation |
|---|---|---|---:|---:|---|
| K1 | Main Menu | `main_menu` | 5 | 29 | Press |
| K2 | Left / Back | `move_left` | 6 | 31 | Press |
| K3 | Enter / Select | `select` | 13 | 33 | Press |
| K4 | Right / Forward | `move_right` | 19 | 35 | Press |
| K5 | Up | `up` | 26 | 37 | Press |
| K6 | Down | `down` | 21 | 40 | Press |
| K7 | Safe Shutdown | `power_toggle` | 20 | 38 | Hold 2.5 seconds |
| K8 | Reset / Reboot | `reset` | 16 | 36 | Hold 3.0 seconds |

```text
Board VCC -> Pi 3.3 V, physical pin 1 or 17
Board GND -> Pi GND, physical pin 39 recommended
K1-K8    -> BCM inputs listed above
```

Never connect the button board to Pi 5 V. Short taps on K7 and K8 do not emit destructive commands.

The current BCM20 K7 is a safe shutdown input while Linux is running. For a future wake-from-halt/power-control design, the wiring documentation retains GPIO3/physical pin 5 as an optional hardware redesign path; it is not the current default map.

## Button and menu sequence

1. K1 opens the main menu.
2. K5/K6 move up and down.
3. K2/K4 move left/back and right/forward where supported.
4. K3 enters a submenu or executes the selected leaf action.
5. During execution, the T114 displays Koalagotchi while the DualEye shows the action name and state.
6. Completion displays the result, updates Koalagotchi health/mood/XP, and returns to navigation.
7. Hold K7 for safe shutdown or K8 for reboot.

## Voice and AI sequence

1. Say `Killer Koala` or `Hey Killer Koala`.
2. The ESP32-S3 opens the active voice session and gives a local saved response.
3. Saved local vocabulary stays on the Waveshare and does not consume Pi AI resources.
4. Exact menu/action commands are forwarded to the Pi for execution.
5. An unmatched local phrase automatically arms full speech capture for the Pi.
6. The Pi routes general questions to TinyLlama.
7. Questions requiring fresh or precise facts may receive web-research context when internet access is available.
8. KillerKoala answers conversationally with recent-turn context and a gruff cyberpunk Australian attitude.
9. Pi speech uses the Australian male TTS backend.
10. Tone and subject metadata keep the DualEye and T114 mouth synchronized for the complete response.

## Music player

Mopidy runs on the Pi and exposes its HTTP/MPD interfaces only on localhost by default.

Supported core sources:

- Local files under `/srv/koalabyte-music`.
- Internet-radio presets from `/etc/koalabyte-blue/music.json`.
- Optional Mopidy extensions, including user-configured OpenSubsonic/Navidrome or other supported services.

Playback actions are integrated into the same menu, voice, display, and error lifecycle as other Pi actions. Private streaming credentials must remain outside the repository.

## Action and error lifecycle

### Normal action

1. Pi latches the action state.
2. T114 switches to Koalagotchi action animation.
3. DualEye displays the action name/state.
4. Pi executes the action.
5. Completion/failure updates displays, speech, health, mood, and XP.

### Universal error

1. DualEye keeps alert eyes visible and flashes cyber purple/green behind them.
2. T114 displays alarmed Koalagotchi with the same alternating purple/green background.
3. The alarm remains synchronized for the configured hold period.
4. Pi sends the clear/recovery packet.
5. T114 returns to the articulated mouth.
6. Pi speaks a non-repeating KillerKoala dig about the error.
7. Persistent faults can relatch the alarm until recovery succeeds.

## Normal boot sequence

1. Raspberry Pi network, Bluetooth, udev, and hardware targets become available.
2. Ollama and Mopidy start when installed.
3. `koalabyte-menu.service` initializes K1-K8 and owns live display synchronization.
4. `koalabyte-ble-node-manager.service` establishes Heltec-primary BLE roles.
5. `koalabyte-dualeye-voice-bridge.service` coordinates local vocabulary, Pi execution, TinyLlama, TTS, music ducking, BLE election, and display expressions.
6. `koalabyte-doctor.service` records diagnostics.
7. T114 shows the boot image and transitions to the articulated mouth.
8. DualEye enters the active cyberpunk eye/menu state.

The obsolete `koalabyte-menu-sync.service` is not used. Display synchronization belongs to the headless menu runtime.

## Verification

```bash
cd ~/KoalaByte-Blue

systemctl status ollama.service --no-pager -l
systemctl status mopidy.service --no-pager -l
systemctl status koalabyte-menu.service --no-pager -l
systemctl status koalabyte-ble-node-manager.service --no-pager -l
systemctl status koalabyte-dualeye-voice-bridge.service --no-pager -l

./pi-companion/.venv/bin/python scripts/test_gpio_buttons.py
./pi-companion/.venv/bin/python scripts/pi_hardware_doctor.py \
  --can-interface can0 --gpio-live
```

Primary reports:

```text
logs/one_shot/final_install_status.json
logs/deployment/whole_system_deployment_status.json
logs/deployment/firmware_build_status.json
logs/deployment/t114_flash_status.json
logs/deployment/esp32_flash_status.json
logs/deployment/whole_system_readiness.json
logs/preflight/koalabyte_ports.json
logs/gpio_buttons/gpio_button_status.json
logs/runtime/headless_menu_status.json
logs/killerkoala/ollama_setup_status.json
logs/killerkoala/killerkoala_ai_readiness.json
logs/killerkoala/error_sequence_readiness.json
logs/music_player/mopidy_setup_status.json
logs/ble_nodes/ble_role_election.json
logs/pi_hardware/pi_hardware_doctor.json
```

## Development validation

```bash
python3 scripts/check_whole_system_deployment.py --source-only
PYTHONPATH=pi-companion python3 scripts/check_one_shot_controls.py
PYTHONPATH=pi-companion python3 scripts/check_music_player.py
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_ai.py
PYTHONPATH=pi-companion python3 scripts/check_ble_role_failover.py
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_error_sequence.py
bash scripts/check_deployability.sh
bash one-shot-install.sh --check-only
```

Dedicated GitHub Actions workflows compile the current ESP32-S3 and T114 sources and publish the same types of artifacts consumed by the canonical one-shot deployment.
