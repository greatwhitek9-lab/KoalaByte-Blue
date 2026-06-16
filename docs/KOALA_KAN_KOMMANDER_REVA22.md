# RevA23/RevA24 Koala Kan Kommander - InnoMaker USB-to-CAN Update

## Purpose

Koala Kan Kommander adds an optional physical CAN observation path for KoalaByte Blue using the user-specified **InnoMaker USB to CAN Converter kit** as the USB-to-CAN adapter.

It is designed for authorized bench, training, and owned-device CAN observation. The production plug-in is passive by default and does not implement raw CAN frame transmission.

RevA24 adds a **synthetic payload generator** for parser, display, logging, and isolated bench-harness validation. The generator writes transmit-compatible JSON artifacts and SocketCAN preview lines, but it does not send frames itself.

## Physical device option

Recommended physical path:

```text
Raspberry Pi 3B+ USB host
  -> short internal USB cable
  -> InnoMaker USB to CAN Converter kit
  -> adapter-side CAN_H / CAN_L / GND / optional SHIELD
  -> authorized bench harness or owned-device test network
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
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py transmit-placeholder
```

## Supported actions

| Action | Behavior |
|---|---|
| `manifest` | Writes the plug-in manifest with the InnoMaker adapter path and payload schema metadata. |
| `inventory` | Detects SocketCAN interfaces under `/sys/class/net`. |
| `status` | Saves `ip -details -statistics link show <interface>` output. |
| `listen` | Performs a bounded passive raw-socket CAN listen and saves JSON artifacts. |
| `report` | Writes a Markdown report with inventory/status/payload artifact links. |
| `generate-payloads` | Generates bench-only synthetic payload JSON using the `koala-kan-payload-batch-v1` schema. No frames are transmitted. |
| `transmit-placeholder` | Writes a blocked transmit manifest. Raw CAN transmission remains intentionally disabled in production. |

## Payload generator

The generator creates synthetic frames for authorized bench harnesses, CAN simulators, parser validation, display checks, and logging tests. It reserves four standard 11-bit lab IDs starting from `--base-id`.

Default profiles:

| Profile | Purpose | Default ID offset |
|---|---|---|
| `heartbeat` | KoalaByte heartbeat pattern for UI/logging validation. | `base + 0` |
| `counter` | Monotonic counter and inverse byte pattern for parser checks. | `base + 1` |
| `walking-bit` | Walking bit pattern for bitfield display validation. | `base + 2` |
| `ascii-tag` | One padded ASCII label frame, default `KOALAKAN`. | `base + 3` |
| `all` | Emits the full synthetic batch. | `base + 0..3` |

Generated artifacts include:

```text
schema_version
interface_hint
frames[].can_id_hex
frames[].dlc
frames[].data_hex
frames[].is_extended
frames[].is_remote_request
frames[].repeat_ms
socketcan_preview_lines
transmit_function_contract
```

The `socketcan_preview_lines` are formatted for human review and downstream bench tooling. They are not executed by the plug-in.

## Optional Pi setup

Most USB-to-CAN adapters expose a SocketCAN interface such as `can0`. Useful host commands:

```bash
sudo apt install -y can-utils iproute2
ip link show
sudo ip link set can0 up type can bitrate 500000
ip -details -statistics link show can0
```

Use the bitrate required by your authorized bench harness or owned-device test network.

## Safety boundary

Koala Kan Kommander is for authorized CAN observation and bench validation only. The production plug-in does not transmit raw CAN frames.

The payload generator deliberately excludes UDS diagnostic services, OBD requests, DTC operations, ECU reset/security-access frames, OEM arbitration IDs, captured traffic replay, and actuator-oriented payloads. Do not use this on vehicles, battery systems, industrial controllers, or any embedded control network unless the network is an isolated owned lab harness with documented authorization and safe operating conditions.
