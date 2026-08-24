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
- **Raspberry Pi OS Lite or Desktop** — main brain, K1-K8 menu controller, action executor, Heltec BLE node, Wi-Fi host, TinyLlama AI, optional web research, Australian speech, Mopidy music player, logs, services, diagnostics, and optional HDMI eyes/menu/Koalagotchi display.
- **K1-K8 front-panel board** — physical menu navigation, protected shutdown, and protected reboot.

Use the project only with systems, networks, radios, captures, vehicles, and test benches you own or are authorized to assess.

## Major updates since the [July 13, 2026 README baseline](https://github.com/greatwhitek9-lab/KoalaByte-Blue/commit/46f12e353005ef9760b2a8043bb82c8cca6337fb)

The current `Main` branch includes the following completed work added after the last comprehensive README alignment:

| Area | Current implementation |
|---|---|
| Whole-system deployment | `one-shot-install.sh` now builds, packages, flashes, installs, verifies, and reports the ESP32-S3, T114, and Pi runtime as one transaction. |
| Firmware safety and recovery | The installer accepts a T114 in runtime USB or mounted `HT-n5262` recovery mode, proves the ESP32-S3 with a non-writing chip-ID probe before either board is written, checks Raspberry Pi power state, validates schema-2 bundles and compiled identities, and rejects missing, stale, or mismatched flash receipts. |
| Heltec T114 | The source-built combined-safe firmware adds the six-second KillerKoala splash, smooth mood-aware mouth/speech motion, Koalagotchi action and alarm scenes, BLE/GNSS USB JSON, guarded bounded lab-beacon TX, and software UF2 entry. |
| ESP32-S3 DualEye | The local front end now includes the KillerKoala wake session, generated fixed menu/action voice routes, saved rotating Australian responses, microphone capture with pre-roll, expressive cyberpunk koala eyes, action/result display, Pi AI escalation, and guarded BLE fallback. |
| Raspberry Pi companion | The Pi now owns synchronized menu/action execution, TinyLlama responses, optional current-fact web research, Australian male TTS, Lyrebird/Mopidy playback and speech ducking, BLE-role election, bounded logs, diagnostics, and persistent state. |
| Runtime ownership | ESP32 and T114 requests are brokered through their exclusive serial-owning services, preventing menu, scan, status, and maintenance helpers from fighting over a board port. Managed KoalaByte nodes are excluded from owned-device surveys. |
| K1-K8 controls | The one-shot installer now creates and preserves a validated persistent GPIO map, supports per-key BCM overrides, keeps K7/K8 protected hold actions locked, and falls back to touch, keyboard, and speech if GPIO initialization is unavailable. |
| HDMI monitor mode | An optional auto-detected compositor mirrors the eyes, mouth, menu, Koalagotchi, speech, actions, and alarms, and can release the same output to Raspberry Pi OS without stopping voice or command services. |
| Host and CI hardening | Current workflows validate source, menu, protocol, firmware, installer, HDMI, AI, music, BLE failover, GPIO, error lifecycle, and release-package contracts on the same tree. |

## Hardware ownership

### Heltec T114

The T114 is the primary embedded radio/display controller:

- Primary BLE controller and passive BLE observer.
- Primary GNSS/NMEA source.
- Native 240 × 135 right-landscape display profile for the physical USB-left/GPS-right installation.
- Guarded SX1262 LoRa/Meshtastic integration. Direct LoRa driving remains disabled until the exact pin map, region, antenna path, and recovery procedure are physically validated.
- Six-second KillerKoala boot image.
- Smooth articulated, texture-warped mouth during idle and speech, with bite, snarl, smile, happy, and sideways-grin mood states instead of flashing still frames.
- Koalagotchi during menu-action execution.
- Alarmed Koalagotchi with synchronized cyber-purple/cyber-green flashing during errors.
- Software request for entry into the HT-n5262 UF2 bootloader after the new firmware is installed.

### Waveshare ESP32-S3 DualEye

The ESP32-S3 owns the local front-end experience:

- Wake phrases: `Killer Koala` and `Hey Killer Koala`.
- Ten-second active voice session, refreshed by accepted speech and trusted K1-K8 events.
- Saved local greetings, acknowledgements, status, help, banter, error, and generated menu responses.
- Generated fixed menu/action command grammar and voice routes, gated by the active ten-second wake session.
- Automatic Pi/TinyLlama escalation when the Waveshare vocabulary does not match.
- Local microphone capture and local saved-response audio.
- Animated cyberpunk koala eyes, eyebrows, fur, menu status, action names, results, and speech expressions.
- Wi-Fi/serial command and telemetry node for the Pi.
- BLE standby by default. If Pi BlueZ is unavailable, the Pi explicitly elects the ESP32 as the guarded Heltec BLE fallback node. A persistent crash guard prevents repeated BLE-controller boot loops.

