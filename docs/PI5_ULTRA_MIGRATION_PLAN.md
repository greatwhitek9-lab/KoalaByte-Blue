# KoalaByte Blue Ultra — Pi 5 / Trixie Migration Plan

**Target:** Raspberry Pi 5, 8 GB RAM, 64-bit Raspberry Pi OS Trixie  
**Branch:** `koalabyte-blue-ultra`  
**Baseline:** `Main` at `73a08711afeb7e41b71cc732bf5e276f9cab76e2`  
**Safety rule:** Preserve the currently known-good ESP32-S3 DualEye and Heltec T114 firmware images, identities, protocol schemas, and serial-owner boundaries. No MCU flashing is part of the initial host-port stages.

## 1. Audit snapshot

The branch is already **25 commits ahead of Main** and has no commits behind it. It includes an initial Pi 5 Ultra profile implementation and documentation; this is not yet evidence of a completed or hardware-validated migration.

### Existing assets worth preserving

- `one-shot-install.sh` orchestrates host setup, MCU firmware deployment, AI, music, GPIO, services, and final health checks.
- `scripts/setup_pi_hardware_stage.sh` validates source contracts, runs the Pi 5 profile check, installs packages/venv/services, and configures audio and hardware rules.
- `scripts/check_supported_host.py` recognizes Raspberry Pi 5 and accepts Debian/Raspberry Pi OS Bookworm or Trixie on 64-bit userspace with Python 3.10–3.13.
- `pi-companion/koalablue/pi_runtime_profile.py` detects the device-tree model, available memory, and CPU count, then returns bounded AI/display/processing recommendations.
- `scripts/check_pi5_ultra_profile.py` provides hardware-free fixtures for Pi 5 2/4/8/16 GB and Pi 3B+ resource tiers.
- `scripts/setup_killerkoala_ollama.sh` applies RAM-aware Ollama service defaults and creates a temporary profile-specific Modelfile while leaving the checked-in Pi 3-safe Modelfile unchanged.
- `pi-companion/koalablue/hdmi_display.py` has a read-only compositor, selects Wayland/X11 when available and otherwise allows SDL KMS/DRM, and does not initialize a competing mixer.
- The existing ESP32/T114 firmware, protocol and verified-flash gates are present and must remain authoritative.

### Gaps and risks to close before calling the port complete

1. **The current branch is a profile-first port, not a finished system redesign.** Its docs explicitly state that physical Pi 5 verification remains outstanding.
2. **The processing profile is partly advisory.** The profile reports worker, build-job, and swap targets, but those values must be traced to every consumer before claiming the entire system actually uses them. Do not silently provision swap or alter scheduling based only on a recommendation.
3. **HDMI 60 FPS is a target, not a measured result.** Validate Trixie’s actual Wayland/X11/KMSDRM path, display-mode switching, sustained frame timing, and interaction latency on the target monitor.
4. **GPIO needs a real backend test on Pi 5/Trixie.** The project uses `gpiozero`; confirm the installed pin factory/backend and K1–K8 edge/hold behavior. Keep the existing BCM map and protected K7/K8 semantics unchanged.
5. **Audio and desktop behavior are OS-image dependent.** Confirm the selected ALSA/PipeWire/PulseAudio path, USB audio selection, TTS, playback ducking, and coexistence with the HDMI compositor.
6. **The default one-shot installer can build and flash both MCU targets.** It must not be used for initial Pi-only migration tests without explicit firmware-skip mode. Keep the known-good bundle and flash receipts backed up and verifiable.
7. **AI improvement is currently resource tuning, not a model-quality upgrade.** TinyLlama 1.1B remains the compatibility baseline. A larger model should be a separate benchmarked option, never an automatic replacement.
8. **No test result in this audit proves physical hardware compatibility.** Source/fixture checks and CI are necessary but cannot replace tests on a Pi 5 running Trixie with the real display, audio devices, buttons, ESP32, and T114.

## 2. Target architecture

Keep the MCU split and Pi-owned control plane:

