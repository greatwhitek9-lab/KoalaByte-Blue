# Koala Kan Commander Firmware Track

This directory is the optional, experimental firmware track for a future CAN Commander-style adapter firmware.

The normal Koala Kan Kommander path **does not require custom InnoMaker firmware**. Use the InnoMaker adapter with its stock firmware through Linux SocketCAN:

```bash
CAN_INTERFACE=can0 CAN_BITRATE=500000 bash scripts/setup_can0.sh
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py manifest --interface can0
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_kommander.py status --interface can0
```

## Current status

This track is included in the suite as a board-qualification and protocol-planning track. It is not a default flash target and does not include a generic firmware image because the exact InnoMaker MCU, bootloader, pinout, clock tree, CAN controller/transceiver wiring, and recovery process must be confirmed first.

Use:

```bash
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_firmware.py manifest
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_firmware.py status
PYTHONPATH=pi-companion python3 scripts/run_koala_kan_firmware.py plan
```

## Why this is optional

Replacing firmware on a USB-to-CAN adapter can brick the adapter if the board profile is wrong. KoalaByte therefore keeps SocketCAN as the production path and treats custom firmware as experimental until the board is positively identified and recoverable.

Before any flash helper is added, confirm:

1. Exact MCU marking.
2. Exact board revision.
3. Bootloader, BOOT/RESET, DFU, or SWD access.
4. CAN transceiver part number and pin wiring.
5. Oscillator / clock source.
6. USB D+ / D- pins.
7. Stock firmware backup or recovery image.
8. Bench simulator or fully isolated owned harness only.

## Candidate protocol

A future Koala Kan Commander firmware can use one of two safe host protocols:

| Protocol | Best use |
|---|---|
| `gs_usb` / candleLight-style USB CAN bridge | Best Linux integration because it appears as a SocketCAN device. |
| USB CDC JSON bridge | Easier to debug and align with KoalaByte logs, but requires a host-side serial bridge. |

## USB CDC JSON sketch

Host to adapter:

```json
{"type":"hello"}
{"type":"get_status"}
{"type":"set_bitrate","bitrate":500000}
{"type":"start_listen"}
{"type":"stop_listen"}
{"type":"tx_frame_lab","can_id":"0x600","data":"4B 42 01 00","bench_simulator":true,"confirm_transmit":true}
```

Adapter to host:

```json
{"type":"boot","device":"koala-kan-commander","fw":"0.1.0"}
{"type":"status","bitrate":500000,"listen":true,"tx_enabled":false}
{"type":"rx_frame","can_id":"0x600","dlc":4,"data":"4B 42 01 00"}
{"type":"tx_ack","can_id":"0x600","bytes":4}
{"type":"error","message":"blocked_by_policy"}
```

## Safety policy

This firmware track is for parser/display/logging validation against a bench CAN simulator or owned isolated harness only.

It does not include:

- Vehicle-specific payload libraries.
- Diagnostic service payloads.
- Security-access, immobilizer, braking, steering, lock, lighting, or powertrain command sets.
- Captured traffic replay.
- Default transmit mode.

The production suite already has gated host-side transmit for synthetic lab-range IDs only. Keep firmware transmit disabled by default until a confirmed adapter profile exists.
