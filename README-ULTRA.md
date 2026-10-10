# KoalaByte Blue Ultra — Raspberry Pi 5 (8 GB)

**Target platform:** Raspberry Pi 5, 8 GB RAM, 64-bit Raspberry Pi OS Bookworm or Trixie.  
**Branch:** `koalabyte-blue-ultra` (Git branch names cannot contain spaces).  
**Base:** `Main` from KoalaByte Blue.  
**Scope:** Pi-host upgrades; preserve the ESP32-S3 DualEye and Heltec T114 firmware/protocol contracts.

> **Port status:** The changes in this branch are source-level migration work. They are not yet hardware-verified on a Pi 5. Run the preflight and check-only gates below before installing or flashing anything.

## Ultra upgrade ledger

| Area | Change in this branch | Validation status |
|---|---|---|
| Host support | Pi 5 is an explicitly supported host in the preflight detector; Pi 3B+, Pi 4, Pi 400, and Pi 500 remain recognized. | Source change; run host gate on target |
| Hardware profile | New host detector reports model, RAM, CPU count, selected AI limits, HDMI target FPS, and bounded worker count. | Offline/profile-checkable |
| Local AI | Pi 5 8 GB profile recommends 2,048-token Ollama context, up to two parallel requests, one loaded model, and 5-minute keep-alive. Existing explicit environment settings win. | Recommendation; smoke-test on hardware |
| HDMI | HDMI renderer selects a profile-based default frame rate (45 FPS for Pi 5 8 GB, 40 FPS for other Pi 5, 30 FPS for legacy Pi) while retaining explicit `--fps` overrides. | Source change; display backend must be tested on target |
| Processing | Profile caps general worker recommendations at four, with at least two on Pi 5. The setting is advisory and does not force thread counts in unrelated services. | Profile output only |
| MCU compatibility | ESP32-S3 and Heltec T114 sources, identities, serial ownership, and protocols are intentionally unchanged by this host-profile change. | Must run existing source and firmware gates |
| Documentation | This branch-specific README records the Pi 5 Ultra changes and their verification status. | Added |

## Recommended clean install

Use the 64-bit Raspberry Pi OS image, connect the HDMI display, keyboard, ESP32-S3, and Heltec T114, and join Wi-Fi first. Clone this branch rather than `Main`:

```bash
git clone --branch koalabyte-blue-ultra --single-branch \
  https://github.com/greatwhitek9-lab/KoalaByte-Blue.git
cd KoalaByte-Blue
```

Check the detected hardware profile:

```bash
PYTHONPATH=pi-companion ./pi-companion/.venv/bin/python \
  scripts/koalabyte_ultra_profile.py --require-8gb
```

If the virtual environment does not exist yet, use the system Python to inspect the profile without installing dependencies:

```bash
PYTHONPATH=pi-companion python3 scripts/koalabyte_ultra_profile.py --require-8gb
```

Run non-writing validation before installation:

```bash
python3 scripts/check_supported_host.py
python3 scripts/check_whole_system_deployment.py --source-only
bash one-shot-install.sh --check-only
```

After those checks pass, install using the project's normal deployment procedure. Do not flash either MCU just to test Pi host detection. If a later deployment requests firmware, review the manifest/identity and power preflight first.

## Runtime profile

The detector is `pi-companion/koalablue/hardware_profile.py`. It reads the device-tree model and `/proc/meminfo`; it does not require network access, modify files, change power settings, or flash firmware.

For a Pi 5 with at least 7,000 MiB detected RAM, its recommended values are:

- Ollama context: 2,048 tokens
- Ollama parallel requests: 2
- Maximum loaded models: 1
- Ollama keep-alive: 5 minutes
- HDMI target frame rate: 45 FPS (capped at 60)
- Suggested processing workers: 2–4, capped at four

These are starting points, not promises of sustained throughput. Thermal state, cooling, power supply, SD/SSD performance, active voice/audio workloads, and actual model memory use still affect results. Use a Pi 5 active cooler and an adequate Pi 5 power supply for sustained AI or firmware builds.

## AI and safety notes

- The current local persona remains `KillerKoala`; the Australian `en-AU-WilliamNeural` voice remains a TTS backend, not the persona identity.
- The profile does not download a larger model or alter the persona Modelfile. Any model upgrade should be benchmarked for latency, RAM pressure, and quality before becoming a default.
- Web research remains an optional network-dependent layer. Offline local responses and existing wake/session routing should continue to work.
- No new unsafe radio behavior is enabled. The existing T114 passive BLE/GNSS defaults, guarded LoRa hooks, and receive-first CAN posture remain unchanged.

## Verification checklist

- [ ] Host gate identifies Raspberry Pi 5 and a 64-bit supported OS.
- [ ] `koalabyte_ultra_profile.py --require-8gb` reports `pi5-8gb-ultra`.
- [ ] Whole-system source checks and installer `--check-only` pass.
- [ ] Ollama context/parallel/keep-alive settings are confirmed in the installed service.
- [ ] HDMI compositor opens on the intended Pi 5 display backend; KoalaByte/Pi OS switching works.
- [ ] ESP32-S3 and T114 owner services remain the only readers of their respective serial ports.
- [ ] Voice, K1–K8, menu/action state, Koalagotchi, audio ducking, and alarm behavior pass on hardware.
- [ ] Power/thermal checks are clean under sustained use.
- [ ] Existing firmware identities are verified before any MCU flash.

## Rollback

This work is isolated to `koalabyte-blue-ultra`. To return to the original branch without changing it:

```bash
git switch Main
```

No Pi OS image, bootloader, partition table, or device firmware is changed by the profile detector itself.
