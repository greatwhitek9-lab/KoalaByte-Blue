<p align="center">
  <img src="assets/code-signature/koalabyte-code-signature.svg" alt="KoalaByte Blue code signature" width="760">
</p>

# KoalaByte Blue

KoalaByte Blue is a Raspberry Pi 3B+-coordinated cyberpet and owned-device lab platform. The current runtime combines:

- **Raspberry Pi OS Lite** as the headless coordinator, K1-K8 menu state machine, action executor, local AI host, web-research host, BLE node, logging host, and report host.
- **Waveshare ESP32-S3 DualEye** as the animated cyberpunk koala eyes, local KillerKoala wake/menu interface, microphone endpoint, local-response speaker, and Pi Wi-Fi/serial node.
- **Heltec T114** as the articulated Koalagotchi mouth, primary BLE controller, GNSS node, and LoRa/Meshtastic node.
- **Eight-key K1-K8 GPIO board** for physical menu navigation and protected system controls.
- Optional external Pi audio and an optional stock-firmware SocketCAN adapter.

Use the project only with devices, networks, radios, captures, vehicles, and test benches you own or are authorized to assess. The installer does not flash peripheral firmware and does not transmit CAN frames.

## Current runtime contract

### Raspberry Pi

The Pi owns:

- Headless K1-K8 input, menu navigation, action execution, and live display synchronization.
- BLE coordination with the T114.
- ESP32 voice-command escalation, Pi-side speech recognition, menu execution, and general-question routing.
- Local Ollama/TinyLlama conversation through `killerkoala-tinyllama:latest`.
- Optional web research when a question requires current information and internet access is available.
- Australian male `en-AU-WilliamNeural` TTS while the spoken identity remains **KillerKoala**.
- Tone/subject classification for synchronized DualEye expressions and T114 mouth movement.
- Koalagotchi health, mood, action, completion, failure-streak, and latched error-state fanout.
- Stable USB aliases, runtime services, diagnostics, logs, and reports.

### ESP32-S3 DualEye

The Waveshare owns:

- The local wake phrases `Killer Koala` and `Hey Killer Koala`.
- A 10-second post-wake command session that is refreshed by accepted voice commands and trusted Pi button/keyboard activity.
- Saved local status, help, greeting, thanks, banter, and menu vocabulary.
- Local embedded responses without requiring TinyLlama or internet access.
- Complex speech capture when the local vocabulary does not match.
- Animated eyes that remain visible during local speech, Pi/TinyLlama speech, actions, completion, and errors.

### Heltec T114

The T114 owns:

- The primary BLE-controller role.
- GNSS and guarded LoRa/Meshtastic integration.
- A six-second KillerKoala boot splash followed by the text-free articulated mouth.
- Smooth irregular idle mouth choreography.
- Tone-aware speaking sequences for local ESP32 responses and Pi/TinyLlama responses.
- Koalagotchi action animation while the DualEye names or reports the running action.

The Pi installer preserves all peripheral firmware. Current source builds remain under `firmware/`, but flashing is a separate physical development/recovery operation.

## Canonical installation

There are two supported entrypoints:

- `install.sh` is only the clone/update bootstrapper.
- `one-shot-install.sh` is the single canonical Raspberry Pi installer.

### Clean Raspberry Pi without a checkout

```bash
curl -fsSL -o /tmp/koalabyte-install.sh \
  https://raw.githubusercontent.com/greatwhitek9-lab/KoalaByte-Blue/Main/install.sh
bash /tmp/koalabyte-install.sh
```

The bootstrapper installs Git if necessary, clones or fast-forwards `~/KoalaByte-Blue`, then invokes `one-shot-install.sh`.

### Existing checkout

```bash
cd ~/KoalaByte-Blue
KOALABYTE_SERVICE_USER="$(whoami)" bash one-shot-install.sh
```

### Validate without changing the host

```bash
cd ~/KoalaByte-Blue
KOALABYTE_SERVICE_USER="$(whoami)" \
INSTALL_INNOMAKER_CAN=0 \
bash one-shot-install.sh --check-only
```