### Raspberry Pi

The Pi is the project’s main brain:

- Executes all menu and voice actions.
- Owns headless K1-K8 navigation and synchronized display state.
- Auto-detects an optional HDMI monitor and renders the eyes, animated mouth, menu, Koalagotchi, speech, and alarm state without taking ownership of either board serial port.
- Switches the same HDMI output between KoalaByte Blue and Raspberry Pi OS while voice, K1-K8, ESP32, Heltec, BLE, AI, music, and other commands keep running.
- Runs the Heltec-primary BLE/GNSS node manager over the T114 USB CDC JSON stream.
- Uses Pi BlueZ for secondary enrichment/fallback and coordinates guarded ESP32 BLE election when host Bluetooth is unavailable.
- Runs local `killerkoala-tinyllama:latest` through Ollama.
- Performs web research for current or precision-dependent questions when internet access is available.
- Maintains short conversational context and the gruff cyberpunk Australian KillerKoala persona.
- Uses the male Australian `en-AU-WilliamNeural` TTS backend while the spoken identity remains **KillerKoala**.
- Runs the Pi-owned Lyrebird player through Mopidy for local music, internet-radio presets, and optional streaming extensions.
- Pauses/ducks music around KillerKoala speech.
- Owns the universal error lifecycle, service management, logs, diagnostics, and reports.

## Complete one-shot deployment

### First boot on a new Wi-Fi network with HDMI and keyboard

1. Connect the HDMI monitor and USB keyboard before powering the Pi.
2. Boot Raspberry Pi OS and sign in as the normal user that will run KoalaByte Blue.
3. On Raspberry Pi OS Desktop, use the network icon in the panel to select the new Wi-Fi network.
4. On Raspberry Pi OS Lite, connect without placing the Wi-Fi password in shell history:

```bash
nmcli radio wifi on
nmcli device wifi list
sudo nmcli --ask device wifi connect "YOUR_SSID"
nmcli --fields NAME,DEVICE connection show --active
```

5. Confirm the Pi has an address and can reach GitHub:

```bash
hostname -I
ping -c 3 github.com
```

If `nmcli` is not available on an older image, run `sudo raspi-config`, configure wireless networking under **System Options**, then reboot. Ethernet can be used for the first installation instead. Keep credentials out of the repository and command history.

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
bash one-shot-install.sh --keep-build-tools
```

The default deployment is strict and requires both peripherals. `--skip-firmware` is the explicit Pi-only maintenance mode.

## One-shot sequence

The canonical installer performs this transaction:

1. Validate shell, Python, menu, AI, music, BLE, HDMI, display, error, firmware, and deployment source contracts.
2. Install Raspberry Pi packages, the Python environment, hardware groups, udev rules, optional SocketCAN support, and audio prerequisites.
3. Check supported host, free storage, memory/swap, system clock, and Raspberry Pi under-voltage/throttle state; strict Pi power preflight fails closed if `vcgencmd get_throttled` is unavailable or unparseable.
4. Stop the exclusive services that own the ESP32 and T114 serial ports.
5. Accept the T114 as either runtime USB or an already-mounted `HT-n5262` recovery volume, and prove the selected ESP32-S3 with a non-writing chip-ID probe before the first board write.
6. Install or update PlatformIO and the nRF Connect SDK/Zephyr toolchain when required.
7. Build the current ESP32-S3 and T114 sources from the checked-out commit.
8. Package `releases/koalabyte-blue-current/` as a schema-2 bundle with source commit, exact runtime identities, flash addresses, sizes, and SHA-256 checksums.
9. Validate every ESP32 partition plus the T114 UF2 magic, family, application offset, vector, and embedded firmware/protocol identity markers.
10. Request T114 UF2 mode when needed, copy the verified UF2 to `HT-n5262`, and observe the exact expected runtime identity.
11. Re-probe the preserved ESP32 candidate immediately before flashing its bootloader, partition table, OTA data, application, and speech-model image, then observe its exact expected runtime identity.
12. Reject stale or mismatched T114/ESP32 flash receipts and retain those successful receipts during later manual `--check-only` runs.
13. Install TinyLlama, Mopidy, restricted power controls, K1-K8 auto-mapping, menu, BLE, voice, HDMI, and diagnostic services.
14. Run K1-K8, AI, music, BLE failover, error lifecycle, display sync, HDMI, dependency, runtime ownership, and hardware checks.
15. Enable and restart services, verify live health, clean build-only tools according to policy, and write the final status reports.

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

Current source-build profiles:

| Target | Build profile |
|---|---|
| ESP32-S3 DualEye | PlatformIO environment `esp32s3_dualeye`, 16 MB QIO flash with OPI PSRAM and the dedicated speech-model partition |
| Heltec T114 | App `firmware/t114-combined-safe`, board `heltec_t114_v2/nrf52840/uf2`, nRF Connect SDK `v2.9.0`, Zephyr SDK `0.16.8` |

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

### Automatic K1-K8 mapping

The one-shot installer creates or preserves the validated runtime map at:

```text
logs/gpio_buttons/k1_k8_map.json
```

The production pin table above is used by default. A custom harness can override individual inputs with `KOALABYTE_K1_BCM` through `KOALABYTE_K8_BCM` before installation. For example:

```bash
KOALABYTE_K1_BCM=5 KOALABYTE_K2_BCM=6 \
  KOALABYTE_SERVICE_USER="$(whoami)" bash one-shot-install.sh
