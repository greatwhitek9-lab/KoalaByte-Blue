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

from koalablue.eucalyptus_wigle import build_gps_trail, control_status, upload_status, upload_to_wigle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Eucalyptus GPS trail and WiGLE upload helper")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Show Eucalyptus GPS/WiGLE readiness")
    sub.add_parser("gps-trail", help="Build a GPS-enriched passive BLE trail and WiGLE CSV")
    upload = sub.add_parser("wigle-upload", help="Upload the latest generated Eucalyptus BLE/GPS trail to WiGLE when explicitly armed")
    upload.add_argument("--dry-run", action="store_true", help="Build the CSV but do not contact WiGLE")
    for name in ["start", "stop", "restart", "upload-status"]:
        sub.add_parser(name, help=f"Record/check Eucalyptus {name} action")
    args = parser.parse_args()

    if args.command == "status":
        payload = upload_status()
    elif args.command == "gps-trail":
        payload = build_gps_trail().__dict__
    elif args.command == "wigle-upload":
        payload = upload_to_wigle(dry_run=args.dry_run)
    else:
        payload = control_status(args.command)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if str(payload.get("status", "")).endswith(("READY", "COMPLETE", "RECORDED", "EMPTY", "NOT_ARMED", "DRY_RUN")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
