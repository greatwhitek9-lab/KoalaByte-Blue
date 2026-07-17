#!/usr/bin/env python3
"""Validate a UF2 image's family, vector table, and reset target."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

UF2_MAGIC_START0 = 0x0A324655
UF2_MAGIC_START1 = 0x9E5D5157
UF2_MAGIC_END = 0x0AB16F30
UF2_FLAG_FAMILY_ID_PRESENT = 0x00002000
UF2_BLOCK_SIZE = 512
UF2_DATA_OFFSET = 32
UF2_MAX_PAYLOAD = 476


def number(value: str) -> int:
    return int(value, 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("uf2", type=Path)
    parser.add_argument("--vector-address", type=number, required=True)
    parser.add_argument("--application-min", type=number, required=True)
    parser.add_argument("--application-max", type=number, required=True)
    parser.add_argument("--ram-min", type=number, default=0x20000000)
    parser.add_argument("--ram-max", type=number, default=0x20040000)
    parser.add_argument("--family", type=number, required=True)
    args = parser.parse_args()

    blob = args.uf2.read_bytes()
    if not blob or len(blob) % UF2_BLOCK_SIZE:
        raise SystemExit("UF2 length is not a nonzero multiple of 512 bytes")

    memory: dict[int, int] = {}
    families: set[int] = set()
    block_count = len(blob) // UF2_BLOCK_SIZE

    for offset in range(0, len(blob), UF2_BLOCK_SIZE):
        block = blob[offset : offset + UF2_BLOCK_SIZE]
        (
            magic0,
            magic1,
            flags,
            target,
            payload_size,
            block_number,
            total_blocks,
            family,
        ) = struct.unpack_from("<IIIIIIII", block)
        magic_end = struct.unpack_from("<I", block, 508)[0]

        if (magic0, magic1, magic_end) != (
            UF2_MAGIC_START0,
            UF2_MAGIC_START1,
            UF2_MAGIC_END,
        ):
            raise SystemExit(f"Invalid UF2 magic in block {block_number}")
        if payload_size > UF2_MAX_PAYLOAD:
            raise SystemExit(f"Invalid payload size in block {block_number}")
        if total_blocks != block_count:
            raise SystemExit(f"Incorrect total-block field in block {block_number}")
        if flags & UF2_FLAG_FAMILY_ID_PRESENT:
            families.add(family)
        else:
            raise SystemExit(f"Family flag missing in block {block_number}")

        payload = block[UF2_DATA_OFFSET : UF2_DATA_OFFSET + payload_size]
        for index, byte in enumerate(payload):
            address = target + index
            previous = memory.get(address)
            if previous is not None and previous != byte:
                raise SystemExit(f"Conflicting UF2 payload at 0x{address:08x}")
            memory[address] = byte

    if families != {args.family}:
        rendered = ", ".join(f"0x{value:08x}" for value in sorted(families))
        raise SystemExit(
            f"Unexpected UF2 family set: [{rendered}], expected 0x{args.family:08x}"
        )

    vector_bytes = bytes(
        memory.get(args.vector_address + index, 0xFF) for index in range(8)
    )
    initial_sp, reset_vector = struct.unpack("<II", vector_bytes)
    reset_handler = reset_vector & ~1

    if not args.ram_min <= initial_sp <= args.ram_max:
        raise SystemExit(f"Initial SP is outside RAM: 0x{initial_sp:08x}")
    if initial_sp % 8:
        raise SystemExit(f"Initial SP is not 8-byte aligned: 0x{initial_sp:08x}")
    if not (reset_vector & 1):
        raise SystemExit(f"Reset vector is not a Thumb address: 0x{reset_vector:08x}")
    if not args.application_min <= reset_handler < args.application_max:
        raise SystemExit(
            "Reset handler is outside the application partition: "
            f"0x{reset_vector:08x}"
        )

    address_min = min(memory)
    address_end = max(memory) + 1
    if address_min != args.application_min:
        raise SystemExit(
            f"UF2 starts at 0x{address_min:08x}, expected 0x{args.application_min:08x}"
        )
    if address_end > args.application_max:
        raise SystemExit(
            f"UF2 ends at 0x{address_end:08x}, beyond 0x{args.application_max:08x}"
        )

    print(f"UF2 blocks: {block_count}")
    print(f"UF2 family: 0x{args.family:08x}")
    print(f"UF2 address range: 0x{address_min:08x}-0x{address_end:08x}")
    print(f"Vector table: 0x{args.vector_address:08x}")
    print(f"Initial SP: 0x{initial_sp:08x}")
    print(f"Reset vector: 0x{reset_vector:08x}")
    print("Reset handler range valid: true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
