# RevA42 KillerKoala Local and Pi Vocabulary

## Purpose

KillerKoala uses two response tiers. The ESP32-S3 provides immediate, repetitive basic responses without depending on the Raspberry Pi. The Pi remains responsible for large-vocabulary, state-aware and complex responses.

## Architecture

```text
ESP32-S3 DualEye:
  local Killer Koala / Hey Killer Koala phrase recognition
  embedded Australian wake acknowledgements
  basic status, help, greeting, thanks and short-banter responses
  fixed menu/submenu command recognition
  explicit complex-AI escalation

Raspberry Pi:
  menu and submenu execution
  open-ended STT and LLM processing after explicit escalation
  large KillerKoala vocabulary engine
  Aussie/cyberpunk response variation
  XP, rank, mood, memory and anti-repeat phrase rotation
```

Ambient audio is not continuously sent to the Pi. The ESP32 captures a Pi-bound utterance only after an explicit phrase such as `Killer Koala ask the AI`.

## ESP32 local response bank

The local bank is generated at firmware build time and embedded in the ESP32 application as compressed audio. It includes rotating phrases for these categories:

```text
wake
status
help
greeting
thanks
banter
complex-AI escalation
```

Representative wake responses include:

```text
Killer Koala is live and ready.
Happy hunting, mate.
Righto, mate. I am listening.
```

The local bank is intentionally compact and repetitive. It prevents network latency for basic interactions and remains available when the Pi is offline.

Implementation files:

```text
firmware/esp32-dualeye/include/local_voice_responses.h
firmware/esp32-dualeye/scripts/generate_local_voice_responses.py
firmware/esp32-dualeye/src/integrated_main_clean_voice.cpp
firmware/esp32-dualeye/voice_commands/killerkoala_multinet_aliases.csv
```

## Pi vocabulary engine

Complex, open-ended, execution-result and state-aware responses continue to use:

```text
pi-companion/koalablue/killerkoala_vocabulary.py
pi-companion/koalablue/killerkoala_hybrid_companion.py
pi-companion/koalablue/esp32_dualeye_local_first_bridge.py
```

The Pi vocabulary engine retains Noob, Hacker and Legend rank tones and a recent-history window of 24 selections per event/rank.

## Fixed action routing

The ESP32 recognizes stable command phrases and sends canonical command IDs to the Pi. Examples:

```text
killerkoala give the air a squiz -> bluez_scan
killerkoala suss the bluetooth stack -> bluez_status
killerkoala bag the beacons -> koala_kapture
killerkoala chew through the logs -> koala_kry
killerkoala call it a day -> shutdown
```

The ESP32 does not execute those system actions itself. It recognizes and routes them; the Raspberry Pi owns execution.

## Complex AI routing

The user first says one of the explicit escalation phrases:

```text
Killer Koala ask the AI
Killer Koala complex question
Killer Koala big brain
```

The ESP32 answers locally, pauses local recognition, records only the following utterance, and sends it to the Pi. The Pi performs STT and routes the request to menu execution or the larger LLM response tier.

## Safety scope

KillerKoala vocabulary is for authorized lab narration, local diagnostics, status reactions, companion banter, defensive workflow guidance and approved menu actions. The architecture does not enable continuous ambient-audio forwarding or autonomous out-of-scope execution.
