#!/usr/bin/env python3
"""Patch the UF2 family ID in every valid UF2 block.

The Heltec T114 / HT-n5262 UF2 bootloader expects family 0x239a0071.
Some Zephyr UF2 outputs for nRF52840 use 0xada52840 instead, which can copy
successfully but fail to boot on this board. This helper rewrites the family ID
and ensures the UF2 family-present flag is set.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

UF2_MAGIC_START0 = 0x0A324655
UF2_MAGIC_START1 = 0x9E5D5157
UF2_MAGIC_END = 0x0AB16F30
UF2_FLAG_FAMILY_ID_PRESENT = 0x00002000


def patch(input_path: Path, output_path: Path, new_family: int) -> int:
    data = bytearray(input_path.read_bytes())

    if len(data) % 512 != 0:
        raise ValueError(f"Input size is not a multiple of 512: {len(data)}")

    patched = 0
    seen: set[int] = set()

    for off in range(0, len(data), 512):
        magic0, magic1, flags, target, payload_size, block_no, num_blocks, family = struct.unpack_from(
            "<IIIIIIII", data, off
        )
        (end_magic,) = struct.unpack_from("<I", data, off + 508)
        if magic0 != UF2_MAGIC_START0 or magic1 != UF2_MAGIC_START1 or end_magic != UF2_MAGIC_END:
            continue

        seen.add(family)
        flags |= UF2_FLAG_FAMILY_ID_PRESENT
        struct.pack_into("<I", data, off + 8, flags)
        struct.pack_into("<I", data, off + 28, new_family)
        patched += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)

    print(f"Input:          {input_path}")
    print(f"Output:         {output_path}")
    print(f"Blocks patched: {patched}")
    print(f"Families seen:  {[hex(x) for x in sorted(seen)]}")
    print(f"New family:     {hex(new_family)}")

    return 0 if patched else 1


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("Usage: patch_uf2_family.py <input.uf2> <output.uf2> <family_hex>", file=sys.stderr)
        return 2

    input_path = Path(argv[1])
    output_path = Path(argv[2])
    new_family = int(argv[3], 0)

    if not input_path.exists():
        print(f"[x] Input UF2 not found: {input_path}", file=sys.stderr)
        return 1

    try:
        return patch(input_path, output_path, new_family)
    except Exception as exc:
        print(f"[x] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
