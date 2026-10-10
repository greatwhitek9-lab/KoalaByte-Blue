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
- Selects a stronger local AI base model by detected RAM: Qwen2.5 1.5B on 4 GB,
  Qwen2.5 3B on 8 GB, and Qwen2.5 7B on 16 GB; 2 GB and older Pi hardware retain
  TinyLlama 1.1B. Explicit `KILLERKOALA_BASE_MODEL` overrides remain supported.
- Builds the same `killerkoala-tinyllama:latest` runtime alias from the selected
  base model, so existing voice/command callers remain compatible. The current
  persona is prompt-defined; the repository's commented adapter is not a trained
  LoRA and is not falsely treated as one.
- Keeps one model loaded, uses RAM-tiered context/prediction limits, and leaves
  the selected model warm for 5 minutes on 8 GB Pi 5 or 10 minutes on 16 GB Pi 5
  to reduce cold-start latency. A 3B model is the balanced Pi 5 default; 7B is
  more capable but can respond more slowly on CPU-only hardware.
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

## KillerKoala AI, latency, and voice

The Ollama setup generates a temporary Modelfile with the selected base model,
context size, and prediction budget. It does not overwrite the checked-in Pi 3
baseline. User-supplied `KILLERKOALA_BASE_MODEL`, context, parallelism, and
keep-alive settings take precedence.

KillerKoala keeps its spoken identity and command-routing contract. Its persona
is tuned toward a cheeky, dry Australian punk/hacker voice with restrained
Australian slang, short first responses, and more detailed answers on request.
The preferred speech backend remains Microsoft Edge Neural `en-AU-WilliamNeural`;
audio uses a small process-local cache for repeated phrases and falls back to
local Australian eSpeak when the neural service is unavailable. Neural TTS still
requires network access, so a truly offline voice will sound less natural.

No CPU-only Raspberry Pi can guarantee literally instant answers. Keeping a
3B model loaded and limiting generated tokens should improve perceived latency
without loading multiple models or consuming the entire system RAM. The 7B tier
prioritizes capability over speed.

## Hardware notes

Use a proper Pi 5 power supply (5 V / 5 A class) and cooling appropriate for
sustained AI and firmware-build workloads. KoalaByte's strict power preflight
must still report `throttled=0x0` before any firmware write. If power state is
unknown or under-voltage is current/latched, do not flash.