```

The generated map is validated for supported, unique 40-pin BCM GPIOs; the physical button wiring must remain at 3.3 V. K7 must remain `power_toggle` with at least a 2.5-second hold, and K8 must remain `reset` with at least a 3-second hold. An invalid or missing map is regenerated or replaced by the locked production-safe defaults.

Check the map and perform a non-interactive GPIO initialization probe:

```bash
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python \
  scripts/setup_gpio_buttons.py --check-only
```

Force regeneration from the defaults plus any per-key overrides with `--auto-map`. If GPIO initialization still fails, installation continues in `touch_speech_only` mode so HDMI/touch, keyboard, and KillerKoala voice controls remain available. Set `STRICT_GPIO_BUTTONS=1` only when a K1-K8 failure must stop deployment.

Never connect the button board to Pi 5 V. Short taps on K7 and K8 do not emit destructive commands.

The current BCM20 K7 is a safe shutdown input while Linux is running. For a future wake-from-halt/power-control design, the wiring documentation retains GPIO3/physical pin 5 as an optional hardware redesign path; it is not the current default map.

## HDMI monitor mode and Raspberry Pi OS switch

The optional `koalabyte-hdmi.service` auto-detects an attached monitor and consumes the same sanitized face/menu/action state as the two embedded displays. It never opens either board serial port. With no monitor attached, it stays idle and KoalaByte keeps its original headless behavior.

| Mode | HDMI output | Voice, K1-K8, ESP32, T114, BLE, AI, music, and actions |
|---|---|---|
| `koalabyte` | Fullscreen synchronized eyes, animated mouth, menu, Koalagotchi, speech, results, and purple/green alarm | Continue running |
| `desktop` | Raspberry Pi OS desktop, or the normal Linux console on Pi OS Lite | Continue running |

Switch or inspect the selected mode:

```bash
cd ~/KoalaByte-Blue
./pi-companion/.venv/bin/python scripts/set_hdmi_display_mode.py desktop
./pi-companion/.venv/bin/python scripts/set_hdmi_display_mode.py koalabyte
./pi-companion/.venv/bin/python scripts/set_hdmi_display_mode.py toggle
./pi-companion/.venv/bin/python scripts/set_hdmi_display_mode.py status
```

The default is `koalabyte`. The choice persists across service restarts and reboots in `logs/hdmi/display_mode.json`; reconnecting a monitor restores the selected mode.

Other controls:

- Say `killerkoala show Pi OS on HDMI` or `killerkoala show KoalaByte on HDMI`.
- Select the matching System / Companion menu action.
- Press F12 or the **PI OS** button from the KoalaByte HDMI view.
- Select **Toggle KoalaByte HDMI** from the Raspberry Pi OS application menu.
- In KoalaByte mode, use arrow keys or WASD to navigate, Enter to select, M for the main menu, and Escape to go back. Mouse wheel, touch scrolling, long-press selection, and double-tap-to-menu are also supported.

Verify the monitor contract and service without touching either board serial port:

```bash
systemctl status koalabyte-hdmi.service --no-pager -l
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python scripts/check_hdmi_display.py
cat logs/hdmi/hdmi_display_status.json
```

Expected marker: `HDMI_DISPLAY_CONTRACT_PASS`. After a first install, reboot once so new `video`, `render`, and `input` group memberships take effect. See [Raspberry Pi HDMI Display Switch](docs/HDMI_DISPLAY.md) for backend selection, configuration, and troubleshooting.

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

## Lyrebird music player

**Lyrebird** is KoalaByte Blue’s Pi-owned music player; Mopidy remains the underlying playback engine and exposes its HTTP/MPD interfaces only on localhost by default.

Supported core sources:

- Local files under `/srv/koalabyte-music`.
- Internet-radio presets from `/etc/koalabyte-blue/music.json`.
- Optional Mopidy extensions, including user-configured OpenSubsonic/Navidrome or other supported services.

Playback actions are integrated into the same menu, voice, display, and error lifecycle as other Pi actions:

- Uploaded songs and configured radio stations appear as scrollable Lyrebird lists.
- The ESP32-S3 left display shows the active song/station while the right display shows the current list and highlight.
- The T114 holds Koalagotchi in the `DANCE` animation while playback is active.
- KillerKoala speech pauses active playback before TTS and resumes it afterward.
- Menu, K1-K8, touch, and voice commands share the same Pi-owned queue and playback actions.

Private streaming credentials must remain outside the repository. See [Lyrebird music player](docs/LYREBIRD.md) for library setup, radio presets, display behavior, and controls.

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

## Runtime ownership and authorized radio safety

- `koalabyte-menu.service` is the sole menu/action owner. K1-K8, HDMI keyboard/touch, voice, and remote requests all enter the same action path.
- The voice bridge owns the ESP32-S3 serial connection; the BLE node manager owns the T114 serial connection. Status, display, scan, and maintenance helpers submit brokered requests instead of opening a competing serial reader.
- Managed KoalaByte radios are excluded from owned-device survey results to prevent the platform from treating its own nodes as targets.
- T114 BLE observation is passive by default. Its Pi-commanded lab beacon is non-connectable, requires `"confirm":true`, defaults to 30 seconds, and is capped at 60 seconds.
- Direct SX1262 LoRa driving remains disabled until the exact T114 pin map, region, antenna/RF-switch path, and recovery procedure are physically validated.
- InnoMaker/SocketCAN support remains optional and receive-first. The installer does not transmit CAN frames.

## Normal boot sequence

1. Raspberry Pi network, Bluetooth, udev, and hardware targets become available.
2. Ollama and Mopidy start when installed.
3. `koalabyte-menu.service` initializes K1-K8 and owns live display synchronization.
4. `koalabyte-hdmi.service` auto-detects an optional monitor and presents the selected KoalaByte or Pi OS mode.
5. `koalabyte-ble-node-manager.service` establishes Heltec-primary BLE roles.
6. `koalabyte-dualeye-voice-bridge.service` coordinates local vocabulary, Pi execution, TinyLlama, TTS, music ducking, BLE election, and display expressions.
7. `koalabyte-doctor.service` records diagnostics.
8. T114 shows the boot image and transitions to the articulated mouth.
9. DualEye enters the active cyberpunk eye/menu state.

The obsolete `koalabyte-menu-sync.service` is not used. Display synchronization belongs to the headless menu runtime.

## Verification

```bash
cd ~/KoalaByte-Blue

systemctl status ollama.service --no-pager -l
systemctl status mopidy.service --no-pager -l
systemctl status koalabyte-menu.service --no-pager -l
systemctl status koalabyte-hdmi.service --no-pager -l
systemctl status koalabyte-ble-node-manager.service --no-pager -l
systemctl status koalabyte-dualeye-voice-bridge.service --no-pager -l

./pi-companion/.venv/bin/python scripts/test_gpio_buttons.py
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python scripts/check_hdmi_display.py
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
logs/gpio_buttons/k1_k8_map.json
logs/runtime/headless_menu_status.json
logs/hdmi/hdmi_display_status.json
logs/one_shot/hdmi_display_contract.json
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
PYTHONPATH=pi-companion python3 scripts/check_hdmi_display.py
bash scripts/check_deployability.sh
bash one-shot-install.sh --check-only
```

Dedicated GitHub Actions workflows compile the current ESP32-S3 and T114 sources and publish the same types of artifacts consumed by the canonical one-shot deployment.

## More documentation

Start with the [documentation index](docs/README.md) for detailed flashing/recovery, HDMI, Pi hardware, BLE/GNSS roles, K1-K8 wiring, Lyrebird music, loading sequences, and authorized-lab references.
