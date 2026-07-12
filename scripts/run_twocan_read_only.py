#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from koalablue import twocan_read_only as twocan

ACTIONS = {
    "full": twocan.full_read_only_report,
    "adapter": twocan.adapter_identity,
    "identity": twocan.vehicle_identity,
    "stored-dtcs": lambda: twocan.dtc_report("stored"),
    "pending-dtcs": lambda: twocan.dtc_report("pending"),
    "permanent-dtcs": lambda: twocan.dtc_report("permanent"),
    "freeze-frame": twocan.freeze_frame_snapshot,
    "readiness": twocan.readiness_monitors,
    "live-snapshot": twocan.live_pid_snapshot,
    "live-log": twocan.live_pid_log,
    "capture-review": twocan.offline_capture_review,
    "repair-checklist": twocan.repair_verification_checklist,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run TwoCan read-only OBD-II and offline capture actions")
    parser.add_argument("action", choices=sorted(ACTIONS))
    parser.add_argument("--port", default=None, help="ELM327 serial device; defaults to python-OBD auto-detection")
    parser.add_argument("--duration", type=float, default=None, help="Live-log duration in seconds, bounded to 1-300")
    parser.add_argument("--interval", type=float, default=None, help="Live-log sample interval in seconds, bounded to 0.25-10")
    parser.add_argument("--capture", default=None, help="Saved JSON/candump/log/text capture to review offline")
    args = parser.parse_args()

    if args.port:
        os.environ["KOALABYTE_OBD_PORT"] = args.port
    if args.capture:
        os.environ["KOALABYTE_TWOCAN_CAPTURE_PATH"] = str(Path(args.capture).expanduser())

    if args.action == "live-log":
        result = twocan.live_pid_log(args.duration, args.interval)
    else:
        result = ACTIONS[args.action]()
    print(json.dumps(twocan._jsonable(result), indent=2, sort_keys=True))
    return 0 if str(result.get("status", "")).endswith(("READY", "PARTIAL", "NOT_FOUND")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