### Useful options

```bash
bash one-shot-install.sh --skip-packages
bash one-shot-install.sh --skip-audio
bash one-shot-install.sh --skip-can
bash one-shot-install.sh --skip-ai
```

Useful environment controls:

```text
KOALABYTE_SERVICE_USER=<linux-user>
INSTALL_INNOMAKER_CAN=auto|1|0
INSTALL_KILLERKOALA_OLLAMA=auto|1|0
STRICT_KILLERKOALA_OLLAMA=0|1
KILLERKOALA_LLM_MODEL=killerkoala-tinyllama:latest
KILLERKOALA_WEB_SEARCH=auto|always|off
CAN_INTERFACE=can0
CAN_BITRATE=500000
KOALABYTE_AUDIO_SINK_PATTERN='JBL|USB|speaker|audio'
STRICT_GPIO_BUTTONS=0|1
```

`INSTALL_KILLERKOALA_OLLAMA=auto` is fail-soft so hardware setup can still complete during an internet or model-download outage. Use `STRICT_KILLERKOALA_OLLAMA=1` when the installation must fail unless Ollama and the KillerKoala TinyLlama model are fully ready.

## One-shot installation sequence

`one-shot-install.sh` performs the following sequence:

1. Validates the canonical shell helpers and compiles the Pi-side Python runtime.
2. Installs Raspberry Pi OS packages unless `--skip-packages` is used.
3. Creates or updates `pi-companion/.venv` and installs the runtime dependencies.
4. Adds the configured service user to available `gpio`, `dialout`, `audio`, `video`, `render`, and `plugdev` groups.
5. Installs stable ESP32-S3 and T114 udev aliases.
6. Configures optional stock-firmware SocketCAN only when enabled and compatible hardware is present.
7. Installs the headless menu/live-sync service, hardware-doctor service, T114 BLE-node manager, and ESP32 voice bridge.
8. Installs or starts Ollama, pulls `tinyllama:1.1b`, creates `killerkoala-tinyllama:latest`, and runs a short local smoke test unless AI setup is skipped.
9. Installs restricted sudoers permissions for only the K7 shutdown and K8 reboot commands.
10. Discovers connected KoalaByte USB devices and writes the stable device map.
11. Probes K1-K8 GPIO initialization and verifies the protected-button contract.
12. Runs menu, action, voice, TinyLlama, web-control, TTS, display-sync, and runtime-dependency checks.
13. Enables/restarts the runtime services and selects the external audio sink unless skipped.
14. Runs the final hardware doctor and writes the installation status reports.
15. Requests one reboot after the first installation so new hardware-group memberships take effect.

The installer does **not** flash the ESP32-S3, T114, or InnoMaker adapter and does not send CAN frames.

## Private AI and web settings

The voice-bridge installer creates this root-readable file when absent:

```text
/etc/koalabyte-blue/killerkoala.env
```

Typical settings:

```bash
KILLERKOALA_WEB_SEARCH=auto
KILLERKOALA_DIALOGUE_TURNS=4
# BRAVE_SEARCH_API_KEY=
```

A Brave key is optional. Keyless DuckDuckGo Instant Answer and Wikipedia fallbacks remain available. Do not commit private keys to the repository.

## First reboot and verification

After the first full install:

```bash
sudo reboot
```

Then verify:

```bash
cd ~/KoalaByte-Blue

systemctl status ollama.service --no-pager -l
systemctl status koalabyte-menu.service --no-pager -l
systemctl status koalabyte-doctor.service --no-pager -l
systemctl status koalabyte-ble-node-manager.service --no-pager -l
systemctl status koalabyte-dualeye-voice-bridge.service --no-pager -l

./pi-companion/.venv/bin/python scripts/test_gpio_buttons.py
./pi-companion/.venv/bin/python scripts/pi_hardware_doctor.py \
  --can-interface can0 --gpio-live
```

## Boot and runtime sequence

At normal Raspberry Pi boot:

