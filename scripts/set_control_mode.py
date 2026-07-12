#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_ROOT = ROOT / "pi-companion"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from koalablue.control_mode import load_control_mode, write_control_mode


def main() -> int:
    parser = argparse.ArgumentParser(description="Set or show the KoalaByte input control mode.")
    parser.add_argument("mode", nargs="?", choices=["auto", "full_controls", "touch_speech_only"])
    parser.add_argument("--reason", default="Manual control-mode selection")
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args()

    if args.show or args.mode is None:
        print(json.dumps(load_control_mode(), indent=2, sort_keys=True))
        return 0

    payload = write_control_mode(
        args.mode,
        reason=args.reason,
        source="set_control_mode_cli",
        buttons_available=True if args.mode == "full_controls" else (False if args.mode == "touch_speech_only" else None),
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
