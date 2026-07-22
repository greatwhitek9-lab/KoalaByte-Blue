#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterator

from .serial_command_bus import submit_command
from .serial_maintenance import require_direct_serial_maintenance


def read_events(path: Path) -> Iterator[dict[str, object]]:
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            print(f"Skipping invalid JSONL line: {line[:120]}", file=sys.stderr)
            continue
        if isinstance(payload, dict):
            yield payload


def write_direct(port: str, baud: int, payloads: list[dict[str, object]]) -> int:
    require_direct_serial_maintenance(
        "heltec",
        env_var="KOALABYTE_ALLOW_DIRECT_HELTEC_SERIAL",
        service_name="koalabyte-ble-node-manager.service",
    )
    import serial  # type: ignore

    written = 0
    serial_port = serial.Serial()
    serial_port.port = port
    serial_port.baudrate = baud
    serial_port.timeout = 0.2
    serial_port.write_timeout = 1.0
    serial_port.dsrdtr = False
    serial_port.rtscts = False
    serial_port.dtr = False
    serial_port.rts = False
    serial_port.open()
    try:
        for payload in payloads:
            serial_port.write(
                (json.dumps(payload, separators=(",", ":")) + "\n").encode(
                    "utf-8"
                )
            )
            serial_port.flush()
            written += 1
    finally:
        serial_port.close()
    return written


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay JSONL events to the Heltec through its serial owner"
    )
    parser.add_argument("--input", required=True, help="JSONL input file")
    parser.add_argument(
        "--port",
        default=os.getenv("KOALABYTE_HELTEC_USB_PORT", "/dev/koalabyte-heltec"),
        help="Used only with --direct-serial",
    )
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument(
        "--direct-serial",
        action="store_true",
        help=(
            "Manual recovery only; requires KOALABYTE_ALLOW_DIRECT_HELTEC_SERIAL=1 "
            "and a stopped Heltec owner service"
        ),
    )
    args = parser.parse_args()

    path = Path(args.input)
    if not path.exists():
        print(f"Input file not found: {path}", file=sys.stderr)
        return 2
    payloads = list(read_events(path))
    if not payloads:
        print("No valid JSON events found.", file=sys.stderr)
        return 2

    if args.direct_serial:
        written = write_direct(args.port, args.baud, payloads)
        mode = "direct_manual_owner_stopped"
    else:
        written = 0
        for payload in payloads:
            result = submit_command(
                "heltec", payload, queue_if_unavailable=True
            )
            if not result.accepted:
                print(
                    f"Heltec owner rejected event: {result.status}",
                    file=sys.stderr,
                )
                return 1
            written += 1
        mode = "single_owner_command_bus"

    print(
        json.dumps(
            {
                "status": "HELTEC_EVENTS_SUBMITTED",
                "mode": mode,
                "input": str(path),
                "submitted": written,
                "target": "heltec",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