1. Network, Bluetooth, udev, and user-session targets become available.
2. Ollama starts the local model API when installed.
3. `koalabyte-menu.service` starts `scripts/run_headless_menu.py` with no HDMI or desktop requirement.
4. The headless menu initializes K1-K8, opens the main menu, and sends the current menu state to the displays.
5. `koalabyte-ble-node-manager.service` establishes the Pi/T114 BLE-node relationship.
6. `koalabyte-dualeye-voice-bridge.service` waits for the stable ESP32 alias, then coordinates local vocabulary, Pi execution, TinyLlama, TTS, and expression packets.
7. `koalabyte-doctor.service` records field diagnostics.
8. The T114 shows the KillerKoala splash for approximately six seconds, then enters its articulated-mouth idle sequence.

The obsolete `koalabyte-menu-sync.service` is deliberately removed. Live display synchronization is owned by the headless menu runtime.

## K1-K8 button board

Use **3.3 V only**. The Pi internal pull-ups are enabled: idle is HIGH and a pressed key pulls its GPIO LOW.

| Key | Runtime function | Command | BCM GPIO | Physical pin | Activation |
|---|---|---|---:|---:|---|
| K1 | Main Menu | `main_menu` | 5 | 29 | Press |
| K2 | Move Left / Back | `move_left` (`back` alias) | 6 | 31 | Press |
| K3 | Enter / Select | `select` | 13 | 33 | Press |
| K4 | Move Right / Forward | `move_right` (`forward` alias) | 19 | 35 | Press |
| K5 | Up | `up` | 26 | 37 | Press |
| K6 | Down | `down` | 21 | 40 | Press |
| K7 | Safe Shutdown | `power_toggle` | 20 | 38 | Hold 2.5 seconds |
| K8 | Reset / Reboot | `reset` | 16 | 36 | Hold 3.0 seconds |

Power wiring:

```text
Button-board VCC -> Pi 3.3 V, physical pin 1 or 17
Button-board GND -> Pi GND, physical pin 39 recommended
K1-K8           -> Assigned BCM GPIO inputs in the table above
```

Never connect the button board to Pi 5 V.

### Button/menu sequence

1. Press K1 to reopen the main menu from any non-destructive runtime state.
2. Use K5/K6 to move up/down through the current list.
3. Use K2/K4 for left/back and right/forward navigation where the menu supports it.
4. Press K3 to enter a submenu or execute the selected leaf action.
5. During execution, the T114 displays Koalagotchi while the DualEye displays the action state/name.
6. Hold K7 for 2.5 seconds to request a restricted safe shutdown.
7. Hold K8 for 3.0 seconds to request a restricted reboot.

A short tap on K7 or K8 does not emit the destructive command.

## KillerKoala voice and AI sequence

1. While sleeping, ambient commands are ignored; say `Killer Koala` or `Hey Killer Koala`.
2. The ESP32-S3 opens a 10-second wake session and plays a local wake response.
3. Saved status, help, greeting, thanks, banter, and generated menu phrases are recognized and answered locally on the Waveshare.
4. Every accepted command or trusted Pi K1-K8/keyboard event refreshes the 10-second session.
5. If the local Waveshare vocabulary times out during an active session, the ESP32 automatically arms complex audio capture for the Pi instead of returning an unknown-command response.
6. The Pi transcribes the captured phrase and routes it to an exact menu/action command or to `killerkoala_question`.
7. General questions use local `killerkoala-tinyllama:latest`; current-information questions may include web evidence when internet access is available.
8. If TinyLlama is unavailable, KillerKoala returns a local non-destructive fallback response rather than inventing a result.
9. Pi responses use the configured Australian male William TTS backend, but identity sanitization ensures the character identifies only as KillerKoala.
10. The Pi classifies the response tone and subject, sends the full expression palette to the DualEye, and sends a compact sub-256-byte mouth packet to the T114.
11. The eyes and mouth animate for the entire spoken response, then settle back to the current menu, Koalagotchi, or idle state.

