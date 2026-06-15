# RevA19 KillerKoala Voice Router

## Purpose

KillerKoala Voice Router lets the Pi companion turn a wake-word phrase into a safe KoalaByte Blue module run.

The wake word is:

```text
killerkoala
```

The router supports typed phrase mode for CI and bench testing, plus optional microphone mode on the Raspberry Pi when `SpeechRecognition` and PyAudio are installed.

## Test without a microphone

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice_control.py --phrase "killerkoala bluez inventory"
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice_control.py --phrase "killerkoala dropbear discovery sweep for 10 seconds"
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice_control.py --phrase "killerkoala ear tag tx lab"
```

## Optional microphone mode

Install optional Pi microphone dependencies only on the target device:

```bash
sudo apt install -y portaudio19-dev python3-pyaudio
python3 -m pip install SpeechRecognition pyttsx3
```

Then run one listen cycle:

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice_control.py --listen --speak
```

Or keep the router open:

```bash
PYTHONPATH=pi-companion python3 scripts/run_killerkoala_voice_control.py --loop --speak
```

## Supported module phrases

| Phrase examples | Module |
|---|---|
| `killerkoala bluez manifest` | KoalaByte Blue Outback Module Deck |
| `killerkoala bluez inventory` | Gumleaf Gear Check |
| `killerkoala bluez status` | Eucalyptus Bus Scout |
| `killerkoala bluetooth scan for 15 seconds` | Dropbear Discovery Sweep |
| `killerkoala hci monitor for 20 seconds` | Billabong HCI Watch |
| `killerkoala bluez all safe` | Kookaburra Safe Nest Run |
| `killerkoala koala kapture for 15 seconds` | Koala Kapture |
| `killerkoala koala kry` | Koala Kry offline replay |
| `killerkoala ear tag tx lab` | Ear Tag TX Lab plan |
| `killerkoala gatt readiness AA:BB:CC:DD:EE:FF owned device` | Gumnut GATT Readiness |

## XP rewards

XP is stored in:

```text
logs/killerkoala/xp_state.json
```

XP is awarded only when a module returns successfully. Blocked or failed requests do not award XP.

| Module | XP |
|---|---:|
| KoalaByte Blue Outback Module Deck | 1 |
| Gumleaf Gear Check | 3 |
| Eucalyptus Bus Scout | 5 |
| Dropbear Discovery Sweep | 10 |
| Billabong HCI Watch | 8 |
| Kookaburra Safe Nest Run | 12 |
| Koala Kapture | 15 |
| Koala Kry | 5 |
| Ear Tag TX Lab | 5 |
| Gumnut GATT Readiness | 4 |

Ranks remain:

```text
Noob   = 0+ XP
Hacker = 75+ XP
Legend = 250+ XP
```

## Safety behavior

- The wake word is required by default.
- Target-specific modules require a Bluetooth address plus an `owned device`, `lab device`, or `in scope` phrase.
- BlueZ scan/status logs hash Bluetooth addresses by default unless `raw addresses` is explicitly requested.
- The restricted placeholder remains non-operational.
- Koala Kry remains offline metadata replay only.
