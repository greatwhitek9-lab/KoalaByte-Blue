#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from koalablue.esp32_dualeye_voice_bridge import ESP32DualEyeVoiceBridge, default_esp32_port


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the ESP32-S3 DualEye built-in mic voice bridge")
    parser.add_argument("--port", default=default_esp32_port())
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--once", action="store_true", help="Exit after first routed voice event")
    parser.add_argument("--status-only", action="store_true", help="Request mic status then exit after a short read window")
    parser.add_argument("--simulate", default=None, help="Ask ESP32 firmware to emit a simulated voice command phrase")
    args = parser.parse_args()

    bridge = ESP32DualEyeVoiceBridge(port=args.port, baud=args.baud)
    if args.status_only:
        bridge.open()
        try:
            for _ in range(8):
                bridge.read_once()
        finally:
            bridge.close()
        payload = {"status": "ESP32_DUALEYE_MIC_STATUS_REQUESTED", "port": args.port}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.simulate:
        bridge.open()
        try:
            bridge.simulate_voice_command(args.simulate)
            result = bridge.run(seconds=args.seconds, once=True)
        finally:
            bridge.close()
    else:
        result = bridge.run(seconds=args.seconds, once=args.once)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
