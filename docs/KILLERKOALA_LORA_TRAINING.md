# KillerKoala TinyLlama LoRA Training Plan

## Runtime rule

KillerKoala does **not** rely only on an LLM.

```text
Fast default:
  pi-companion/koalablue/killerkoala_vocabulary.py
  anti-repeat phrase engine
  XP/rank-aware Aussie/cyberpunk response rotation

Optional flexible banter:
  local tiny Ollama/llama.cpp model
  LoRA-tuned for KillerKoala's gruff Aussie cyberpunk voice
  short timeout
  automatic fallback to the phrase engine
```

The phrase engine stays the production-safe response path. The tiny LLM is only for flexible companion banter or when `KILLERKOALA_LLM_MODE=force` is explicitly set.

## Target model

Recommended base:

```text
TinyLlama-1.1B-Chat
```

Recommended deployment names:

```text
killerkoala-tinyllama:latest
```

Recommended runtime path on Raspberry Pi 3B+:

```text
Try Ollama first.
Fall back to llama.cpp direct GGUF if Ollama overhead is too heavy.
```

## LoRA voice target

Train the adapter to produce:

- Australian slang and colloquial phrasing.
- Gruff cyberpunk attitude.
- Short useful companion responses.
- Legal/authorized lab tone.
- No long essays by default.
- No repeated catchphrases.

Do **not** train the model on unsafe instructions or out-of-scope workflows. The adapter should tune style and companion behavior, not offensive capability.

## Data format

Use instruction/response JSONL pairs:

```jsonl
{"instruction":"Rewrite this fallback as KillerKoala in under 40 words: scan complete","input":"scan wrapped; the canopy coughed up a few notes.","output":"Bonza, mate. Sweep's done, the canopy coughed up a few useful chirps, and I've tucked the notes in the pouch."}
```

Good examples should include:

- status responses
- scan start/complete responses
- error responses
- level-up responses
- help responses
- short banter responses
- reminders to stay in authorized scope

## Generate training seed data

```bash
PYTHONPATH=pi-companion python3 scripts/generate_killerkoala_lora_dataset.py \
  --output training/killerkoala_lora/killerkoala_lora_seed.jsonl \
  --count-per-event-rank 8
```

Review and hand-edit the JSONL before real training. The generated file is a seed, not a finished dataset.

## Suggested off-device LoRA training flow

Train off the Pi on a stronger machine:

```text
1. Pull TinyLlama-1.1B-Chat base model.
2. Train a small LoRA adapter using the reviewed JSONL dataset.
3. Merge adapter or export the adapter in a runtime-compatible format.
4. Quantize to GGUF Q4 or similar if using llama.cpp/Ollama.
5. Copy the resulting model/adaptor files to the Pi.
```

## Ollama Modelfile

Repository template:

```text
training/killerkoala_lora/Modelfile.killerkoala-tinyllama
```

Build example after placing the tuned model or adapter in the expected local path:

```bash
ollama create killerkoala-tinyllama -f training/killerkoala_lora/Modelfile.killerkoala-tinyllama
```

## Runtime configuration

Default phrase-first mode:

```bash
export KILLERKOALA_LLM_MODE=fast_default
export KILLERKOALA_LLM_MODEL=killerkoala-tinyllama:latest
export KILLERKOALA_LLM_TIMEOUT_SECONDS=2.5
```

Disable LLM completely:

```bash
export KILLERKOALA_LLM_MODE=off
```

Force LLM for testing only:

```bash
export KILLERKOALA_LLM_MODE=force
```

## Preview commands

Phrase engine fast path:

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_hybrid.py scan_complete --xp 100
```

Flexible optional LLM path with automatic fallback:

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_hybrid.py banter --xp 250 --flexible --text "give me a status quip"
```

Voice command execution with optional flexible banter:

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice.py \
  --phrase "killerkoala give the air a squiz and be cheeky" \
  --flexible-banter
```

## Pi 3B+ rule

Keep responses short, context small, and timeouts aggressive. If the tiny LLM is slow, missing, or overloaded, KillerKoala automatically uses the fast phrase engine.