- **Pi 5 host:** menu/action orchestration, local AI and optional research, voice/TTS routing, HDMI compositor, K1–K8 handling, state persistence, logging, diagnostics, and systemd lifecycle.
- **ESP32-S3 DualEye:** retain the current wake/microphone/local-response/eyes/serial contract.
- **Heltec T114:** retain the current mouth/Koalagotchi/BLE/GNSS/USB JSON contract and guarded radio behavior.
- **Exclusive serial ownership:** only the designated ESP32 voice-bridge and Heltec BLE-manager services may own their respective serial streams. UI, AI, diagnostics, and maintenance must use the existing broker/command bus.
- **Resource profile:** detect hardware and produce a bounded, observable profile; all settings remain overridable. Hardware detection must not change clock/voltage, flash devices, or make irreversible system changes.

## 3. Staged migration

### Stage 0 — Freeze and establish a rollback point

**Changes:** none to device firmware.

1. Record the exact `Main` commit and the current Ultra branch head.
2. Save the known-good ESP32-S3 and T114 artifacts, manifests, SHA-256 values, runtime identities, and successful flash receipts outside the working checkout.
3. Capture a baseline health report from the currently working KoalaByte setup: services, serial-owner sockets, voice, menu, HDMI, audio, BLE/GNSS, Koalagotchi, and error lifecycle.
4. Verify that `Main` remains unchanged by this work.

**Gate:** a verified firmware rollback bundle exists; no MCU write is allowed if the bundle or power preflight is missing.

### Stage 1 — Static and hardware-free validation

Run these in the Ultra checkout before installing packages or attaching any flash action:

```bash
python3 scripts/check_supported_host.py
PYTHONPATH=pi-companion python3 scripts/check_pi5_ultra_profile.py --check-only
PYTHONPATH=pi-companion python3 scripts/check_serial_command_bus.py
PYTHONPATH=pi-companion python3 scripts/check_hdmi_display.py
python3 scripts/check_firmware_hardware_contract.py
python3 scripts/check_firmware_protocol_contract.py
python3 scripts/check_verified_firmware_flashes.py
bash one-shot-install.sh --check-only
```

Also run the repository’s shell syntax, Python compilation, whole-system source, menu/action, voice, and runtime-dependency gates used by CI. Fix failures on the Ultra branch only.

**Gate:** all non-writing checks pass; profile fixtures cover Pi 5 2/4/8/16 GB and legacy Pi 3B+ behavior; the firmware source/protocol/receipt checks show no unintended contract changes.

### Stage 2 — Trixie host compatibility

1. Use a **clean 64-bit Raspberry Pi OS Trixie image**. Raspberry Pi’s upgrade guidance recommends imaging a clean Trixie system rather than attempting an in-place Bookworm-to-Trixie upgrade.
2. Install KoalaByte in Pi-only mode; do not run firmware deployment. Use `--skip-firmware` and skip optional AI/music only when needed to isolate failures.
3. Audit package availability and Python wheel/build behavior for Trixie/Python 3.13, especially `pygame`, `gpiozero` plus its GPIO backend, `pyserial`, `bleak`, PocketSphinx, audio dependencies, and CAN tools.
4. Confirm udev aliases and permissions survive reboot and the services run as the intended non-root service user.

**Gate:** clean install and reboot succeed; no service depends on a Pi 3-only device name, deprecated GPIO backend, hard-coded user path, or missing Trixie package.

### Stage 3 — GPIO, USB and MCU integration

1. Verify K1–K8 physical BCM mappings, debounce, navigation, and protected K7/K8 long-press actions.
2. Verify stable ESP32/T114 udev aliases, serial-owner sockets, exclusive access, reconnect behavior, and command acknowledgements.
3. Exercise USB recovery detection without writing firmware. Confirm that firmware deployment remains disabled in this stage.
4. Test BLE role election, T114 primary behavior, and the guarded ESP32 fallback.

**Gate:** repeated reconnect/reboot tests pass; no direct serial open by the HDMI/menu/diagnostic processes; MCU identities remain unchanged.

### Stage 4 — HDMI and Koalagotchi performance

1. Test the actual Trixie display path: Wayland first where a desktop session exists, then X11 where configured, and SDL KMS/DRM for headless/lite mode.
2. Validate KoalaByte ↔ Pi OS display switching while menu, voice, board brokers, BLE, and AI remain alive.
3. Benchmark 30/45/60 FPS rather than assuming 60 FPS is sustainable. Measure frame-time distribution, input-to-display latency, CPU load, memory, and dropped frames under simultaneous voice/AI/audio.
4. Keep Koalagotchi and HDMI animation budgets synchronized. Reduce frame rate automatically or via configuration if thermal/load tests show dropped frames or audio/voice regressions.
5. Confirm the renderer does not open MCU serial ports or initialize a competing audio mixer.

