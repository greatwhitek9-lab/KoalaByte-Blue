#!/usr/bin/env python3
"""Print the detected KoalaByte Blue Ultra hardware/runtime profile."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
for path in (ROOT, PI_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from koalablue.hardware_profile import detect_hardware_profile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail unless a Raspberry Pi 5 is detected")
    parser.add_argument("--require-8gb", action="store_true", help="fail unless Pi 5 with at least 7,000 MiB RAM is detected")
    args = parser.parse_args()
    profile = detect_hardware_profile()
    print(json.dumps(profile, indent=2, sort_keys=True))
    if args.require_8gb and not profile["is_pi5_8gb"]:
        print("Required profile not detected: Raspberry Pi 5 with approximately 8 GB RAM.", file=sys.stderr)
        return 2
    if args.check and not profile["is_pi5"]:
        print("Raspberry Pi 5 was not detected.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
