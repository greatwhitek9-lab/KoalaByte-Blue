# ESP32-S3 DualEye Voice Front End

KoalaByte Blue uses the ESP32-S3 DualEye as the voice front end, not the full AI brain.

## Selected model stack

```text
ESP32-S3 DualEye:
  ESP-SR AFE/VAD
  WakeNet9 or WakeNet9s wake word path
  MultiNet7 Q8 English command recognition

Raspberry Pi:
  KillerKoala companion brain
  Large Aussie/cyberpunk vocabulary pack
  XP, rank, mood, memory, and response variation
```

## Wake word

```text
killerkoala
```

The firmware config records the intended stack. The actual custom WakeNet model must be generated/trained with Espressif's supported workflow before it can replace the placeholder wake backend.

## Command aliases

`killerkoala_multinet_aliases.csv` maps natural spoken phrases to stable command IDs. The ESP32-S3 should send command IDs or raw recognized text to the Raspberry Pi over serial JSON. The Raspberry Pi then chooses the full KillerKoala response using the large vocabulary engine.

## Why the vocabulary lives on the Pi

The ESP32-S3 is best used for wake word detection, voice activity, and short command recognition. Large vocabulary, anti-repeat response selection, Aussie slang variation, XP-aware personality, and longer companion banter run on the Raspberry Pi.

This split prevents KillerKoala from repeating the same handful of phrases while keeping the ESP32 voice front end fast and reliable.
