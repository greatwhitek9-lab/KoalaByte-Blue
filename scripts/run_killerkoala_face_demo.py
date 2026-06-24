#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time

from koalablue.killerkoala_face_bridge import emit_face


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview split KillerKoala face: ESP32-S3 DualEye eyes plus optional Heltec USB-C face/mouth state JSON")
    parser.add_argument("--state", choices=["wake", "listening", "thinking", "speaking", "action", "success", "error"], help="Send one state only")
    parser.add_argument("--message", default="killerkoala online")
    parser.add_argument("--duration-ms", type=int, default=2500)
    parser.add_argument("--sequence", action="store_true", help="Run wake -> thinking -> action -> speaking -> success")
    args = parser.parse_args()

    steps = [(args.state or "wake", args.message)]
    if args.sequence:
        steps = [("wake", "killerkoala heard"), ("thinking", "sussing the job"), ("action", "action selected"), ("speaking", "too easy mate"), ("success", "done and logged")]

    results = []
    for state, message in steps:
        results.append(emit_face(state, message, duration_ms=args.duration_ms))
        if len(steps) > 1:
            time.sleep(max(0.35, args.duration_ms / 1000.0 * 0.55))
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
