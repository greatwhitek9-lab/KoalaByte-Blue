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

from koalablue.hdmi_display_state import display_mode_status, set_display_mode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Switch HDMI between KoalaByte Blue and the Raspberry Pi OS display"
    )
    parser.add_argument(
        "mode",
        choices=("koalabyte", "desktop", "toggle", "status"),
        help="desktop releases fullscreen so Pi OS/console is visible",
    )
    parser.add_argument("--state-dir", default=None)
    args = parser.parse_args()
    root = Path(args.state_dir) if args.state_dir else None
    payload = (
        display_mode_status(root=root)
        if args.mode == "status"
        else set_display_mode(args.mode, source="hdmi-mode-cli", root=root)
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
