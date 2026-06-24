#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PI_COMPANION = ROOT / "pi-companion"
if str(PI_COMPANION) not in sys.path:
    sys.path.insert(0, str(PI_COMPANION))

from koalablue import meshtastic_app


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the KoalaByte Didgeridoo Meshtastic application")
    parser.add_argument("action", nargs="?", default="status", choices=["status", "nodes", "gps", "profile"], help="Didgeridoo action to run")
    args = parser.parse_args()

    if args.action == "status":
        payload = meshtastic_app.status()
    elif args.action == "nodes":
        payload = meshtastic_app.nodes()
    elif args.action == "gps":
        payload = meshtastic_app.gps_info()
    else:
        payload = meshtastic_app.profile().to_dict()

    print(json.dumps({"app": "Didgeridoo", "action": args.action, "result": payload}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