Local ESP32 responses are spoken by the Waveshare audio path. Pi/TinyLlama responses are played through the configured Pi audio output. The T114 mouth follows both speech owners.

## Action, completion, and error sequence

1. An exact menu or voice action is latched as `action` before execution begins.
2. The T114 switches to Koalagotchi action animation while the DualEye reports the executing action.
3. The Pi runs the action and writes the XP/result state before releasing the display lifecycle.
4. Success produces `action_complete`, resets the consecutive-failure counter, speaks the result when applicable, and keeps the eyes/mouth synchronized to the result tone.
5. A normal failed attempt produces a disappointed state; repeated failures progress to angry after the configured failure threshold.
6. Fault/error results enter a latched alarm state and remain visible until an explicit clear/recovery event is received.
7. Menu navigation exits persistent Koalagotchi display mode and restores normal navigation state.

## Device discovery

```bash
cd ~/KoalaByte-Blue
./pi-companion/.venv/bin/python scripts/discover_koalabyte_ports.py \
  --profile heltec --output-dir logs/preflight

ls -l /dev/koalabyte-* 2>/dev/null || true
```

Expected aliases when connected:

```text
/dev/koalabyte-heltec
/dev/koalabyte-heltec-t114
/dev/koalabyte-esp32-dualeye
```

## Services and status files

Service status:

```bash
systemctl status koalabyte-menu.service --no-pager -l
systemctl status koalabyte-doctor.service --no-pager -l
systemctl status koalabyte-ble-node-manager.service --no-pager -l
systemctl status koalabyte-dualeye-voice-bridge.service --no-pager -l
```

Primary status files:

```text
logs/one_shot/final_install_status.json
logs/killerkoala/ollama_setup_status.json
logs/killerkoala/killerkoala_ai_readiness.json
logs/killerkoala/killerkoala_last_companion_response.json
logs/killerkoala/web_research/latest.json
logs/runtime/headless_menu_status.json
logs/runtime/headless_menu_events.jsonl
logs/preflight/koalabyte_ports.json
logs/gpio_buttons/gpio_button_status.json
logs/gpio_buttons/gpio_button_runtime_events.jsonl
logs/pi_hardware/pi_hardware_doctor.json
```

## Firmware policy and source builds

The working peripheral firmware is preserved by the Pi installer:

- ESP32-S3 DualEye: local wake/menu vocabulary, complex-capture fallback, Pi node bridge, and tone-aware eyes.
- Heltec T114: six-second boot artwork, original-texture articulated mouth, tone-aware speech, BLE/GNSS, and latched Koalagotchi lifecycle.
- InnoMaker or other SocketCAN adapter: stock adapter firmware only.

Current firmware source:

```text
firmware/esp32-dualeye/
firmware/t114-combined-safe/
```

Dedicated GitHub Actions workflows compile and publish source-build artifacts. They do not create or run an automatic hardware flasher. Physical flashing remains separate from `install.sh` and `one-shot-install.sh`.

## Validation

Repository and installer checks:

```bash
python3 scripts/check_repo_readiness.py
PYTHONPATH=pi-companion python3 scripts/check_one_shot_controls.py
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_ai.py
PYTHONPATH=pi-companion python3 scripts/check_killerkoala_face_mouth_sync.py
bash scripts/check_deployability.sh
KOALABYTE_SERVICE_USER="$(whoami)" \
INSTALL_INNOMAKER_CAN=0 \
bash one-shot-install.sh --check-only
```

The CI contract verifies:

- Canonical one-shot syntax and check-only execution.
- Headless Raspberry Pi OS Lite runtime.
- Correct K1-K8 GPIO mapping and K7/K8 hold protection.
- Restricted shutdown/reboot permissions.
- Menu/action catalog and display synchronization.
- TinyLlama question routing, web controls, KillerKoala identity, and Australian TTS.
- Tone-aware DualEye/T114 speech synchronization.
- Stable USB aliases and no-flash/no-CAN-transmit installer policy.
- Current ESP32-S3 source compilation.
- Current Heltec T114 articulated-mouth source compilation and UF2 validation.
