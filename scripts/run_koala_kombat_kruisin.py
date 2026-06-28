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

from koalablue.koala_kombat_kruisin import control, run_survey, status, upload_to_wigle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Koala Kombat Kruisin’: passive Wi-Fi/BLE/GPS survey and WiGLE helper")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Show survey/GPS/WiGLE readiness")
    survey = sub.add_parser("survey", help="Run Wi-Fi + BLE survey")
    survey.add_argument("--wifi-seconds", type=float, default=None)
    survey.add_argument("--ble-seconds", type=float, default=None)
    sub.add_parser("wifi-survey", help="Run Wi-Fi AP survey only")
    sub.add_parser("ble-survey", help="Run BLE survey only")
    sub.add_parser("gps-status", help="Show GPS readiness/fix status")
    sub.add_parser("export", help="Run survey and write CSV/GeoJSON/WiGLE exports")
    upload = sub.add_parser("wigle-upload", help="Run survey and upload WiGLE CSV when explicitly armed")
    upload.add_argument("--dry-run", action="store_true", help="Build WiGLE CSV but do not contact WiGLE")
    args = parser.parse_args()

    if args.command == "status":
        payload = status()
    elif args.command == "survey":
        payload = run_survey(mode="both", wifi_seconds=args.wifi_seconds or 10.0, ble_seconds=args.ble_seconds or 10.0).__dict__
    elif args.command == "wifi-survey":
        payload = run_survey(mode="wifi").__dict__
    elif args.command == "ble-survey":
        payload = run_survey(mode="ble").__dict__
    elif args.command == "wigle-upload":
        payload = upload_to_wigle(dry_run=args.dry_run)
    else:
        payload = control(args.command)
    print(json.dumps(payload, indent=2, sort_keys=True))
    status_text = str(payload.get("status", ""))
    ok_tokens = ("READY", "COMPLETE", "RECORDED", "EMPTY", "STATUS", "DRY_RUN", "NOT_READY")
    return 0 if status_text.endswith(ok_tokens) or status_text in {"KOALA_KOMBAT_KRUISIN_STATUS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
