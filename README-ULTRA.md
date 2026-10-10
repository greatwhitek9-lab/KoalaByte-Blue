# KoalaByte Blue Ultra — Raspberry Pi 5 (8 GB)

**Target platform:** Raspberry Pi 5, 8 GB RAM, 64-bit Raspberry Pi OS Bookworm or Trixie.  
**Branch:** `koalabyte-blue-ultra` (Git branch names cannot contain spaces).  
**Base:** `Main` from KoalaByte Blue.  
**Scope:** Pi-host upgrades; preserve the ESP32-S3 DualEye and Heltec T114 firmware/protocol contracts.

> **Port status:** The branch contains source-level migration work and hardware-aware profiles. It has not yet been verified on the target Pi 5. Run the preflight and check-only gates below before installing or flashing anything.

## Ultra upgrade ledger

| Area | Change in this branch | Validation status |
|---|---|---|
| Host support | Pi 5 is explicitly recognized in the 64-bit host preflight; Pi 3B+, Pi 4, Pi 400, Pi 500 and Pi 5 remain recognized. | Source change; run host gate on target |
| Hardware-aware budgets | Canonical `pi_runtime_profile.py` detects model, RAM, CPU count and emits AI, HDMI, worker/build and power recommendations. | Offline/profile-checkable |
| Local AI | Pi 5 with at least 7,000 MiB detected RAM recommends a 2,048-token context, up to two parallel requests, one loaded model, 300-second keep-alive and 160-token output budget. Explicit environment overrides win. | Recommendation; smoke-test on hardware |
| HDMI | Renderer reads the same profile. Pi 5 8 GB targets up to 60 FPS; lower-RAM Pi 5 targets 45 FPS; Pi 3-class hosts remain conservative. Explicit `KOALABYTE_HDMI_FPS` or `--fps` overrides remain available. | Source change; display backend must be tested on target |
| Processing | Profile recommends up to four runtime workers and up to four firmware build jobs for Pi 5 8 GB; lower-memory systems get more conservative build budgets. Swap target and thermal policy are reported, not silently applied by profile detection. | Profile output; benchmark on target |
| Power and thermal safety | No overclock is introduced. Existing deployment power gate remains in force; a current or latched under-voltage condition must be cleared before hardware writes. Official Pi 5 27 W / 5 V 5 A supply is recommended for full peripheral load. | Must verify on target |
| MCU compatibility | ESP32-S3 and Heltec T114 sources, identities, serial ownership, and protocols are intentionally preserved. | Must run existing source and firmware gates |
| Documentation | This branch-specific README records the Ultra profile and its validation status. | Added |

## Recommended clean install

Use the 64-bit Raspberry Pi OS Bookworm or Trixie image, connect the HDMI display, keyboard, ESP32-S3 and Heltec T114, and join Wi-Fi first. Clone this branch rather than `Main`:

```bash
git clone --branch koalabyte-blue-ultra --single-branch \
  https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
```

Check the detected hardware profile:

```bash
PYTHONPATH=pi-companion python3 scripts/koalabyte_ultra_profile.py --require-8gb
```

Run non-writing validation before installation:

```bash
python3 scripts/check_supported_host.py
python3 scripts/check_whole_system_deployment.py --source-only
bash one-shot-install.sh --check-only
```

If those checks pass, run the project's normal deployment procedure. Do not flash either MCU just to test Pi host detection. If a later deployment requests firmware, review the manifest/identity and power preflight first.

## Runtime profile

The canonical detector is `pi-companion/koalablue/pi_runtime_profile.py`. It reads the device-tree model and `/proc/meminfo`; profile detection does not require network access, alter files, change clocks/voltage, or flash firmware. The CLI wrapper is `scripts/koalabyte_ultra_profile.py`.

For a Pi 5 with at least 7,000 MiB detected RAM, the profile recommends:

- Ollama context: 2,048 tokens
- Ollama parallel requests: 2
- Maximum loaded models: 1
- Ollama keep-alive: 300 seconds
- Generated output budget: 160 tokens
- HDMI / Koalagotchi target: up to 60 FPS
- Runtime worker budget: up to four
- Firmware build jobs: up to four
- Build swap target: 1,024 MiB (profile recommendation)

These are starting points, not guarantees of sustained throughput. Cooling, power, storage, audio/voice workload and actual model memory use still affect performance. Use an active cooler and an adequate Pi 5 power supply for sustained AI or firmware builds. Swap and parallelism should be validated under load rather than assumed optimal.

## AI and Koalagotchi

- KillerKoala remains the persona; the Australian `en-AU-WilliamNeural` voice remains a TTS backend, not the persona identity.
- The branch adapts Ollama resource defaults to detected hardware but does not automatically download a larger language model or claim a newly fine-tuned model. Keep TinyLlama as the compatibility baseline until candidate models pass latency, memory and response-quality tests.
- Existing expression/state payloads remain the source of truth for Koalagotchi; the Pi 5 profile adds resource headroom without changing the ESP32/T114 protocol contract.
- Web research remains optional and network-dependent. Offline local responses and wake/session routing must continue to work.
- Existing T114 passive BLE/GNSS defaults, guarded LoRa hooks and receive-first CAN posture remain unchanged.

## HDMI and processing

The compositor's profile-based frame-rate default is selected by `pi_runtime_profile.py`. You can inspect it before launching the display:

```bash
PYTHONPATH=pi-companion python3 scripts/koalabyte_ultra_profile.py --check
PYTHONPATH=pi-companion python3 scripts/check_hdmi_display.py
systemctl status koalabyte-hdmi.service --no-pager -l
```

The compositor still respects `KOALABYTE_HDMI_FPS` and the `--fps` command-line option. The profile's worker/build values are advisory budgets; they are not a promise that every subsystem is parallelized. Serial ports remain owned by their dedicated services, and the HDMI renderer must not open board serial ports or initialize a competing audio mixer.

## Verification checklist

- [ ] Host gate identifies Raspberry Pi 5 and a supported 64-bit OS.
- [ ] `koalabyte_ultra_profile.py --require-8gb` exits successfully and reports `is_pi5: true` with at least 7,000 MiB RAM.
- [ ] Whole-system source checks and installer `--check-only` pass.
- [ ] Ollama context, parallelism and keep-alive settings are confirmed in the installed service.
- [ ] HDMI compositor opens on the actual display backend; KoalaByte/Pi OS switching works.
- [ ] ESP32-S3 and T114 owner services remain the only readers of their respective serial ports.
- [ ] Voice, K1–K8, menu/action state, Koalagotchi, audio ducking and alarm behavior pass on hardware.
- [ ] Power/thermal state stays clean under sustained use.
- [ ] Existing firmware identities are verified before any MCU flash.

## Rollback

This work is isolated to `koalabyte-blue-ultra`. To return to the original branch without changing it:

```bash
git switch Main
```

The profile detector itself does not alter the Pi OS image, bootloader, partition table or device firmware.