**Gate:** at least 30 minutes of combined display/voice/menu/AI activity without flicker loops, service restarts, audio interference, or serial-owner violations; desktop switching works in both directions.

### Stage 5 — AI and voice tuning

1. Keep TinyLlama 1.1B as the fallback/compatibility model. Validate the Ultra profile’s initial 2,048-token context, two parallel requests, one loaded model, 300-second keep-alive, and 160-token output budget on the actual 8 GB Pi 5.
2. Measure cold-start time, warm response latency, peak RSS, token throughput, thermal behavior, and latency during concurrent HDMI, speech, and Mopidy activity.
3. Preserve local PocketSphinx/STT and saved-response fallback; web research remains optional and must not block offline commands.
4. Validate voice wake/session handling, Australian William TTS backend, KillerKoala identity, speech ducking, expression mapping, and Koalagotchi state.
5. Evaluate larger quantized models only as an opt-in experiment after measuring real memory/latency. Do not claim improved intelligence based on hardware alone.

**Gate:** no OOM kills, no loss of offline command paths, acceptable measured response latency, and correct TTS/identity/expression behavior.

### Stage 6 — Processing, storage, power and thermals

1. Trace the profile’s worker/build-job values to the actual call sites. Apply bounded concurrency only where parallelism is safe; keep MCU flash and shared serial operations serialized.
2. Benchmark firmware builds with one, two, and four jobs on the Pi 5 8 GB. Choose a default based on peak RAM and thermal behavior.
3. Treat swap as an explicit setup decision with disk-space, wear, and power safeguards; do not silently resize active swap from profile detection.
4. Record CPU temperature, throttling, memory pressure, storage latency, and service restarts during sustained load.
5. Require a healthy Pi 5 power state before any MCU flash. No overclocking or voltage changes.

**Gate:** 30–60 minute soak test under AI + HDMI + voice/audio + device telemetry, no OOM or throttling-related degradation, and a clean power preflight. Any nonzero current/latched under-voltage/throttle state blocks flashing until investigated and cleared.

### Stage 7 — Full-system acceptance and release

1. Run all existing source, installer, firmware, protocol, exact flash receipt, live runtime, HDMI, GPIO, AI, music, BLE, and error-lifecycle checks.
2. Run a final Pi-only install/reboot acceptance first.
3. Only if a firmware update is independently required, review its diff, bundle manifest, identity markers, checksum, and board-specific recovery route. Flash one target at a time and verify identity after each write.
4. Publish a release note that separates source checks, CI results, and tests completed on physical Pi 5/Trixie hardware.
5. Keep the known-good firmware bundle and a tested `git switch Main` rollback path.

**Release gate:** no known-good firmware is replaced merely to validate the Pi port; all hardware gates pass; measured results and any remaining limitations are documented.

## 4. Acceptance criteria

- Pi 5 8 GB and 64-bit Trixie pass host preflight.
- A clean Pi-only install and reboot pass without flashing either MCU.
- K1–K8, menu/action state, voice, AI, TTS, Mopidy/ducking, BLE/GNSS, and serial brokers operate together.
- HDMI renders expressive eyes/mouth, menu and Koalagotchi; Pi OS switching does not stop background services.
- Runtime profile, AI settings, frame rate, processing limits, thermal state, and failures are observable in reports/logs.
- No OOM, runaway CPU, repeated service restarts, direct serial ownership conflicts, or power/thermal safety violations during soak tests.
- ESP32-S3 and T114 identities/protocols remain intact unless a separately reviewed firmware change is explicitly approved.

## 5. Rollback

- Source-only rollback: `git switch Main`.
- Host rollback: restore the captured configuration and service baseline, or re-image the clean OS if the Trixie setup is compromised.
- MCU rollback: flash only the archived, checksum-verified known-good artifacts using the board-specific recovery process and only after the strict Pi power gate passes.
- Do not use `git reset --hard`, erase flash, replace bootloaders/partitions, or overwrite the known-good bundle as a migration shortcut.

## 6. External platform note

Raspberry Pi’s published Trixie guidance recommends a clean image rather than an in-place upgrade of a customized Bookworm installation. The Ultra migration should therefore be validated on a separate clean Trixie install, leaving the currently working Pi untouched until acceptance is complete.
