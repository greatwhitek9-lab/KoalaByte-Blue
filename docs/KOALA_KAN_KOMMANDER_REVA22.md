# RevA23/RevA25 Koala Kan Kommander - InnoMaker USB-to-CAN Update

## Purpose

Koala Kan Kommander adds an optional physical CAN bench path for KoalaByte Blue using the user-specified **InnoMaker USB to CAN Converter kit** as the USB-to-CAN adapter.

It is designed for authorized bench, training, owned-device CAN observation, and completely isolated bench simulator testing. RevA25 changes the module from passive-only observation to **bounded listen plus gated transmit**. Transmit requires an isolated bench simulator and explicit operator confirmation flags.

RevA24 added a **synthetic payload generator** for parser, display, logging, and isolated bench-harness validation. RevA25 can send those synthetic payloads through SocketCAN when the bench simulator gates are present.

## Physical device option

Recommended physical path:

```text
Raspberry Pi 3B+ USB host
  -> short internal USB cable
  -> InnoMaker USB to CAN Converter kit
  -> adapter-side CAN_H / CAN_L / GND / optional SHIELD
  -> isolated CAN bench simulator or owned bench harness
```

Do not wire CAN_H or CAN_L directly to Raspberry Pi GPIO. Use the InnoMaker adapter as the CAN controller/transceiver path.

## Mechanical update

RevA23 removes the earlier circular CAN panel port. Mount the InnoMaker converter internally or in a side/rear rectangular service bay and provide cable strain relief. Keep it clear of antennas, batteries, speaker grille, and the Pi GPIO header.

## Connector lines

```text
CAN_H
CAN_L
GND
optional SHIELD
```

Use the adapter-side connection supplied by the selected InnoMaker kit/listing. Do not create a direct Pi GPIO CAN wiring path.

## Menu entry

The menu option is named:

```text
Koala Kan Kommander
```

The command key is:

```text
koala_kan_kommander
```

## Runner

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py inventory
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py status --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py listen --interface can0 --duration 10
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py report --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py generate-payloads --interface can0 --payload-profile all --base-id 0x600 --sequence-count 8 --tag KOALAKAN
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py transmit --interface can0 --bench-simulator --confirm-transmit --payload-profile heartbeat --base-id 0x600 --sequence-count 3
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py listen-transmit --interface can0 --bench-simulator --confirm-transmit --can-id 0x600 --data "4B 42 01 00" --duration 10
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py transmit-placeholder
```

## Supported actions

| Action | Behavior |
|---|---|
| `manifest` | Writes the plug-in manifest with the InnoMaker adapter path, payload schema metadata, and RevA25 transmit gates. |
| `inventory` | Detects SocketCAN interfaces under `/sys/class/net`. |
| `status` | Saves `ip -details -statistics link show <interface>` output. |
| `listen` | Performs a bounded raw-socket CAN listen and saves JSON artifacts. |
| `transmit` | Sends synthetic lab-range CAN frames only when `--bench-simulator` and `--confirm-transmit` are both present. |
| `listen-transmit` | Sends the gated transmit batch and then performs a bounded listen, writing a combined artifact. |
| `report` | Writes a Markdown report with inventory/status/payload artifact links. |
| `generate-payloads` | Generates bench-only synthetic payload JSON using the `koala-kan-payload-batch-v1` schema. |
| `transmit-placeholder` | Legacy blocked placeholder. It never sends frames; use `transmit` or `listen-transmit` with the required gates. |

## Payload generator and transmit limits

The generator creates synthetic frames for authorized bench harnesses, CAN simulators, parser validation, display checks, and logging tests. It reserves four standard 11-bit lab IDs starting from `--base-id`.

Default profiles:

| Profile | Purpose | Default ID offset |
|---|---|---|
| `heartbeat` | KoalaByte heartbeat pattern for UI/logging validation. | `base + 0` |
| `counter` | Monotonic counter and inverse byte pattern for parser checks. | `base + 1` |
| `walking-bit` | Walking bit pattern for bitfield display validation. | `base + 2` |
| `ascii-tag` | One padded ASCII label frame, default `KOALAKAN`. | `base + 3` |
| `all` | Emits the full synthetic batch. | `base + 0..3` |

RevA25 transmit constraints:

- Requires `--bench-simulator` and `--confirm-transmit`.
- Uses standard 11-bit CAN frames only.
- Allows only the lab-range ID window `0x600-0x67F`.
- Caps generated and transmitted batches at 64 frames.
- Logs every requested and sent frame to JSON artifacts.
- Keeps `transmit-placeholder` blocked for backward-compatible safety checks.

Manual single-frame example:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py transmit \
  --interface can0 \
  --bench-simulator \
  --confirm-transmit \
  --can-id 0x600 \
  --data "4B 42 01 00" \
  --count 3 \
  --inter-frame-ms 100
```

Generated profile transmit example:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py transmit \
  --interface can0 \
  --bench-simulator \
  --confirm-transmit \
  --payload-profile all \
  --base-id 0x600 \
  --sequence-count 4
```

## Optional Pi setup

Most USB-to-CAN adapters expose a SocketCAN interface such as `can0`. Useful host commands:

```bash
sudo apt install -y can-utils iproute2
ip link show
sudo ip link set can0 up type can bitrate 500000
ip -details -statistics link show can0
```

Use the bitrate required by your isolated bench simulator or owned bench harness.

## Safety boundary

Koala Kan Kommander is for authorized CAN observation and completely isolated bench simulator validation only. RevA25 can transmit synthetic lab-range CAN frames only after explicit bench confirmation flags.

The payload generator and transmit path deliberately exclude UDS diagnostic services, OBD requests, DTC operations, ECU reset/security-access frames, OEM arbitration IDs, captured traffic replay, and actuator-oriented payloads. Do not use this on vehicles, battery systems, industrial controllers, or any embedded control network unless the network is an isolated owned lab harness with documented authorization and safe operating conditions.
