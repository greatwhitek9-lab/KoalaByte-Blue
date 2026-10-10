# KoalaByte Blue Ultra — Raspberry Pi 5 profile

This branch adds a Pi 5 host profile while retaining the existing ESP32-S3 DualEye
and Heltec T114 firmware/protocols. It does not flash either board unless the
normal whole-system installer is explicitly run without `--skip-firmware`.

## Branch

Use `koalabyte-blue-ultra` (Git refs cannot contain spaces).

## Pi 5 host changes

- Detects the actual board model, RAM tier, CPU count, 64-bit userspace, OS release,
  and power/throttle status rather than warning that the installer is only tuned
  for Pi 3B+.
- Selects conservative AI limits by RAM. Pi 5 with 8/16 GB receives a 2048-token
  context and at most two parallel requests; 4 GB receives a 1536-token context
  and one request; 2 GB stays at 1024 tokens and one request.
- Raises HDMI/Koalagotchi rendering budget on higher-RAM Pi 5 models while keeping
  the two animation budgets synchronized. The renderer continues to prefer an
  existing Wayland/X11 desktop session and otherwise uses SDL KMS/DRM.
- Exposes a bounded processing/build budget and reports the hardware profile.
  No overclocking, voltage changes, or automatic firmware changes are performed.
- Keeps the exclusive serial-owner services and the existing T114/ESP32 command
  contracts unchanged.

## Checks

Run these before installation:

```bash
python3 scripts/check_pi5_ultra_profile.py --check-only
python3 scripts/check_supported_host.py
bash one-shot-install.sh --check-only
```

On the Pi, the full profile is recorded at
`logs/pi_hardware/pi5_ultra_profile.json` during the hardware setup stage.

## AI tuning

The installer uses the profile only when `OLLAMA_CONTEXT_LENGTH`,
`OLLAMA_NUM_PARALLEL`, `OLLAMA_MAX_LOADED_MODELS`, or `OLLAMA_KEEP_ALIVE`
are not explicitly set. The model remains TinyLlama 1.1B. This is resource-aware
configuration, not a claim that the model has been retrained or that a larger
model will fit safely. Existing voice routing, local STT, web-research policy,
Australian TTS backend, and spoken identity are retained.

## Hardware notes

Use a proper Pi 5 power supply (5 V / 5 A class) and cooling appropriate for
sustained AI and firmware-build workloads. KoalaByte's strict power preflight
must still report `throttled=0x0` before any firmware write. If power state is
unknown or under-voltage is current/latched, do not flash.
