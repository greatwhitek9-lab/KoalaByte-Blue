# KoalaByte Blue Ultra — Raspberry Pi 5 (8 GB)

**Target platform:** Raspberry Pi 5, 8 GB RAM, 64-bit Raspberry Pi OS Bookworm or Trixie.  
**Branch:** `koalabyte-blue-ultra` (Git refs cannot contain spaces).  
**Base:** `Main` from KoalaByte Blue.  
**Scope:** Pi 5 host upgrades; preserve the ESP32-S3 DualEye and Heltec T114 firmware/protocol contracts.

> **Port status:** This branch contains Pi 5 host-profile and adaptive-resource source changes. It has not yet been verified on the physical target Pi 5. Run the hardware-free profile tests and deployment check gates before installing or flashing anything.

## Ultra upgrade ledger

| Area | Change in this branch | Validation status |
|---|---|---|
| Host support | Pi 5 is explicitly recognized in the 64-bit host preflight; Pi 3B+, Pi 4, Pi 400, Pi 500 and Pi 5 remain recognized. | Source change; run host gate on target |
| Hardware-aware budgets | Canonical `pi_runtime_profile.py` detects model, RAM, CPU count and emits AI, HDMI, worker/build and power recommendations. | Hardware-free profile tests available |
| Local AI | Pi 5 with at least 7,000 MiB detected RAM recommends a 2,048-token context, up to two parallel requests, one loaded model, 300-second keep-alive and 160-token output budget. A temporary profile-specific Modelfile applies context/output limits without editing the checked-in Pi 3-safe source. Explicit environment overrides win. | Recommendation; smoke-test on hardware |
| Local response sizing | Response length is tuned by detected RAM tier to avoid long generations on lower-memory Pis while allowing more headroom on Pi 5 8 GB. | Source change; measure latency on target |
| HDMI / Koalagotchi | Renderer selects synchronized frame budgets by Pi generation/RAM. Pi 5 8 GB targets up to 60 FPS; 4 GB Pi 5 targets 45 FPS; 2 GB Pi 5 targets 30 FPS. Wayland/X11 is preferred when available, with SDL KMS/DRM fallback. | Source change; display backend must be tested on target |
| Processing | Profile recommends up to four runtime workers and up to four firmware build jobs for Pi 5 8 GB; lower-memory systems get more conservative build budgets. Swap target and thermal policy are reported, not silently applied by profile detection. | Profile output; benchmark on target |
| Optional Ultra Vision | USB/UVC camera capture and local object detection; opt-in protected GNSS tagging, operator-supplied Kruisin event/session references, and confidence-scored camera-like candidates for manual verification. No automatic RF-to-photo matching. | Source-contract check; camera/model/GNSS must be tested on hardware |
| Power and thermal safety | No overclock is introduced. Existing deployment power gate remains in force; a current or latched under-voltage condition must be cleared before hardware writes. Official Pi 5 27 W / 5 V 5 A supply is recommended for full peripheral load. | Must verify on target |
| MCU compatibility | ESP32-S3 and Heltec T114 sources, identities, serial ownership, and protocols are intentionally preserved. | Must run existing source and firmware gates |
| Validation and CI | Hardware-free fixtures cover Pi 5 2/4/8/16 GB and Pi 3B+ resource tiers; the profile is included in dependency and installer-contract checks. | Checks are committed; execution results must be confirmed in CI/on hardware |
| Documentation | This branch-specific README records the Ultra profile and its validation status; detailed technical notes live in `docs/PI5_ULTRA.md`. | Added |

## Optional AI camera

See [Ultra Vision](docs/ULTRA_VISION.md) for USB/UVC setup, local model requirements, KillerKoala's request-triggered conversational vision (spoken requests such as “what do you see?”), opt-in GNSS, Kruisin event references, camera-like object review, privacy constraints, and hardware-free validation. KillerKoala captures one still frame per explicit visual request and answers from a configured local Ollama vision model; it does not pretend to see when the camera/model is unavailable. The feature is optional and does not install camera dependencies unless the operator requests them.

## Recommended clean install

Use the 64-bit Raspberry Pi OS Bookworm or Trixie image, connect the HDMI display, keyboard, ESP32-S3 and Heltec T114, and join Wi-Fi first. Clone this branch rather than `Main`:

```bash
git clone --branch koalabyte-blue-ultra --single-branch \
  https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
```

Run the hardware-free profile checks and inspect the detected profile:

```bash
PYTHONPATH=pi-companion python3 scripts/check_pi5_ultra_profile.py --check-only
PYTHONPATH=pi-companion python3 scripts/check_pi5_ultra_profile.py --json
```

Run non-writing validation before installation:

```bash
python3 scripts/check_supported_host.py
python3 scripts/check_whole_system_deployment.py --source-only
bash one-shot-install.sh --check-only
```

If those checks pass, run the project's normal deployment procedure. Do not flash either MCU just to test Pi host detection. If a later deployment requests firmware, review the manifest/identity and power preflight first.

## Runtime profile

The canonical detector is `pi-companion/koalablue/pi_runtime_profile.py`. It reads the device-tree model and `/proc/meminfo`; profile detection does not require network access, alter files, change clocks/voltage, or flash firmware. Hardware-free fixtures in `scripts/check_pi5_ultra_profile.py` exercise 2 GB, 4 GB and 8/16 GB Pi 5 profiles and a legacy Pi 3B+ profile.

For a Pi 5 with at least 7,000 MiB detected RAM, the profile recommends:

- Ollama context: 2,048 tokens
- Ollama parallel requests: 1
- Maximum loaded models: 1
- Ollama keep-alive: 300 seconds
- Generated output budget: 128 tokens
- HDMI / Koalagotchi target: up to 60 FPS
- Runtime worker budget: up to four
- Firmware build jobs: up to four
- Build swap target: 1,024 MiB (profile recommendation)

These are starting points, not guarantees of performance. Full documentation remains in [Pi 5 Ultra notes](docs/PI5_ULTRA.md).
