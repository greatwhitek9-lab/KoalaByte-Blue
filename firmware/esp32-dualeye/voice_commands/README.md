# ESP32-S3 DualEye Local-First Voice

KoalaByte Blue uses the ESP32-S3 DualEye as a small local companion and voice router. It is not only a microphone bridge.

## Runtime split

```text
ESP32-S3 DualEye:
  ES7210 microphone and ESP-SR English MultiNet phrase recognition
  local Killer Koala / Hey Killer Koala recognition
  embedded Australian wake acknowledgements
  repetitive basic responses: status, help, greetings, thanks and short banter
  local recognition of fixed menu and submenu command IDs
  explicit complex-AI escalation and one-shot PCM capture

Raspberry Pi:
  execution of menu and submenu actions
  complex or open-ended STT/LLM responses
  large Aussie/cyberpunk vocabulary, XP, rank, mood, memory and anti-repeat logic
  returned speech for Pi-owned execution and complex-AI results
```

## Local wake and basic response behavior

The phrases `Killer Koala` and `Hey Killer Koala` are registered in the always-on MultiNet command set. A recognized wake phrase is answered from the embedded ESP32 response bank without contacting the Pi.

Examples include:

```text
Killer Koala is live and ready.
Happy hunting, mate.
Righto, mate. I am listening.
```

Status, help, greetings, thanks and short repetitive banter are also answered locally. The bank is deliberately small and rotates responses to avoid immediate repetition.

## Fixed actions

`killerkoala_multinet_aliases.csv` maps supported phrases to stable command IDs. Fixed menu and submenu requests are recognized on the ESP32 and sent to the Raspberry Pi as canonical action requests. The Pi performs the action and returns its result.

## Complex AI escalation

Open-ended microphone audio is not streamed continuously. The user must first say an explicit escalation phrase such as:

```text
Killer Koala ask the AI
Killer Koala complex question
Killer Koala big brain
```

The ESP32 responds locally, pauses MultiNet, captures only the following utterance, and sends that utterance to the Pi for STT and LLM processing. It then returns to local phrase recognition.

## Privacy and display behavior

Ambient microphone audio remains on the ESP32. Raw sound never draws `AUDIO` or `MIC` text, never adds audio borders, and never plays a detection beep. Only explicit action, thinking, speaking, success and error states affect the eye expressions.
