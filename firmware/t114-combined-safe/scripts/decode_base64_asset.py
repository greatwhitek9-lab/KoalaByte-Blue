#!/usr/bin/env python3
"""Decode split, repository-safe base64 firmware artwork deterministically."""

from __future__ import annotations

import argparse
import base64
import hashlib
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-bytes", type=int, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("parts", nargs="+", type=Path)
    args = parser.parse_args()

    encoded = "".join(
        "".join(part.read_text(encoding="ascii").split()) for part in args.parts
    )
    payload = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(payload).hexdigest()
    if len(payload) != args.expected_bytes:
        raise SystemExit(
            f"decoded {len(payload)} bytes; expected {args.expected_bytes}"
        )
    if digest != args.expected_sha256.lower():
        raise SystemExit(
            f"decoded SHA-256 {digest}; expected {args.expected_sha256.lower()}"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
