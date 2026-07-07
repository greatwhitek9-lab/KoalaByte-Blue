#!/usr/bin/env python3
"""Inspect UF2 firmware metadata.

Used by the KoalaByte Blue Heltec T114 / HT-n5262 HCI USB build flow to
confirm that the generated UF2 starts at the expected bootloader-safe app
offset and carries the expected UF2 family ID.
"""

from __future__ import annotations

import struct
import sys
from collections import Counter
from pathlib import Path

UF2_MAGIC_START0 = 0x0A324655
UF2_MAGIC_START1 = 0x9E5D5157
UF2_MAGIC_END = 0x0AB16F30


def inspect(path: Path) -> int:
    data = path.read_bytes()
    addrs: list[int] = []
    families: list[int] = []
    sizes: list[int] = []
    flags_seen: Counter[int] = Counter()
    total_blocks = len(data) // 512

    for i in range(total_blocks):
        block = data[i * 512 : (i + 1) * 512]
        if len(block) != 512:
            continue
        magic0, magic1, flags, target, payload_size, block_no, num_blocks, family = struct.unpack_from(
            "<IIIIIIII", block, 0
        )
        (end_magic,) = struct.unpack_from("<I", block, 508)
        if magic0 != UF2_MAGIC_START0 or magic1 != UF2_MAGIC_START1 or end_magic != UF2_MAGIC_END:
            continue
        addrs.append(target)
        families.append(family)
        sizes.append(payload_size)
        flags_seen[flags] += 1

    print(f"File: {path}")
    print(f"Size: {len(data)} bytes")
    print(f"UF2 blocks parsed: {len(addrs)} / {total_blocks}")

    if not addrs:
        print("[!] No valid UF2 blocks found")
        return 1

    print(f"Address min: 0x{min(addrs):08x}")
    print(f"Address max: 0x{max(addrs):08x}")
    print(f"Address span end approx: 0x{max(a + s for a, s in zip(addrs, sizes)):08x}")
    print(f"Payload sizes: {sorted(set(sizes))}")
    print(f"Families: {[hex(x) for x in sorted(set(families))]}")
    print(f"Flags: {[hex(x) for x in sorted(flags_seen)]}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: inspect_uf2.py <file.uf2> [file2.uf2 ...]", file=sys.stderr)
        return 2

    rc = 0
    for name in argv[1:]:
        path = Path(name)
        if not path.exists():
            print(f"[x] Missing file: {path}", file=sys.stderr)
            rc = 1
            continue
        if len(argv) > 2:
            print("=" * 72)
        rc = max(rc, inspect(path))
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
